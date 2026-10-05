"""v7b2 step 2 (preregistration_v7.md §5, 3c-3d): add the persistent dynamical BHs to the v2 training sample.
main: 31 v2 sources + Cyg X-1, LMC X-1, LMC X-3 (34 sources, 10 BH); sensitivity: + LMC X-3 only (32 sources;
the two HMXBs above the Marcel+2026 Table 1 line removed). LOSO for H-LR, H-RF, B-LR, B-RF (v2 settings).
(i) on the original 31 sources: new OOF vs v2 OOF, paired by source (PRIMARY: H-LR source BA and AUC);
(ii) all sources of the run: source-level metrics with intervals. 3d shortcut checks: colour positions of the new
sources, their held-out scores, per-source score changes of the original 31, state of the new observations."""
import os, sys
os.environ['XRB_VERSION'] = 'v7b2'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import LeaveOneGroupOut
import config as C
import v4lib as L, v7lib as L7
from plotstyle import plt, CLASS_COLOR, INK, INK2

R7, FG = ROOT/'results/v7b2', ROOT/'figures/v7b2'
for p in (R7, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
z2, z7 = dict(np.load(ROOT/'data/v2/processed/features.npz')), dict(np.load(ROOT/'data/v7b2/processed/features.npz'))
assert np.allclose(z2['edges'], z7['edges'])
NEW = ['CYGX1', 'LMCX1', 'LMCX3']
cat = {k: np.concatenate([z2[k], z7[k]]) for k in ('rate', 'F', 'y', 'source_id', 'obs_id')}
RUNS = {'main (34 sources)': NEW, 'sensitivity: + LMC X-3 only (32 sources)': ['LMCX3']}
MODELS = [('H_colours', 'LogReg', 'H-LR'), ('H_colours', 'RandomForest', 'H-RF'), ('B_shape', 'LogReg', 'B-LR'), ('B_shape', 'RandomForest', 'B-RF')]
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})


def run(runname, rep, alg):
    keep = np.isin(cat['source_id'], list(np.unique(z2['source_id'])) + RUNS[runname])
    y, g, o = cat['y'][keep], cat['source_id'][keep], cat['obs_id'][keep]
    X = L.v2_representations(cat['rate'][keep], z2['edges'], cat['F'][keep])[rep]
    folds = list(LeaveOneGroupOut().split(np.zeros(len(y)), y, g))
    s = L.loso_scores(X, y, g, folds, alg)
    return runname, rep, alg, L.to_oof(np.arange(len(y)), s, 0.5, y, g, o, rep, alg)


out = Parallel(n_jobs=8)(delayed(run)(r, rep, a) for r in RUNS for rep, a, _ in MODELS)
oofs = {(r, rep, a): o for r, rep, a, o in out}
nm = {(rep, a): n for rep, a, n in MODELS}
pd.concat([o.assign(run=r) for (r, rep, a), o in oofs.items()]).to_csv(R7/'v7b2_oof_predictions.csv', index=False)
bs = []
v2src = set(z2['source_id'])
for (r, rep, a), o in oofs.items():
    n = nm[(rep, a)]
    ref = v2[(v2.representation == rep) & (v2.model == a)]
    b = L.paired_bootstrap({f'v2 {n} (31 sources)': ref, f'{n} [{r}] on the 31 v2 sources': o[o.source_id.isin(v2src)]}, f'v2 {n} (31 sources)')
    b['run'] = r; b['model'] = n; b['comparison_type'] = '(i) original 31 sources, paired'
    b['role'] = 'PRIMARY' if (r.startswith('main') and n == 'H-LR') else 'descriptive'; bs.append(b)
    b = L.paired_bootstrap({f'{n} [{r}] all sources': o}, f'{n} [{r}] all sources'); b['run'] = r; b['model'] = n
    b['comparison_type'] = '(ii) all sources of the run'; b['role'] = 'descriptive'; bs.append(b)
bs = pd.concat(bs, ignore_index=True); bs.to_csv(R7/'v7b2_bootstrap.csv', index=False)
t = bs.copy(); t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
print(t.pivot_table(index=['comparison_type', 'run', 'comparison'], columns='metric', values='txt', aggfunc='first').to_string())
prim = bs[(bs.role == 'PRIMARY') & bs.comparison.str.contains(' - ')].set_index('metric')
print('\nPRIMARY (main run, H-LR, original 31 sources - v2):\n' + prim[['point', 'ci2_5', 'ci97_5']].round(3).to_string())

# ---- 3d shortcut checks ----
ps = pd.concat([L.src_table(o).assign(run=r, model=nm[(rep, a)]) for (r, rep, a), o in oofs.items()]).reset_index()
v2ps = pd.concat([L.src_table(v2[(v2.representation == rep) & (v2.model == a)]).assign(model=n) for rep, a, n in MODELS]).reset_index()
ps = ps.merge(v2ps[['source_id', 'model', 'score']].rename(columns={'score': 'v2_score'}), on=['source_id', 'model'], how='left')
ps['score_change_vs_v2'] = ps.score - ps.v2_score; ps.to_csv(R7/'v7b2_per_source.csv', index=False)
print('\nnew sources (held out) mean BH score:\n' + ps[ps.source_id.isin(NEW)].pivot_table(index=['run', 'source_id'], columns='model', values='score').round(3).to_string())
print('\noriginal 31 sources whose source label changed vs v2 (main run):')
chg = ps[(ps.run.str.startswith('main')) & ps.source_id.isin(v2src) & ((ps.score >= .5) != (ps.v2_score >= .5))]
print(chg[['model', 'source_id', 'true_label', 'v2_score', 'score']].round(3).to_string(index=False) if len(chg) else '  none')
print('\nlargest score changes of the original 31 (main run):\n' +
      ps[(ps.run.str.startswith('main')) & ps.source_id.isin(v2src)].assign(a=lambda d: d.score_change_vs_v2.abs()).sort_values('a', ascending=False)
      .head(8)[['model', 'source_id', 'true_label', 'v2_score', 'score', 'score_change_vs_v2']].round(3).to_string(index=False))
# state of the new observations (v7a estimator; no bursts in these observations)
ob7 = pd.read_csv(ROOT/'data/v7b2/observations.csv', dtype={'obs_id': str}); ob7 = ob7[ob7.in_dataset.astype(str).str.lower().eq('true')]
stn = pd.DataFrame(Parallel(n_jobs=8)(delayed(L7.state_rms)(r.obs_id, r.path_src, r.path_bkg, []) for r in ob7.itertuples()))
stn = ob7[['obs_id', 'source_id']].merge(stn, on='obs_id'); stn.to_csv(R7/'v7b2_new_obs_states.csv', index=False)
print('\nstates of the new observations:\n' + stn.groupby('source_id').state.value_counts().unstack(fill_value=0).to_string())
# colour-colour figure
H2 = L.v2_representations(z2['rate'], z2['edges'], z2['F'])['H_colours']; H7 = L.v2_representations(z7['rate'], z7['edges'], z7['F'])['H_colours']
fig, a = plt.subplots(figsize=(7.5, 5.8))
for lab, col in (('NS', CLASS_COLOR['NS']), ('BH', CLASS_COLOR['BH'])):
    m = z2['y'] == (lab == 'BH'); a.scatter(H2[m, 0], H2[m, 1], s=6, color=col, alpha=.35, lw=0, label=f'v2 {lab}')
for s, mk in zip(NEW, ['*', 'D', 's']):
    m = z7['source_id'] == s; a.scatter(H7[m, 0], H7[m, 1], s=40, marker=mk, facecolor='none', edgecolor=INK, lw=.9, label=s)
a.set_xlabel('soft colour F(7–10)/F(5–7)'); a.set_ylabel('hard colour F(16–25)/F(10–16)'); a.legend(fontsize=7, loc='upper left')
a.set_title('v7b2: persistent BHs (open markers) on the v2 colour plane', loc='left', fontsize=9)
fig.savefig(FG/'v7b2_colour_positions.png'); plt.close(fig)
progress('v7b2_analysis', f"PRIMARY H-LR main run on the 31 v2 sources - v2: source BA {prim.loc['source_balanced_accuracy','point']:+.3f} "
         f"[{prim.loc['source_balanced_accuracy','ci2_5']:+.3f},{prim.loc['source_balanced_accuracy','ci97_5']:+.3f}], source AUC "
         f"{prim.loc['source_AUC','point']:+.3f} [{prim.loc['source_AUC','ci2_5']:+.3f},{prim.loc['source_AUC','ci97_5']:+.3f}]")
