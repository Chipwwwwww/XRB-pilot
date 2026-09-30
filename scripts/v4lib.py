"""Shared helpers for v4 (reports/preregistration_v4.md). Import with XRB_VERSION starting with 'v4'.
Models, class-imbalance handling, nested LOSO selection and the paired source-level bootstrap."""
import os, warnings
os.environ.setdefault('XRB_VERSION', 'v4')
import numpy as np, pandas as pd
from scipy.stats import spearmanr
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', message='.*[Cc]ollinear.*')
warnings.filterwarnings('ignore', message='.*converge.*')
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings('ignore', category=ConvergenceWarning)
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score
import config as C
from v3lib import LR_PARAMS, RF_PARAMS, v2_representations, band

SCALED = {'LogReg', 'SVM_RBF', 'kNN', 'QDA', 'MLP'}
ALGS = list(C.V4_GRID)                      # fixed order used for tie-breaking
REPS = list(C.V4_REPRESENTATIONS)
THRESHOLD = 0.5


def balanced_weights(y):
    y = np.asarray(y); w = np.empty(len(y))
    for c in (0, 1): w[y == c] = len(y) / (2.0 * (y == c).sum())
    return w


def source_equal_weights(y, g):
    """w_i = 1 / (n training sources in class(i) * n training obs of source(i)); each class sums to 1."""
    y, g = np.asarray(y), np.asarray(g); w = np.empty(len(y))
    for c in (0, 1):
        srcs = np.unique(g[y == c])
        for s in srcs:
            m = g == s; w[m] = 1.0 / (len(srcs) * m.sum())
    return w


class V4Model:
    """alg in ALGS; cfg = grid entry (or {} for the fixed 1b setting); stage in {'fixed','inner','outer'}.
    fit(X, y, w): w=None -> balanced class handling as preregistered; w given -> sample_weight (1c)."""

    def __init__(self, alg, cfg=None, stage='fixed'):
        self.alg, self.cfg, self.stage = alg, dict(cfg or {}), stage

    def _trees(self):
        return C.V4_INNER_TREES if self.stage == 'inner' else C.V4_OUTER_TREES

    def fit(self, X, y, w=None):
        a, c = self.alg, self.cfg
        y = np.asarray(y)
        self.scaler = StandardScaler().fit(X) if a in SCALED else None
        Xs = self.scaler.transform(X) if self.scaler is not None else X
        bal = w is None
        self.pi = float(y.mean())
        if a == 'LogReg':
            p = dict(LR_PARAMS); p['C'] = c.get('C', p['C'])
            if not bal: p['class_weight'] = None
            self.m = LogisticRegression(**p).fit(Xs, y, sample_weight=w)
        elif a in ('RandomForest', 'ExtraTrees'):
            p = dict(RF_PARAMS) if a == 'RandomForest' else dict(C.V4_FIXED['ExtraTrees'])
            p.update(n_jobs=1, n_estimators=self._trees(), min_samples_leaf=c.get('min_samples_leaf', p['min_samples_leaf']))
            if not bal: p['class_weight'] = None
            self.m = (RandomForestClassifier if a == 'RandomForest' else ExtraTreesClassifier)(**p).fit(Xs, y, sample_weight=w)
        elif a == 'HistGB':
            p = dict(C.V4_FIXED['HistGB']); p.update({k: v for k, v in c.items() if k in ('learning_rate', 'max_leaf_nodes')})
            if not bal: p['class_weight'] = None
            self.m = HistGradientBoostingClassifier(**p).fit(Xs, y, sample_weight=w)
        elif a == 'SVM_RBF':
            p = dict(C.V4_FIXED['SVM_RBF']); p['C'] = c.get('C', p['C'])
            if 'gamma_factor' in c: p['gamma'] = c['gamma_factor'] / (Xs.shape[1] * Xs.var())   # factor x 'scale'
            self.m = SVC(**p).fit(Xs, y)
        elif a == 'kNN':
            p = dict(C.V4_FIXED['kNN']); p['n_neighbors'] = min(c.get('n_neighbors', p['n_neighbors']), len(y))
            self.m = KNeighborsClassifier(**p).fit(Xs, y)
        elif a == 'QDA':
            p = dict(C.V4_FIXED['QDA']); p['reg_param'] = c.get('reg_param', p['reg_param'])
            self.m = QuadraticDiscriminantAnalysis(**p).fit(Xs, y)
        elif a == 'MLP':
            p = dict(C.V4_FIXED['MLP']); p.update({k: v for k, v in c.items() if k in ('hidden_layer_sizes', 'alpha')})
            seeds = C.V4_MLP_SEEDS_INNER if self.stage == 'inner' else C.V4_MLP_SEEDS_OUTER
            sw = balanced_weights(y) if bal else w
            self.ms = [MLPClassifier(random_state=s, **p).fit(Xs, y, sample_weight=sw) for s in seeds]
        else:
            raise ValueError(a)
        return self

    def score(self, X):
        Xs = self.scaler.transform(X) if self.scaler is not None else X
        a = self.alg
        if a == 'MLP':
            return np.mean([m.predict_proba(Xs)[:, list(m.classes_).index(1)] for m in self.ms], axis=0)
        if a == 'SVM_RBF':
            return 1.0 / (1.0 + np.exp(-self.m.decision_function(Xs)))
        p = self.m.predict_proba(Xs)[:, list(self.m.classes_).index(1)]
        if a == 'kNN':                                   # prior correction to equal class priors
            q1, q0 = p / self.pi, (1 - p) / (1 - self.pi)
            return q1 / (q1 + q0)
        return p


def loso_scores(X, y, g, folds, alg, cfg=None, weighting=None, stage='fixed'):
    """OOF BH scores; weighting None (balanced class handling) or 'source_equal' (1c)."""
    s = np.full(len(y), np.nan)
    for tr, te in folds:
        w = source_equal_weights(y[tr], g[tr]) if weighting == 'source_equal' else None
        s[te] = V4Model(alg, cfg, stage).fit(X[tr], y[tr], w).score(X[te])
    return s


def src_means(scores, y, g):
    d = pd.DataFrame(dict(s=scores, y=y, g=g)).groupby('g').agg(s=('s', 'mean'), y=('y', 'first'))
    return d.s.values, d.y.values


def bal_acc(y, pred):
    y, pred = np.asarray(y).astype(bool), np.asarray(pred).astype(bool)
    return 0.5 * (pred[y].mean() + (~pred[~y]).mean())


def choose_threshold(ss, sy):
    """Maximise source balanced accuracy over midpoints of sorted unique source scores; ties -> closest to 0.5."""
    u = np.unique(ss)
    cands = np.r_[u[0] - 1e-9, (u[:-1] + u[1:]) / 2, u[-1] + 1e-9]
    ba = np.array([bal_acc(sy, ss >= t) for t in cands])
    best = ba.max(); opts = cands[np.isclose(ba, best, atol=1e-12)]
    t = float(opts[np.argmin(np.abs(opts - THRESHOLD))])
    return t, float(best)


def nested_fold(k, outer_tr, outer_te, Xs, y, g, grid=None, reps=None):
    """One outer fold of 1d/1e. Inner LOSO over the training sources for every (alg, rep, cfg);
    select per (alg, rep) by inner source AUC (ties: inner source BA, grid order); threshold by inner source BA;
    refit on all training sources (outer stage) and score the outer test observations."""
    grid = grid or C.V4_GRID; reps = reps or REPS
    ytr, gtr = y[outer_tr], g[outer_tr]
    inner = list(LeaveOneGroupOut().split(np.zeros(len(ytr)), ytr, gtr))
    rows, preds = [], []
    for ri, rep in enumerate(reps):
        Xtr = Xs[rep][outer_tr]
        for ai, alg in enumerate(ALGS):
            if alg not in grid: continue
            cand = []
            for ci, cfg in enumerate(grid[alg]):
                s = loso_scores(Xtr, ytr, gtr, inner, alg, cfg, stage='inner')
                ss, sy = src_means(s, ytr, gtr)
                auc = roc_auc_score(sy, ss); t, ba = choose_threshold(ss, sy)
                rows.append(dict(fold=k, representation=rep, algorithm=alg, config_index=ci, config=str(cfg),
                                 inner_source_AUC=auc, inner_source_BA=ba, inner_threshold=t))
                cand.append((round(auc, 12), round(ba, 12), -ci, ci, cfg, t, auc, ba))
            best = max(cand, key=lambda z: z[:3])
            ci, cfg, t, auc, ba = best[3], best[4], best[5], best[6], best[7]
            m = V4Model(alg, cfg, 'outer').fit(Xtr, ytr)
            sc = m.score(Xs[rep][outer_te])
            preds.append(dict(fold=k, representation=rep, algorithm=alg, config_index=ci, config=str(cfg),
                              threshold=t, inner_source_AUC=auc, inner_source_BA=ba,
                              rep_order=ri, alg_order=ai, idx=outer_te, raw=sc))
    return rows, preds


# ---------------- evaluation ----------------
def to_oof(idx, raw, thr, y, g, oid, rep, model, fold=None):
    """Rows with BH_score = raw - thr + 0.5 so that the fixed 0.5 rule reproduces the fold-specific threshold."""
    adj = raw - thr + THRESHOLD
    return pd.DataFrame(dict(representation=rep, model=model, fold=fold, source_id=g[idx], obs_id=oid[idx],
                             true_label=np.where(y[idx] == 1, 'BH', 'NS'), BH_score=adj, raw_score=raw, threshold=thr,
                             predicted_label=np.where(adj >= THRESHOLD, 'BH', 'NS')))


def src_table(d):
    t = d.assign(c=(d.true_label == d.predicted_label)).groupby('source_id').agg(
        true_label=('true_label', 'first'), n=('obs_id', 'size'), nc=('c', 'sum'), score=('BH_score', 'mean'))
    t['source_pred'] = np.where(t.score >= THRESHOLD, 'BH', 'NS'); t['sc'] = (t.source_pred == t.true_label).astype(float)
    return t


def _boot_metrics(t, idx, bhm):
    nc, nn, sc, sco = t.nc.values.astype(float), t.n.values.astype(float), t.sc.values, t.score.values
    ob = 0.5 * ((nc[idx] * bhm).sum(1) / (nn[idx] * bhm).sum(1) + (nc[idx] * ~bhm).sum(1) / (nn[idx] * ~bhm).sum(1))
    sb = 0.5 * ((sc[idx] * bhm).sum(1) / bhm.sum(1) + (sc[idx] * ~bhm).sum(1) / (~bhm).sum(1))
    nb = bhm[0].sum()
    s1, s0 = sco[idx][bhm].reshape(len(idx), nb), sco[idx][~bhm].reshape(len(idx), -1)
    auc = (s1[:, :, None] > s0[:, None, :]).mean((1, 2)) + 0.5 * (s1[:, :, None] == s0[:, None, :]).mean((1, 2))
    return np.c_[sb, auc, ob]


METRICS = ['source_balanced_accuracy', 'source_AUC', 'obs_balanced_accuracy']


def paired_bootstrap(oofs, ref, n_boot=2000, seed=42):
    """oofs: {name: oof DataFrame}. Class-stratified source bootstrap with the same draws as v3lib/09_bootstrap
    (sorted BH / NS source names, np.random.default_rng(seed)). Returns point/CI per name and paired differences vs ref."""
    tabs = {k: src_table(v) for k, v in oofs.items()}
    t0 = tabs[ref]
    bh = np.sort(t0.index[t0.true_label == 'BH'].values); ns = np.sort(t0.index[t0.true_label == 'NS'].values)
    rng = np.random.default_rng(seed)
    draws = [np.r_[rng.choice(bh, len(bh)), rng.choice(ns, len(ns))] for _ in range(n_boot)]
    order = np.r_[bh, ns]
    ident = order[None, :]
    rows, B, P = [], {}, {}
    for k, t in tabs.items():
        assert set(t.index) == set(order), f'{k}: source set differs from reference'
        t = t.loc[order]
        pos = {s: i for i, s in enumerate(t.index)}
        idx = np.array([[pos[x] for x in d] for d in draws]); bhm = (t.true_label == 'BH').values[idx]
        B[k] = _boot_metrics(t, idx, bhm)
        i0 = np.arange(len(order))[None, :]; P[k] = _boot_metrics(t, i0, (t.true_label == 'BH').values[i0])[0]
        for j, n in enumerate(METRICS):
            rows.append(dict(name=k, comparison=k, metric=n, point=P[k][j], ci2_5=np.percentile(B[k][:, j], 2.5),
                             ci97_5=np.percentile(B[k][:, j], 97.5)))
    for k in tabs:
        if k == ref: continue
        dB = B[k] - B[ref]
        for j, n in enumerate(METRICS):
            lo, hi = np.percentile(dB[:, j], 2.5), np.percentile(dB[:, j], 97.5)
            rows.append(dict(name=k, comparison=f'{k} - {ref}', metric=n, point=P[k][j] - P[ref][j], ci2_5=lo, ci97_5=hi,
                             frac_first_better=float(np.mean(dB[:, j] > 0)),
                             verdict='improvement' if lo > 0 else 'not detected'))
    return pd.DataFrame(rows)


def agreement_vs(oofs, ref):
    r = oofs[ref].set_index('obs_id')
    out = []
    for k, d in oofs.items():
        if k == ref: continue
        d = d.set_index('obs_id'); common = r.index.intersection(d.index)
        a, b = r.loc[common], d.loc[common]
        out.append(dict(name=k, n_obs=len(common), spearman_obs_scores=spearmanr(a.BH_score, b.BH_score)[0],
                        label_agreement=float((a.predicted_label == b.predicted_label).mean())))
    return pd.DataFrame(out)
