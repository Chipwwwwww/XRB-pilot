"""v4a (preregistration_v4.md §2): can another algorithm beat H-LR?  Uses only data/v2/processed/features.npz.
1a reproduction, 1b fixed-hyperparameter models, 1c source-equal weights, 1d nested per (algorithm, representation),
1e PRIMARY: nested automatic selection over all algorithms x representations (+ threshold) vs the v2 H-LR OOF.
Outputs results/v4/v4a_*, figures/v4/v4a_*.  Re-uses cached OOF files unless --retrain."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v4'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import LeaveOneGroupOut
import config as C
import v4lib as L
from v3lib import point_metrics
from plotstyle import plt, INK, INK2, CLASS_COLOR

R4, FG4 = ROOT/'results/v4', ROOT/'figures/v4'
for p in (R4, FG4): p.mkdir(parents=True, exist_ok=True)
N_JOBS = int(os.environ.get('V4_JOBS', 16)); RETRAIN = '--retrain' in sys.argv
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
T0 = time.time()

z = np.load(ROOT/'data/v2/processed/features.npz')
y, g, oid = z['y'], z['source_id'], z['obs_id']
reps = L.v2_representations(z['rate'], z['edges'], z['F'])
folds = list(LeaveOneGroupOut().split(np.zeros(len(y)), y, g))
ff = pd.read_csv(ROOT/'results/v2/folds_loso.csv', dtype={'obs_id': str})
assert all((ff[ff.fold == k].obs_id.values == oid[te]).all() for k, (tr, te) in enumerate(folds)), 'folds differ from v2'
fold_of = np.empty(len(y), int)
for k, (tr, te) in enumerate(folds): fold_of[te] = k
pd.DataFrame(dict(obs_id=oid, source_id=g, fold=fold_of)).to_csv(R4/'folds_loso.csv', index=False)
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
REF = 'H_colours|LogReg'
print(f'{len(y)} obs, {len(set(g))} sources; {N_JOBS} workers', flush=True)

# ---------------- 1a + 1b + 1c: fixed-hyperparameter LOSO ----------------
F_FILE = R4/'v4a_oof_fixed.csv'
if F_FILE.exists() and not RETRAIN:
    fixed = pd.read_csv(F_FILE, dtype={'obs_id': str}); print('re-using', F_FILE.name)
else:
    tasks = [(rep, alg, None) for rep in L.REPS for alg in L.ALGS] + \
            [(rep, alg, 'source_equal') for rep in L.REPS for alg in C.V4_SOURCE_WEIGHTED_MODELS]
    def run(rep, alg, w):
        return rep, alg, w, L.loso_scores(reps[rep], y, g, folds, alg, None, w)
    out = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(run)(*t) for t in tasks)
    parts = []
    for rep, alg, w, s in out:
        name = alg if w is None else f'{alg}[srcw]'
        d = L.to_oof(np.arange(len(y)), s, 0.5, y, g, oid, rep, name); d['fold'] = fold_of
        d['part'] = '1b_fixed' if w is None else '1c_source_weighted'
        parts.append(d)
    fixed = pd.concat(parts, ignore_index=True); fixed.to_csv(F_FILE, index=False)
print(f'fixed models done ({time.time()-T0:.0f} s)', flush=True)

# 1a reproduction check (LR logit-level, RF <= 0.01, 0 label changes)
rows = []
for rep in L.REPS:
    for alg, tol in (('LogReg', 1e-8), ('RandomForest', 0.01)):
        a = fixed[(fixed.representation == rep) & (fixed.model == alg)].set_index('obs_id').loc[oid]
        b = v2[(v2.representation == rep) & (v2.model == alg)].set_index('obs_id').loc[oid]
        d = np.abs(a.raw_score.values - b.BH_score.values)
        rows.append(dict(representation=rep, model=alg, max_abs_score_diff=d.max(), tolerance=tol,
                         n_label_changes=int((a.predicted_label.values != b.predicted_label.values).sum()),
                         passed=bool(d.max() <= tol and (a.predicted_label.values == b.predicted_label.values).all())))
repro = pd.DataFrame(rows); repro.to_csv(R4/'v4a_reproduction_check.csv', index=False)
print('\n1a reproduction:\n' + repro.to_string(index=False), flush=True)
if not repro.passed.all():
    print('REPRODUCTION FAILED -> stop (preregistration 1a)'); sys.exit(2)

# ---------------- 1d + 1e: nested LOSO ----------------
N_FILE, I_FILE, S_FILE = R4/'v4a_oof_nested.csv', R4/'v4a_nested_inner.csv', R4/'v4a_nested_selection.csv'
if N_FILE.exists() and not RETRAIN:
    nested = pd.read_csv(N_FILE, dtype={'obs_id': str}); sel = pd.read_csv(S_FILE); print('re-using', N_FILE.name)
else:
    res = Parallel(n_jobs=N_JOBS, verbose=10)(delayed(L.nested_fold)(k, tr, te, reps, y, g) for k, (tr, te) in enumerate(folds))
    inner = pd.DataFrame([r for rr, _ in res for r in rr]); inner.to_csv(I_FILE, index=False)
    parts, srows = [], []
    for k, (rr, preds) in enumerate(res):
        for p in preds:
            d = L.to_oof(p['idx'], p['raw'], p['threshold'], y, g, oid, p['representation'], f"nested:{p['algorithm']}", k)
            d['part'] = '1d_nested_per_algorithm'; parts.append(d)
        best = max(preds, key=lambda p: (round(p['inner_source_AUC'], 12), round(p['inner_source_BA'], 12),
                                         -p['alg_order'], -p['rep_order'], -p['config_index']))
        d = L.to_oof(best['idx'], best['raw'], best['threshold'], y, g, oid, 'auto', 'nested:auto', k)
        d['part'] = '1e_primary'; parts.append(d)
        srows.append(dict(fold=k, test_source=g[best['idx']][0], test_label='BH' if y[best['idx']][0] else 'NS',
                          algorithm=best['algorithm'], representation=best['representation'], config=best['config'],
                          threshold=best['threshold'], inner_source_AUC=best['inner_source_AUC'],
                          inner_source_BA=best['inner_source_BA'],
                          test_source_mean_raw=float(best['raw'].mean()),
                          test_source_pred='BH' if best['raw'].mean() >= best['threshold'] else 'NS'))
    nested = pd.concat(parts, ignore_index=True); nested.to_csv(N_FILE, index=False)
    sel = pd.DataFrame(srows); sel.to_csv(S_FILE, index=False)
print(f'nested done ({time.time()-T0:.0f} s)', flush=True)
print('\n1e selections per outer fold:\n' + sel.to_string(index=False), flush=True)

# ---------------- evaluation ----------------
ref = v2[(v2.representation == 'H_colours') & (v2.model == 'LogReg')].copy()
ref['raw_score'] = ref.BH_score; ref['threshold'] = 0.5; ref['part'] = 'reference_v2'
allo = pd.concat([ref, fixed[~((fixed.representation == 'H_colours') & (fixed.model == 'LogReg'))], nested], ignore_index=True)
allo.to_csv(R4/'v4a_oof_predictions.csv', index=False)
oofs = {f'{r}|{m}': d for (r, m), d in allo.groupby(['representation', 'model'], sort=False)}
part_of = {f'{r}|{m}': p for (r, m), p in allo.groupby(['representation', 'model'], sort=False).part.first().items()}
pm, ps = point_metrics(allo)
pm['name'] = pm.representation + '|' + pm.model; pm['part'] = pm.name.map(part_of)
pm.to_csv(R4/'v4a_metrics.csv', index=False); ps.to_csv(R4/'v4a_per_source.csv', index=False)
bs = L.paired_bootstrap(oofs, REF); bs['part'] = bs.name.map(part_of); bs.to_csv(R4/'v4a_bootstrap.csv', index=False)
ag = L.agreement_vs(oofs, REF); ag['part'] = ag.name.map(part_of); ag.to_csv(R4/'v4a_agreement.csv', index=False)

diff = bs[bs.comparison.str.contains(' - ')].pivot_table(index=['part', 'name'], columns='metric',
        values=['point', 'ci2_5', 'ci97_5'], aggfunc='first')
print('\nPoint metrics:\n' + pm.drop(columns=['misclassified_sources']).round(3).to_string(index=False))
print('\nPaired differences vs H-LR (v2 OOF):')
d = bs[bs.comparison.str.contains(' - ')].copy()
d['txt'] = d.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]{' *' if r.ci2_5 > 0 else ''}", axis=1)
print(d.pivot_table(index=['part', 'name'], columns='metric', values='txt', aggfunc='first').to_string())
prim = bs[(bs.name == 'auto|nested:auto') & bs.comparison.str.contains(' - ')]
print('\nPRIMARY (1e nested automatic selection - H-LR):\n' + prim[['metric', 'point', 'ci2_5', 'ci97_5', 'verdict']].round(3).to_string(index=False))
print('\nAgreement with H-LR:\n' + ag.round(3).to_string(index=False))

# ---------------- figures ----------------
S = bs[bs.metric == 'source_AUC']; pt = S[~S.comparison.str.contains(' - ')].set_index('name'); df_ = S[S.comparison.str.contains(' - ')].set_index('name')
B_ = bs[(bs.metric == 'source_balanced_accuracy') & bs.comparison.str.contains(' - ')].set_index('name')
order = [n for p in ['1e_primary', '1d_nested_per_algorithm', '1b_fixed', '1c_source_weighted'] for n in pt.index if part_of[n] == p]
order = [REF] + order
fig, axes = plt.subplots(1, 2, figsize=(12, 0.2 * len(order) + 1.6), sharey=True)
colp = {'reference_v2': INK, '1e_primary': '#c2410c', '1d_nested_per_algorithm': '#4a3aa7', '1b_fixed': '#2a78d6', '1c_source_weighted': '#1baf7a'}
for i, n in enumerate(order):
    c = colp[part_of[n]]
    axes[0].plot([pt.loc[n, 'ci2_5'], pt.loc[n, 'ci97_5']], [i, i], color=c, lw=1.2); axes[0].plot(pt.loc[n, 'point'], i, 'o', color=c, ms=3.5)
    if n != REF:
        axes[1].plot([B_.loc[n, 'ci2_5'], B_.loc[n, 'ci97_5']], [i, i], color=c, lw=1.2); axes[1].plot(B_.loc[n, 'point'], i, 'o', color=c, ms=3.5)
axes[0].axvline(pt.loc[REF, 'point'], color=INK2, ls='--', lw=.8); axes[1].axvline(0, color=INK2, ls='--', lw=.8)
axes[0].set_yticks(range(len(order))); axes[0].set_yticklabels(order, fontsize=6); axes[0].invert_yaxis()
axes[0].set_xlabel('source-level AUC (95% source bootstrap)'); axes[1].set_xlabel('source balanced accuracy minus H-LR (paired)')
axes[0].set_title('orange = PRIMARY nested auto-selection; purple = nested per algorithm; blue = fixed; green = source-weighted', loc='left', fontsize=7.5)
fig.suptitle('v4a: algorithms vs the v2 H-LR baseline (LOSO, 31 sources; 1b-1d rows are descriptive, many comparisons)', x=.01, ha='left')
fig.savefig(FG4/'v4a_forest_source_auc.png'); plt.close(fig)

H = reps['H_colours']; gx, gy = np.meshgrid(np.linspace(0.1, 1.1, 300), np.linspace(0.0, 0.55, 300)); G = np.c_[gx.ravel(), gy.ravel()]
fig, a = plt.subplots(figsize=(7.5, 6))
for lab, col in (('NS', CLASS_COLOR['NS']), ('BH', CLASS_COLOR['BH'])):
    m = y == (lab == 'BH'); a.scatter(H[m, 0], H[m, 1], s=6, color=col, alpha=.5, lw=0, label=f'{lab} observation')
for alg, ls, col in (('LogReg', '-', INK), ('RandomForest', '--', '#555555'), ('SVM_RBF', '-.', '#c2410c'), ('kNN', ':', '#4a3aa7'), ('HistGB', (0, (5, 1, 1, 1)), '#1baf7a')):
    sc = L.V4Model(alg).fit(H, y).score(G).reshape(gx.shape)
    cs = a.contour(gx, gy, sc, levels=[0.5], colors=[col], linestyles=[ls], linewidths=1.2)
    a.plot([], [], color=col, ls=ls, label=f'{alg} 0.5')
a.set_xlim(.1, 1.1); a.set_ylim(0, .55); a.legend(fontsize=7, loc='upper left')
a.set_xlabel('soft colour F(7–10)/F(5–7)'); a.set_ylabel('hard colour F(16–25)/F(10–16)')
a.set_title('v4a: 0.5 boundaries fitted on all 456 observations (visualisation only; accuracies are LOSO)', loc='left', fontsize=8)
fig.savefig(FG4/'v4a_colour_boundaries.png'); plt.close(fig)
v = prim.set_index('metric')
progress('v4a_algorithms', f"primary nested auto - H-LR: source BA {v.loc['source_balanced_accuracy','point']:+.3f} "
         f"[{v.loc['source_balanced_accuracy','ci2_5']:+.3f},{v.loc['source_balanced_accuracy','ci97_5']:+.3f}], "
         f"source AUC {v.loc['source_AUC','point']:+.3f} [{v.loc['source_AUC','ci2_5']:+.3f},{v.loc['source_AUC','ci97_5']:+.3f}]")
print(f'total {time.time()-T0:.0f} s')
