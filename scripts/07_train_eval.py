"""Step 4 (+5 representations): leave-one-source-out evaluation of Dummy / LogisticRegression / RandomForest
on representation A (intensity kept) and B (per-spectrum shape normalised). Same samples and folds for all."""
from common import *
from config import *
from plotstyle import *
import numpy as np, pandas as pd, json
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold
from sklearn.metrics import confusion_matrix, recall_score, balanced_accuracy_score

z = np.load(ROOT/'data/processed/features.npz')
rate, F, y, g, oid = z['rate'], z['F'], z['y'], z['source_id'], z['obs_id']
W = np.diff(z['edges'])
REPS = {'A_intensity': np.arcsinh(rate / ASINH_SCALE),        # per-spectrum: none; keeps count-rate level
        'B_shape': rate / F[:, None]}                            # per-spectrum: divide by own 5-25 keV net rate
assert np.all(F > 0)
MODELS = {'Dummy': lambda: DummyClassifier(strategy='prior'),
          'LogReg': lambda: make_pipeline(StandardScaler(), LogisticRegression(**LR_PARAMS)),  # scaler fit on train only
          'RandomForest': lambda: RandomForestClassifier(**RF_PARAMS)}

folds = list(LeaveOneGroupOut().split(rate, y, g))
fold_tab, checks = [], []
for k, (tr, te) in enumerate(folds):
    ts = sorted(set(g[te])); trs = set(g[tr])
    ok = (len(ts) == 1) and not (set(ts) & trs) and set(y[tr]) == {0, 1}
    checks.append(dict(fold=k, test_source=ts[0], n_train=len(tr), n_test=len(te), train_BH=int(y[tr].sum()),
                       train_NS=int((1-y[tr]).sum()), train_sources=len(trs), disjoint_and_both_classes=ok))
    assert ok
    fold_tab += [dict(obs_id=oid[i], source_id=g[i], fold=k) for i in te]
pd.DataFrame(fold_tab).to_csv(ROOT/'results/folds_loso.csv', index=False)
pd.DataFrame(checks).to_csv(ROOT/'results/fold_checks.csv', index=False)

oof = []
for rep, X in REPS.items():
    assert np.isfinite(X).all()
    for mname, mk in MODELS.items():
        for k, (tr, te) in enumerate(folds):
            m = mk().fit(X[tr], y[tr])
            p = m.predict_proba(X[te])[:, list(m.classes_).index(1)]
            for i, s in zip(te, p):
                oof.append(dict(representation=rep, model=mname, fold=k, source_id=g[i], obs_id=oid[i],
                                true_label='BH' if y[i] else 'NS', BH_score=float(s),
                                predicted_label='BH' if s >= 0.5 else 'NS'))
        print(rep, mname, 'done', flush=True)
oof = pd.DataFrame(oof)
oof.to_csv(ROOT/'results/oof_predictions_loso.csv', index=False)

# ---- metrics ----
obs_rows, src_rows, per_src = [], [], []
for (rep, mname), d in oof.groupby(['representation', 'model'], sort=False):
    t = (d.true_label == 'BH').astype(int); p = (d.predicted_label == 'BH').astype(int)
    cm = confusion_matrix(t, p, labels=[1, 0])
    ps = d.assign(correct=d.true_label == d.predicted_label).groupby('source_id').agg(
        true_label=('true_label', 'first'), n_obs=('obs_id', 'size'), obs_accuracy=('correct', 'mean'),
        mean_BH_score=('BH_score', 'mean'), median_BH_score=('BH_score', 'median'))
    ps['source_pred'] = np.where(ps.mean_BH_score >= SOURCE_THRESHOLD, 'BH', 'NS')
    ps['source_correct'] = ps.source_pred == ps.true_label
    per_src.append(ps.reset_index().assign(representation=rep, model=mname))
    st = (ps.true_label == 'BH').astype(int); sp = (ps.source_pred == 'BH').astype(int)
    scm = confusion_matrix(st, sp, labels=[1, 0])
    obs_rows.append(dict(representation=rep, model=mname, n_obs=len(d), BH_recall=recall_score(t, p, pos_label=1, zero_division=0),
                         NS_recall=recall_score(t, p, pos_label=0, zero_division=0), balanced_accuracy=balanced_accuracy_score(t, p),
                         mean_per_source_accuracy=ps.obs_accuracy.mean(), min_per_source_accuracy=ps.obs_accuracy.min(),
                         cm_BHtrue_BHpred=cm[0, 0], cm_BHtrue_NSpred=cm[0, 1], cm_NStrue_BHpred=cm[1, 0], cm_NStrue_NSpred=cm[1, 1]))
    src_rows.append(dict(representation=rep, model=mname, n_sources=len(ps), sources_correct=int(ps.source_correct.sum()),
                         BH_sources_correct=f'{scm[0,0]}/{scm[0].sum()}', NS_sources_correct=f'{scm[1,1]}/{scm[1].sum()}',
                         source_balanced_accuracy=balanced_accuracy_score(st, sp),
                         misclassified_sources=';'.join(ps.index[~ps.source_correct])))
mo, ms, psdf = pd.DataFrame(obs_rows), pd.DataFrame(src_rows), pd.concat(per_src)
mo.to_csv(ROOT/'results/metrics_observation_level.csv', index=False)
ms.to_csv(ROOT/'results/metrics_source_level.csv', index=False)
psdf.to_csv(ROOT/'results/per_source_results.csv', index=False)
pd.set_option('display.width', 200)
print(mo.round(3).to_string(index=False)); print(ms.round(3).to_string(index=False))

# ---- secondary, pre-declared diagnostic: observation-wise stratified 5-fold (LEAKY: same source in train & test) ----
leak = []
skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
for rep, X in REPS.items():
    for mname in ['LogReg', 'RandomForest']:
        pred = np.zeros(len(y))
        for tr, te in skf.split(X, y):
            m = MODELS[mname]().fit(X[tr], y[tr]); pred[te] = m.predict_proba(X[te])[:, 1]
        leak.append(dict(representation=rep, model=mname, split='observation-wise 5-fold (sources shared)',
                         balanced_accuracy=balanced_accuracy_score(y, pred >= .5)))
pd.DataFrame(leak).to_csv(ROOT/'results/secondary_observation_split.csv', index=False)
print(pd.DataFrame(leak).round(3).to_string(index=False))

# ---- figures ----
src = pd.read_csv(ROOT/'data/sources.csv'); order = list(src.source_id); lab = dict(zip(src.source_id, src.label))
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
for a, rep in zip(axes, REPS):
    d = oof[(oof.representation == rep)]
    for j, mname in enumerate(MODELS):
        dm = d[d.model == mname]
        for i, s in enumerate(order):
            v = dm[dm.source_id == s].BH_score.values
            yy = i + (j-1)*0.25 + np.random.default_rng(i).uniform(-.07, .07, len(v))
            a.scatter(v, yy, s=9, color=['#9e9d98', '#4a3aa7', '#1baf7a'][j], alpha=.75, lw=0, label=mname if i == 0 else None)
            a.plot([v.mean()]*2, [i+(j-1)*.25-.1, i+(j-1)*.25+.1], color=INK, lw=2)
    a.axvline(0.5, color=INK2, ls='--', lw=.8)
    a.set_yticks(range(len(order))); a.set_yticklabels([f'{s} ({lab[s]})' for s in order]); a.invert_yaxis()
    a.set_xlabel('out-of-fold BH score (not a calibrated probability)'); a.set_title(rep, loc='left'); a.set_xlim(-.02, 1.02)
axes[0].legend(loc='lower center', bbox_to_anchor=(1.0, -0.32), ncol=3)
fig.suptitle('Leave-one-source-out BH scores per held-out source (black tick = source mean; dashed = 0.5 threshold)', x=0.01, ha='left')
fig.savefig(ROOT/'figures/step4_loso_scores.png'); plt.close(fig)
progress('4_train_eval', 'LOSO predictions/metrics written to results/')
