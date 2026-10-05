"""v7c2 step 2 (preregistration_v7.md §6, 4c) + v7c3 (4d): strict pipeline on MAXI/GSC standard products.
Features per 1-day point (L=2-4, M=4-10, H=10-20 keV): SC=(M-L)/(M+L), HC=(H-L)/(H+L), RelInt=(L+M+H)/99.99th percentile
of that source; C4=(H-M)/(H+M) (>= 4 keV only). Feature sets: CCI=[SC,HC,RelInt], C2D=[SC,HC], C1D=[C4].
Main task BH vs NPNS (LR, RF fixed; KNN k in grid and SVM C x gamma in grid selected by inner LOSO source AUC);
secondary BH vs PSR (LR, RF only). LOSO over sources; <= 200 random points per training source (seed 42); test on all points.
Source score = mean point score; threshold 0.5. PRIMARY: LR (i) CCI - C2D and (ii) C2D - C1D (source BA, source AUC).
v7c3: sources in both the RXTE samples and the MAXI main sample: RXTE H-LR source score vs MAXI LR (CCI) source score."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v7c'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import config as C
import v4lib as L
import v7lib as L7
from plotstyle import plt, CLASS_COLOR, INK2

R7, FG = ROOT/'results/v7c', ROOT/'figures/v7c'
for p in (R7, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
T0 = time.time()
pts = pd.read_csv(ROOT/'data/v7c/maxi_points.csv')
pts['SC'] = (pts.M - pts.L) / (pts.M + pts.L); pts['HC'] = (pts.H - pts.L) / (pts.H + pts.L); pts['C4'] = (pts.H - pts.M) / (pts.H + pts.M)
tot = pts.L + pts.M + pts.H
pts['RelInt'] = tot / pts.assign(t=tot).groupby('source').t.transform(lambda s: np.percentile(s, 99.99))
pts['obs_id'] = pts.source + '_' + pts.mjd.round(1).astype(str)
FS = {'CCI': ['SC', 'HC', 'RelInt'], 'C2D': ['SC', 'HC'], 'C1D': ['C4']}
GRID = {'KNN': [dict(k=k) for k in C.V7_C2_KNN_GRID], 'SVM': [dict(C=c, gamma=g) for c in C.V7_C2_SVM_GRID['C'] for g in C.V7_C2_SVM_GRID['gamma']]}
SMOKE = os.environ.get('V7C_SMOKE') == '1'
if SMOKE:                                                     # quick end-to-end check only (results not used)
    GRID = {k: v[:2] for k, v in GRID.items()}; R7 = R7/'smoke'; FG = FG/'smoke'; R7.mkdir(exist_ok=True); FG.mkdir(exist_ok=True)
    keep = [s for c in ('BH', 'NPNS', 'PSR') for s in pts[pts.cls == c].source.unique()[:4]]; pts = pts[pts.source.isin(keep)]


class M:
    def __init__(self, alg, cfg=None): self.alg, self.cfg = alg, cfg or {}
    def fit(self, X, y):
        a = self.alg; self.pi = y.mean()
        if a == 'LR': self.m = make_pipeline(StandardScaler(), LogisticRegression(**C.LR_PARAMS)).fit(X, y)
        elif a == 'RF': self.m = RandomForestClassifier(**dict(C.RF_PARAMS, n_jobs=1)).fit(X, y)
        elif a == 'KNN': self.m = make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=self.cfg['k'])).fit(X, y)
        else: self.m = make_pipeline(StandardScaler(), SVC(C=self.cfg['C'], gamma=self.cfg['gamma'], class_weight='balanced')).fit(X, y)
        return self
    def score(self, X):
        if self.alg == 'SVM': return expit(self.m.decision_function(X))
        p = self.m.predict_proba(X)[:, 1]
        if self.alg == 'KNN':
            q1, q0 = p / self.pi, (1 - p) / (1 - self.pi); return q1 / (q1 + q0)
        return p


def capped(df, rng_seed=C.SEED):
    rng = np.random.default_rng(rng_seed)
    return pd.concat([d if len(d) <= C.V7_MAXI_TRAIN_CAP else d.iloc[np.sort(rng.choice(len(d), C.V7_MAXI_TRAIN_CAP, replace=False))]
                      for _, d in df.groupby('source', sort=True)])


def src_auc(scores, df):
    s = pd.DataFrame(dict(s=scores, y=df.y.values, g=df.source.values)).groupby('g').agg(s=('s', 'mean'), y=('y', 'first'))
    y, v = s.y.values.astype(bool), s.s.values
    if y.sum() == 0 or (~y).sum() == 0: return np.nan
    return float((v[y][:, None] > v[~y][None, :]).mean() + 0.5 * (v[y][:, None] == v[~y][None, :]).mean())


def outer(test_src, data, alg, cols):
    tr = capped(data[data.source != test_src]); te = data[data.source == test_src]
    cfg, inner = None, []
    if alg in GRID:
        best = (-1, None)
        for ci, c in enumerate(GRID[alg]):
            sc = np.full(len(tr), np.nan)
            for s in tr.source.unique():
                itr, ite = tr.source != s, tr.source == s
                if tr[itr].y.nunique() < 2: continue
                sc[ite.values] = M(alg, c).fit(tr[itr][cols].values, tr[itr].y.values).score(tr[ite][cols].values)
            a = src_auc(sc, tr); inner.append(dict(test_source=test_src, alg=alg, cfg=str(c), inner_source_AUC=a))
            if a > best[0] + 1e-12: best = (a, c)
        cfg = best[1]
    s = M(alg, cfg).fit(tr[cols].values, tr.y.values).score(te[cols].values)
    return test_src, alg, str(cfg), s, inner


def oof_frame(res, data, name):
    rows = []
    for src, alg, cfg, s, _ in res:
        te = data[data.source == src]
        rows.append(pd.DataFrame(dict(source_id=src, obs_id=te.obs_id.values, true_label=np.where(te.y.values == 1, 'BH', 'NS'),
                                      BH_score=s, predicted_label=np.where(s >= 0.5, 'BH', 'NS'), model=name, cfg=cfg)))
    return pd.concat(rows, ignore_index=True)


TASKS = {'main: BH vs NPNS': ('BH', 'NPNS', ['LR', 'RF', 'KNN', 'SVM']), 'secondary: BH vs PSR': ('BH', 'PSR', ['LR', 'RF'])}
oofs, inners, bs = {}, [], []
for task, (c1, c0, algs) in TASKS.items():
    data = pts[pts.cls.isin([c1, c0])].copy(); data['y'] = (data.cls == c1).astype(int)
    srcs = sorted(data.source.unique())
    print(f'\n[{task}] {len(srcs)} sources ({data[data.y == 1].source.nunique()} BH), {len(data)} points', flush=True)
    for alg in algs:
        for fs, cols in FS.items():
            cdir = R7/'cache'; cdir.mkdir(exist_ok=True); tag = task.split(':')[0]
            akey = alg + ('_gkf5' if alg == 'SVM' else '')     # SVM inner tuning: grouped 5-fold (see decision_log)
            res = Parallel(n_jobs=16)(delayed(L7.c2_outer_cached)(str(cdir/f'{tag}_{akey}_{fs}_{s}.pkl'), s, data, alg, cols, GRID, C.V7_MAXI_TRAIN_CAP, C.SEED) for s in srcs)
            name = f'{alg} [{fs}]'
            oofs[(task, name)] = oof_frame(res, data, name)
            inners += [dict(task=task, feature_set=fs, **x) for r in res for x in r[4]]
            print(f'  {name} done ({time.time()-T0:.0f} s)', flush=True)
            pd.concat([v.assign(task=t) for (t, n), v in oofs.items()]).to_csv(R7/'v7c2_oof_predictions.csv.gz', index=False)
        for ref, cmp_, lab in (('C2D', 'CCI', '(i) CCI vs 2D colours'), ('C1D', 'C2D', '(ii) colours incl. 2-4 keV vs >= 4 keV colour')):
            b = L.paired_bootstrap({f'{alg} [{ref}]': oofs[(task, f'{alg} [{ref}]')], f'{alg} [{cmp_}]': oofs[(task, f'{alg} [{cmp_}]')]}, f'{alg} [{ref}]')
            b['task'] = task; b['model'] = alg; b['comparison_set'] = lab
            b['role'] = 'PRIMARY' if (task.startswith('main') and alg == 'LR') else 'descriptive'; bs.append(b)
    pd.DataFrame(inners).to_csv(R7/'v7c2_inner_selection.csv', index=False)
bs = pd.concat(bs, ignore_index=True); bs.to_csv(R7/'v7c2_bootstrap.csv', index=False)
t = bs.copy(); t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
print('\n' + t.pivot_table(index=['task', 'comparison_set', 'comparison'], columns='metric', values='txt', aggfunc='first').to_string())
ps = pd.concat([L.src_table(v).assign(task=tk, model=n) for (tk, n), v in oofs.items()]).reset_index()
ps = ps.merge(pts.drop_duplicates('source')[['source', 'name']].rename(columns={'source': 'source_id'}), on='source_id', how='left')
ps.to_csv(R7/'v7c2_per_source.csv', index=False)
print('\nmain task, BH sources (mean score):\n' + ps[(ps.task.str.startswith('main')) & (ps.true_label == 'BH')]
      .pivot_table(index='name', columns='model', values='score').round(2).to_string())

# ---------------- v7c3: RXTE vs MAXI for shared sources ----------------
mx = pd.read_csv(ROOT/'data/v7c/c2_sources.csv'); mx = mx[mx.included & mx.cls.isin(['BH', 'NPNS'])]
import v7lib as L7
rx = []
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
for s, d in v2[(v2.representation == 'H_colours') & (v2.model == 'LogReg')].groupby('source_id'): rx.append(dict(rxte_source=s, rxte_score=d.BH_score.mean(), rxte_sample='v2 H-LR'))
v4 = pd.read_csv(ROOT/'results/v4b2/v4b2_oof_predictions.csv', dtype={'obs_id': str})
v4src = set(pd.read_csv(ROOT/'data/v4b2/sources.csv').source_id)
for s, d in v4[(v4.representation == 'H_count_space') & (v4.model == 'LogReg') & v4.source_id.isin(v4src)].groupby('source_id'): rx.append(dict(rxte_source=s, rxte_score=d.BH_score.mean(), rxte_sample='v4b2 H-LR (46 sources)'))
v7 = pd.read_csv(ROOT/'results/v7b2/v7b2_oof_predictions.csv', dtype={'obs_id': str})
for s, d in v7[(v7.run.str.startswith('main')) & (v7.representation == 'H_colours') & (v7.model == 'LogReg') & v7.source_id.isin(['CYGX1', 'LMCX1', 'LMCX3'])].groupby('source_id'):
    rx.append(dict(rxte_source=s, rxte_score=d.BH_score.mean(), rxte_sample='v7b2 H-LR (34 sources)'))
rx = pd.DataFrame(rx)
rxpos = pd.concat([pd.read_csv(ROOT/f'data/{v}/sources.csv')[['source_id', 'ra_deg', 'dec_deg', 'label']] for v in ('v2', 'v4b2', 'v7b2')]).drop_duplicates('source_id')
rx = rx.merge(rxpos, left_on='rxte_source', right_on='source_id')
mxs = ps[(ps.task.str.startswith('main')) & (ps.model == 'LR [CCI]')][['source_id', 'name', 'true_label', 'score']].rename(columns={'source_id': 'maxi_id', 'score': 'maxi_score'})
mxs = mxs.merge(pd.read_csv(ROOT/'data/v7c/c2_sources_matched.csv')[['maxi_id', 'ra', 'dec']].drop_duplicates('maxi_id'), on='maxi_id')
pairs = []
for r in mxs.itertuples():
    d = L7.sep_deg(rx.ra_deg.values, rx.dec_deg.values, r.ra, r.dec); k = int(np.argmin(d))
    if d[k] <= 0.1: pairs.append(dict(maxi_name=r.name, maxi_id=r.maxi_id, rxte_source=rx.rxte_source.iloc[k], label=r.true_label,
                                      rxte_label=rx.label.iloc[k], rxte_sample=rx.rxte_sample.iloc[k], rxte_score=rx.rxte_score.iloc[k], maxi_score=r.maxi_score, sep_deg=d[k]))
pr = pd.DataFrame(pairs); pr.to_csv(R7/'v7c3_rxte_vs_maxi.csv', index=False)
agree = float(((pr.rxte_score >= .5) == (pr.maxi_score >= .5)).mean()) if len(pr) else np.nan
rho = spearmanr(pr.rxte_score, pr.maxi_score)[0] if len(pr) > 2 else np.nan
print(f'\n[v7c3] {len(pr)} shared sources ({int((pr.label == "BH").sum())} BH): Spearman {rho:.3f}, label agreement {agree:.3f}\n' + pr.round(3).to_string(index=False))
fig, a = plt.subplots(figsize=(5.5, 5))
for lab in ('NS', 'BH'):
    d = pr[pr.label == lab]; a.scatter(d.rxte_score, d.maxi_score, s=30, color=CLASS_COLOR[lab], label=lab)
    for _, r in d.iterrows(): a.annotate(r.rxte_source, (r.rxte_score, r.maxi_score), fontsize=5.5, xytext=(2, 2), textcoords='offset points')
a.axhline(.5, color=INK2, ls='--', lw=.6); a.axvline(.5, color=INK2, ls='--', lw=.6); a.plot([0, 1], [0, 1], color=INK2, lw=.5)
a.set_xlabel('RXTE/PCA source score (H-LR, LOSO)'); a.set_ylabel('MAXI/GSC source score (LR, CCI, LOSO)'); a.legend(frameon=False, fontsize=7)
a.set_title(f'v7c3: same sources, two instruments (rho = {rho:.2f}, agreement {agree:.2f})', loc='left', fontsize=8)
fig.savefig(FG/'v7c3_rxte_vs_maxi.png'); plt.close(fig)
prim = bs[(bs.role == 'PRIMARY') & bs.comparison.str.contains(' - ')]
progress('v7c2_analysis', '; '.join(f"{r.comparison_set} {r.metric} {r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]" for r in prim[prim.metric != 'obs_balanced_accuracy'].itertuples()))
print(f'total {time.time()-T0:.0f} s')
