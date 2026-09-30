"""Shared helpers for the v3 analyses (preregistration_v3.md).
Same models, hyperparameters, fold construction, source-level rule and bootstrap procedure as v2."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore", message=".*penalty.*deprecated", category=FutureWarning)
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import balanced_accuracy_score, recall_score, roc_auc_score

SEED = 42
ASINH_SCALE = 0.1
SOURCE_THRESHOLD = 0.5
LR_PARAMS = dict(C=1.0, penalty='l2', class_weight='balanced', max_iter=5000, solver='lbfgs')
RF_PARAMS = dict(n_estimators=500, max_features='sqrt', min_samples_leaf=2,
                 class_weight='balanced', n_jobs=2, random_state=SEED)
MODELS = {'LogReg': lambda: make_pipeline(StandardScaler(), LogisticRegression(**LR_PARAMS)),  # scaler fit on train only
          'RandomForest': lambda: RandomForestClassifier(**RF_PARAMS)}


def band(rate, edges, lo, hi):
    """Net count rate [count/s/PCU] summed over grid bins whose geometric centre lies in [lo, hi)."""
    ec = np.sqrt(edges[:-1] * edges[1:]); w = np.diff(edges)
    return np.sum((rate * w)[:, (ec >= lo) & (ec < hi)], 1)


def v2_representations(rate, edges, F):
    """A, B, H, HI exactly as in 07_train_eval.py (v2)."""
    b1, b2, b3, b4 = (band(rate, edges, *r) for r in [(5, 7), (7, 10), (10, 16), (16, 25.1)])
    assert (np.r_[b1, b3] > 0).all(), 'non-positive colour denominator'
    H = np.c_[b2 / b1, b4 / b3]
    return {'A_intensity': np.arcsinh(rate / ASINH_SCALE), 'B_shape': rate / F[:, None],
            'H_colours': H, 'HI_colours_intensity': np.c_[H, np.log10(F)]}


def run_loso(reps, y, g, oid, models=MODELS, folds=None):
    """Leave-one-source-out OOF predictions; asserts disjoint sources and both classes in every training set."""
    folds = folds if folds is not None else list(LeaveOneGroupOut().split(np.zeros(len(y)), y, g))
    for tr, te in folds:
        assert len(set(g[te])) == 1 and not (set(g[te]) & set(g[tr])) and set(y[tr]) == {0, 1}
    out = []
    for rep, X in reps.items():
        assert np.isfinite(X).all(), rep
        for mname, mk in models.items():
            for k, (tr, te) in enumerate(folds):
                m = mk().fit(X[tr], y[tr])
                p = m.predict_proba(X[te])[:, list(m.classes_).index(1)]
                out += [dict(representation=rep, model=mname, fold=k, source_id=g[i], obs_id=oid[i],
                             true_label='BH' if y[i] else 'NS', BH_score=float(s),
                             predicted_label='BH' if s >= SOURCE_THRESHOLD else 'NS') for i, s in zip(te, p)]
            print(f'  {rep:<24s} {mname:<12s} done', flush=True)
    return pd.DataFrame(out), folds


def per_source(d):
    ps = d.assign(correct=d.true_label == d.predicted_label).groupby('source_id').agg(
        true_label=('true_label', 'first'), n_obs=('obs_id', 'size'), obs_accuracy=('correct', 'mean'),
        mean_BH_score=('BH_score', 'mean'))
    ps['source_pred'] = np.where(ps.mean_BH_score >= SOURCE_THRESHOLD, 'BH', 'NS')
    ps['source_correct'] = ps.source_pred == ps.true_label
    return ps


def metric_triplet(ps_sub, o_sub):
    """(observation balanced acc, source balanced acc, source AUC) for a (possibly bootstrap-resampled) set."""
    t = (o_sub.true_label == 'BH').astype(int); p = (o_sub.predicted_label == 'BH').astype(int)
    st = (ps_sub.true_label == 'BH').astype(int); sp = (ps_sub.source_pred == 'BH').astype(int)
    return (balanced_accuracy_score(t, p), balanced_accuracy_score(st, sp), roc_auc_score(st, ps_sub.mean_BH_score))


def point_metrics(oof):
    rows, pss = [], []
    for (rep, m), d in oof.groupby(['representation', 'model'], sort=False):
        ps = per_source(d); pss.append(ps.reset_index().assign(representation=rep, model=m))
        t = (d.true_label == 'BH').astype(int); p = (d.predicted_label == 'BH').astype(int)
        ob, sb, sa = metric_triplet(ps, d)
        rows.append(dict(representation=rep, model=m, n_obs=len(d), n_sources=len(ps),
                         BH_recall=recall_score(t, p, pos_label=1), NS_recall=recall_score(t, p, pos_label=0),
                         obs_balanced_accuracy=ob, obs_AUC=roc_auc_score(t, d.BH_score),
                         source_balanced_accuracy=sb, source_AUC=sa,
                         BH_sources_correct=f"{int(ps[ps.true_label=='BH'].source_correct.sum())}/{int((ps.true_label=='BH').sum())}",
                         NS_sources_correct=f"{int(ps[ps.true_label=='NS'].source_correct.sum())}/{int((ps.true_label=='NS').sum())}",
                         misclassified_sources=';'.join(ps.index[~ps.source_correct])))
    return pd.DataFrame(rows), pd.concat(pss)


def bootstrap(oof, pairs, n_boot=2000, seed=SEED):
    """Source-level bootstrap within class (same procedure as 09_bootstrap_sources.py), fixed OOF predictions."""
    names = ['obs_balanced_accuracy', 'source_balanced_accuracy', 'source_AUC']
    anyd = oof.drop_duplicates('source_id')
    bh = anyd[anyd.true_label == 'BH'].source_id.values; ns = anyd[anyd.true_label == 'NS'].source_id.values
    # keep source order identical to 09_bootstrap_sources.py (per_source_results order = sorted source_id)
    bh, ns = np.sort(bh), np.sort(ns)
    rng = np.random.default_rng(seed)
    draws = [np.r_[rng.choice(bh, len(bh)), rng.choice(ns, len(ns))] for _ in range(n_boot)]
    boot, rows = {}, []
    for (rep, m), d in oof.groupby(['representation', 'model'], sort=False):
        ps = per_source(d)
        pt = metric_triplet(ps, d)
        # vectorised, exact equivalent of metric_triplet on resampled sources
        pos = {s: i for i, s in enumerate(ps.index)}
        idx = np.array([[pos[x] for x in s] for s in draws])            # (n_boot, n_sources)
        isbh = (ps.true_label == 'BH').values; nc = (ps.obs_accuracy * ps.n_obs).round().values; nn = ps.n_obs.values
        sc = ps.source_correct.values.astype(float); sco = ps.mean_BH_score.values
        bhm = isbh[idx]                                                   # same pattern every row (class-stratified)
        ob = 0.5 * ((nc[idx] * bhm).sum(1) / (nn[idx] * bhm).sum(1) + (nc[idx] * ~bhm).sum(1) / (nn[idx] * ~bhm).sum(1))
        sb = 0.5 * ((sc[idx] * bhm).sum(1) / bhm.sum(1) + (sc[idx] * ~bhm).sum(1) / (~bhm).sum(1))
        s1, s0 = sco[idx][bhm].reshape(len(draws), -1), sco[idx][~bhm].reshape(len(draws), -1)
        gt = (s1[:, :, None] > s0[:, None, :]).mean((1, 2)); eq = (s1[:, :, None] == s0[:, None, :]).mean((1, 2))
        B = np.c_[ob, sb, gt + 0.5 * eq]                                  # AUC = P(score_BH > score_NS) + ties/2
        boot[(rep, m)] = (np.array(pt), B)
        for k, n in enumerate(names):
            rows.append(dict(comparison=rep, model=m, metric=n, point=pt[k],
                             ci2_5=np.percentile(B[:, k], 2.5), ci97_5=np.percentile(B[:, k], 97.5)))
    for r1, r2 in pairs:
        for m in MODELS:
            if (r1, m) not in boot or (r2, m) not in boot: continue
            (p1, B1), (p2, B2) = boot[(r1, m)], boot[(r2, m)]
            dB = B1 - B2
            for k, n in enumerate(names):
                rows.append(dict(comparison=f'{r1} - {r2}', model=m, metric=n, point=p1[k] - p2[k],
                                 ci2_5=np.percentile(dB[:, k], 2.5), ci97_5=np.percentile(dB[:, k], 97.5),
                                 frac_first_better=float(np.mean(dB[:, k] > 0))))
    return pd.DataFrame(rows)


def agreement(oof, r1, r2):
    rows = []
    for m in MODELS:
        a = oof[(oof.representation == r1) & (oof.model == m)].set_index('obs_id')
        b = oof[(oof.representation == r2) & (oof.model == m)].set_index('obs_id').loc[a.index]
        rows.append(dict(pair=f'{r1} vs {r2}', model=m, spearman_obs_scores=spearmanr(a.BH_score, b.BH_score)[0],
                         label_agreement=float((a.predicted_label == b.predicted_label).mean())))
    return rows
