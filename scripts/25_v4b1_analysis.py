"""v4b1 step 3 (preregistration_v4.md §4, 3c): all eligible epoch-5 pointings of the 31 v2 sources.
H, B, A, HI x LR, RF with source-equal sample weights (primary) and class_weight=balanced (descriptive);
LOSO over the same 31 sources; paired source bootstrap vs the v2 H-LR OOF. Effective sample size = 31 sources."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v4b1'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress, D
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import LeaveOneGroupOut
import v4lib as L
from plotstyle import plt, CLASS_COLOR, INK2

R_ = ROOT/'results/v4b1'; R_.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250)
z = np.load(D/'processed/features.npz')
y, g, oid = z['y'], z['source_id'], z['obs_id']
reps = L.v2_representations(z['rate'], z['edges'], z['F'])
print(len(y), 'observations;', pd.Series(np.where(y == 1, 'BH', 'NS')).value_counts().to_dict(), ';', len(set(g)), 'sources', flush=True)
print(pd.Series(g).value_counts().to_string(), flush=True)
folds = list(LeaveOneGroupOut().split(np.zeros(len(y)), y, g))
fold_of = np.empty(len(y), int)
for k, (tr, te) in enumerate(folds): fold_of[te] = k
pd.DataFrame(dict(obs_id=oid, source_id=g, fold=fold_of)).to_csv(R_/'folds_loso.csv', index=False)
tasks = [(rep, alg, w) for rep in L.REPS for alg in ('LogReg', 'RandomForest') for w in ('source_equal', None)]
def run(rep, alg, w): return rep, alg, w, L.loso_scores(reps[rep], y, g, folds, alg, None, w)
out = Parallel(n_jobs=16, verbose=5)(delayed(run)(*t) for t in tasks)
oofs = {}
for rep, alg, w, s in out:
    name = f"{rep}|{alg}[{'srcw' if w else 'balanced'}]"
    d = L.to_oof(np.arange(len(y)), s, 0.5, y, g, oid, rep, f"{alg}[{'srcw' if w else 'balanced'}]", None); d['fold'] = fold_of
    oofs[name] = d
allo = pd.concat(oofs.values(), ignore_index=True); allo.to_csv(R_/'v4b1_oof_predictions.csv', index=False)
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
oofs['H-LR (v2, 456 obs)'] = v2[(v2.representation == 'H_colours') & (v2.model == 'LogReg')]
bs = L.paired_bootstrap(oofs, 'H-LR (v2, 456 obs)'); bs.to_csv(R_/'v4b1_bootstrap.csv', index=False)
t = bs.copy(); t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
print('\n' + t.pivot_table(index=['comparison'], columns='metric', values='txt', aggfunc='first').to_string())
ag = L.agreement_vs({k: v for k, v in oofs.items()}, 'H-LR (v2, 456 obs)'); ag.to_csv(R_/'v4b1_agreement_on_v2_obs.csv', index=False)
# descriptive (decided before seeing v4b1 results): v4b1-trained OOF scores restricted to the v2 observations, same obs as the reference
sub = {k: (v[v.obs_id.isin(set(oofs['H-LR (v2, 456 obs)'].obs_id))] if k != 'H-LR (v2, 456 obs)' else v) for k, v in oofs.items()}
print('\nv2 observations present in v4b1:', len(sub['H_colours|LogReg[srcw]']), 'of', len(oofs['H-LR (v2, 456 obs)']))
bs2 = L.paired_bootstrap(sub, 'H-LR (v2, 456 obs)'); bs2.to_csv(R_/'v4b1_bootstrap_on_v2_obs.csv', index=False)
t = bs2[bs2.comparison.str.contains(' - ')].copy(); t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
print('\n[v2 observations only]\n' + t.pivot_table(index=['comparison'], columns='metric', values='txt', aggfunc='first').to_string())
ps = pd.concat([L.src_table(v).assign(name=k) for k, v in oofs.items()]).reset_index()
ps.to_csv(R_/'v4b1_per_source.csv', index=False)
print('\n' + ps.pivot_table(index=['source_id', 'true_label'], columns='name', values='score').round(2).to_string())
FG = ROOT/'figures/v4b1'; FG.mkdir(parents=True, exist_ok=True)
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
ref = L.src_table(oofs['H-LR (v2, 456 obs)'])
for a, m in zip(axes, ['H_colours|LogReg[srcw]', 'H_colours|RandomForest[srcw]']):
    t = L.src_table(oofs[m]).join(ref.score.rename('ref'))
    for lab in ('NS', 'BH'):
        e = t[t.true_label == lab]; a.scatter(e.ref, e.score, s=12 + 3 * np.sqrt(e.n), color=CLASS_COLOR[lab], alpha=.7, label=lab)
    a.plot([0, 1], [0, 1], color=INK2, lw=.7); a.axhline(.5, color=INK2, ls='--', lw=.7); a.axvline(.5, color=INK2, ls='--', lw=.7)
    a.set_xlabel('v2 H-LR source mean score (15 obs/source)'); a.set_title(m.replace('H_colours|', 'H-'), loc='left')
axes[0].set_ylabel('v4b1 source mean score (all obs; size ~ sqrt n)'); axes[0].legend(frameon=False)
fig.suptitle('v4b1: per-source LOSO score, all eligible pointings vs v2', x=.01, ha='left')
fig.savefig(FG/'v4b1_source_scores.png'); plt.close(fig)
p = bs[(bs.comparison == 'H_colours|LogReg[srcw] - H-LR (v2, 456 obs)')].set_index('metric')
progress('v4b1_analysis', f"{len(y)} obs; H-LR[srcw] - v2 H-LR: source BA {p.loc['source_balanced_accuracy','point']:+.3f} "
         f"[{p.loc['source_balanced_accuracy','ci2_5']:+.3f},{p.loc['source_balanced_accuracy','ci97_5']:+.3f}]")
