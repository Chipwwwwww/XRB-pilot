"""v4b2 step 3 (preregistration_v4.md §4, 3b): response-normalised representations across gain epochs.
R  = net rate per bin / (Gamma=2, N_H=0 power law folded through that observation's response)  [pl2 in features.npz]
H_R = colours of net counts divided by the same colours of the folded power law (same bands as H).
Bridge check on the v2 456 (must pass): H_R-LR vs H-LR paired differences (source BA, source AUC) include 0 AND
observation-score Spearman >= 0.90. Then LOSO on v2 456 + new v4b2 sources: H_R, R x LR, RF (fixed v2 hyperparameters).
Gain epoch is a diagnostic only (never a feature)."""
import os, sys
os.environ['XRB_VERSION'] = 'v4b2'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress, D
import config as C
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.model_selection import LeaveOneGroupOut
import v4lib as L
from plotstyle import plt, CLASS_COLOR, INK2

R_, FG = ROOT/'results/v4b2', ROOT/'figures/v4b2'
for p in (R_, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250)


def reps_R(z):
    W = np.diff(z['edges']); ec = np.sqrt(z['edges'][:-1] * z['edges'][1:])
    Rr = z['rate'] / z['pl2']
    band = lambda a, lo, hi: np.sum((a * W)[:, (ec >= lo) & (ec < hi)], 1)
    c = {k: band(z['rate'], *b) / band(z['pl2'], *b) for k, b in {'b1': (5, 7), 'b2': (7, 10), 'b3': (10, 16), 'b4': (16, 25.1)}.items()}
    return {'H_R': np.c_[c['b2'] / c['b1'], c['b4'] / c['b3']], 'R': Rr}


def epoch_of(mjd):
    return np.searchsorted([C.V4_EPOCH_STOP_MJD[k] for k in (1, 2, 3, 4)], mjd, side='right') + 1


z2 = np.load(ROOT/'data/v2/processed/features.npz')
y2, g2, o2 = z2['y'], z2['source_id'], z2['obs_id']
r2 = reps_R(z2)
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
ref = v2[(v2.representation == 'H_colours') & (v2.model == 'LogReg')]
folds2 = list(LeaveOneGroupOut().split(np.zeros(len(y2)), y2, g2))

# ---- bridge check ----
s = L.loso_scores(r2['H_R'], y2, g2, folds2, 'LogReg')
hr = L.to_oof(np.arange(len(y2)), s, 0.5, y2, g2, o2, 'H_R', 'LogReg')
b = L.paired_bootstrap({'H-LR (v2)': ref, 'H_R-LR': hr}, 'H-LR (v2)')
rho = spearmanr(ref.set_index('obs_id').loc[o2].BH_score, s)[0]
dd = b[b.comparison.str.contains(' - ')].set_index('metric')
passed = bool(dd.loc['source_balanced_accuracy', 'ci2_5'] <= 0 <= dd.loc['source_balanced_accuracy', 'ci97_5'] and
              dd.loc['source_AUC', 'ci2_5'] <= 0 <= dd.loc['source_AUC', 'ci97_5'] and rho >= C.V4_BRIDGE_MIN_SPEARMAN)
b['spearman_obs_scores'] = rho; b['bridge_passed'] = passed; b.to_csv(R_/'v4b2_bridge_check.csv', index=False)
hr.to_csv(R_/'v4b2_bridge_oof_HR_LR.csv', index=False)
print('BRIDGE CHECK (v2 456): Spearman', round(rho, 4)); print(b.round(3).to_string(index=False)); print('PASSED' if passed else 'FAILED')
if not passed:
    progress('v4b2_bridge', 'bridge check FAILED -> v4b2 stopped (preregistration)'); sys.exit(3)

# ---- extended sample ----
z3 = np.load(D/'processed/features.npz')
assert np.allclose(z3['edges'], z2['edges']), 'grid differs'
ob3 = pd.read_csv(D/'observations.csv', dtype={'obs_id': str}); ob3 = ob3[ob3.in_dataset.astype(str).str.lower().eq('true')]
assert list(ob3.obs_id) == list(z3['obs_id'])
obs2 = pd.read_csv(ROOT/'data/v2/observations.csv', dtype={'obs_id': str}); obs2 = obs2[obs2.in_dataset.astype(str).str.lower().eq('true')]
r3 = reps_R(z3)
y = np.r_[y2, z3['y']]; g = np.r_[g2, z3['source_id']]; oid = np.r_[o2, z3['obs_id']]
mjd = np.r_[obs2.mjd.values, ob3.mjd.values]; ep = epoch_of(mjd)
X = {k: np.r_[r2[k], r3[k]] for k in r2}
H = np.r_[L.v2_representations(z2['rate'], z2['edges'], z2['F'])['H_colours'], L.v2_representations(z3['rate'], z3['edges'], z3['F'])['H_colours']]
X['H_count_space'] = H
cnt = pd.DataFrame(dict(source_id=g, label=np.where(y == 1, 'BH', 'NS'), epoch=ep)).groupby(['label', 'source_id', 'epoch']).size().unstack(fill_value=0)
cnt.to_csv(R_/'v4b2_sample_by_epoch.csv'); print('\nextended sample:', len(y), 'obs,', len(set(g)), 'sources,', len(set(g[y == 1])), 'BH')
print(cnt.to_string())
folds = list(LeaveOneGroupOut().split(np.zeros(len(y)), y, g))
oofs = {}
for rep in ['H_R', 'R', 'H_count_space']:
    for alg in ['LogReg', 'RandomForest']:
        sc = L.loso_scores(X[rep], y, g, folds, alg)
        d = L.to_oof(np.arange(len(y)), sc, 0.5, y, g, oid, rep, alg); d['epoch'] = ep; oofs[f'{rep}|{alg}'] = d
allo = pd.concat(oofs.values(), ignore_index=True); allo.to_csv(R_/'v4b2_oof_predictions.csv', index=False)
fold_of = np.empty(len(y), int)
for k, (tr, te) in enumerate(folds): fold_of[te] = k
pd.DataFrame(dict(obs_id=oid, source_id=g, fold=fold_of)).to_csv(R_/'folds_loso.csv', index=False)
bs = L.paired_bootstrap(oofs, 'H_R|LogReg'); bs['sample'] = f'extended ({len(set(g))} sources)'
# on the 31 v2 sources / 456 observations: extended-trained OOF vs v2 H-LR
sub = {k: d[d.obs_id.isin(o2)] for k, d in oofs.items()}; sub['H-LR (v2)'] = ref
b2 = L.paired_bootstrap(sub, 'H-LR (v2)'); b2['sample'] = 'v2 456 observations (models trained on extended sample)'
bs = pd.concat([bs, b2], ignore_index=True); bs.to_csv(R_/'v4b2_bootstrap.csv', index=False)
t = bs.copy(); t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
print('\n' + t.pivot_table(index=['sample', 'comparison'], columns='metric', values='txt', aggfunc='first').to_string())
# epoch diagnostics
diag = allo.groupby(['representation', 'model', 'true_label', 'epoch']).BH_score.agg(['size', 'mean', 'median']).reset_index()
diag.to_csv(R_/'v4b2_epoch_diagnostics.csv', index=False)
rows = []
for (rep, m), d in allo.groupby(['representation', 'model']):
    for lab in ('BH', 'NS'):
        e = d[d.true_label == lab]
        if e.epoch.nunique() > 1: rows.append(dict(representation=rep, model=m, label=lab, spearman_score_vs_epoch=spearmanr(e.epoch, e.BH_score)[0], n=len(e)))
pd.DataFrame(rows).to_csv(R_/'v4b2_epoch_score_correlation.csv', index=False)
print('\nscore vs epoch (within class):\n' + pd.DataFrame(rows).round(3).to_string(index=False))
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for a, rep in zip(axes, ['H_R', 'R']):
    d = allo[(allo.representation == rep) & (allo.model == 'LogReg')]
    for lab, off in (('NS', -.12), ('BH', .12)):
        for e in sorted(d.epoch.unique()):
            v = d[(d.true_label == lab) & (d.epoch == e)].BH_score
            if len(v): a.scatter(np.full(len(v), e + off), v, s=6, alpha=.5, color=CLASS_COLOR[lab]); a.plot([e + off - .08, e + off + .08], [v.mean()] * 2, color='k')
    a.axhline(.5, color=INK2, ls='--', lw=.7); a.set_xlabel('PCA gain epoch (diagnostic only)'); a.set_title(f'{rep}-LR', loc='left')
axes[0].set_ylabel('LOSO BH score')
fig.suptitle('v4b2: scores by gain epoch (blue = BH, orange = NS; black = mean)', x=.01, ha='left')
fig.savefig(FG/'v4b2_scores_by_epoch.png'); plt.close(fig)
progress('v4b2_analysis', f'bridge passed (rho={rho:.3f}); extended {len(set(g))} sources')
