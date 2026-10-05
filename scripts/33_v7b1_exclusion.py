"""v7b1 step 3 (preregistration_v7.md §3, 1d-1e): re-run LOSO (H-LR, H-RF, B-LR, B-RF; v2 settings) on
  minbar   : v2 sample minus MINBAR-contaminated observations (PRIMARY exclusion; no replacement)
  literal  : minus the literal-rule set (any MINBAR burst anywhere in the sky; sensitivity)
  union    : minus MINBAR U v4-visual (sensitivity, decided after seeing the cross-check)
  replaced : contaminated observations replaced by the next clean candidate of the same time bin (sensitivity)
and compare, paired by source, with the v2 OOF (all 456 obs; PRIMARY = H-LR) and with v2 on the same kept
observations (descriptive). v1-v3 headline check: B - H (LR, RF) inside each set."""
import os, sys
os.environ['XRB_VERSION'] = 'v7b1'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import LeaveOneGroupOut
import v4lib as L

R7 = ROOT/'results/v7b1'
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
fl = pd.read_csv(R7/'minbar_flags.csv', dtype={'obs_id': str})
SETS = {'minbar': set(fl[fl.contaminated_minbar].obs_id), 'literal': set(fl[fl.contaminated_literal].obs_id),
        'union': set(fl[fl.contaminated_minbar | fl.std1_visual].obs_id)}
z2 = np.load(ROOT/'data/v2/processed/features.npz')
data = {}
for k, ex in SETS.items():
    m = ~np.isin(z2['obs_id'], list(ex))
    data[k] = {f: z2[f][m] for f in ('rate', 'F', 'y', 'source_id', 'obs_id')}; data[k]['edges'] = z2['edges']
zr = np.load(ROOT/'data/v7b1/processed/features_replaced.npz')
data['replaced'] = {f: zr[f] for f in ('rate', 'F', 'y', 'source_id', 'obs_id', 'edges')}
MODELS = [('H_colours', 'LogReg'), ('H_colours', 'RandomForest'), ('B_shape', 'LogReg'), ('B_shape', 'RandomForest')]
short = {'H_colours': 'H', 'B_shape': 'B', 'LogReg': 'LR', 'RandomForest': 'RF'}


def run(setname, rep, alg):
    d = data[setname]
    X = L.v2_representations(d['rate'], d['edges'], d['F'])[rep]
    folds = list(LeaveOneGroupOut().split(np.zeros(len(d['y'])), d['y'], d['source_id']))
    s = L.loso_scores(X, d['y'], d['source_id'], folds, alg)
    o = L.to_oof(np.arange(len(d['y'])), s, 0.5, d['y'], d['source_id'], d['obs_id'], rep, alg)
    return setname, rep, alg, o


out = Parallel(n_jobs=16)(delayed(run)(s, r, a) for s in data for r, a in MODELS)
oofs = {(s, r, a): o for s, r, a, o in out}
pd.concat([o.assign(set=s) for (s, r, a), o in oofs.items()]).to_csv(R7/'exclusion_oof.csv', index=False)
counts = pd.DataFrame([dict(set=s, n_obs=len(d['y']), n_BH_obs=int(d['y'].sum()), n_sources=len(set(d['source_id'])),
                            min_obs_per_source=int(pd.Series(d['source_id']).value_counts().min()),
                            fewest=pd.Series(d['source_id']).value_counts().idxmin()) for s, d in data.items()])
counts.to_csv(R7/'exclusion_counts.csv', index=False); print(counts.to_string(index=False))

bs = []
for s in data:
    for r, a in MODELS:
        nm = f'{short[r]}-{short[a]}'
        ref = v2[(v2.representation == r) & (v2.model == a)]
        b = L.paired_bootstrap({f'v2 {nm} (456 obs)': ref, f'{nm} [{s}]': oofs[(s, r, a)]}, f'v2 {nm} (456 obs)')
        b['set'] = s; b['model'] = nm; b['comparison_type'] = 'vs v2 (all obs, paired by source)'
        b['role'] = 'PRIMARY' if (s == 'minbar' and nm == 'H-LR') else 'descriptive'; bs.append(b)
        if s != 'replaced':
            kept = set(oofs[(s, r, a)].obs_id)
            b = L.paired_bootstrap({f'v2 {nm} (same kept obs)': ref[ref.obs_id.isin(kept)], f'{nm} [{s}]': oofs[(s, r, a)]}, f'v2 {nm} (same kept obs)')
            b['set'] = s; b['model'] = nm; b['comparison_type'] = 'vs v2 on the same kept obs'; b['role'] = 'descriptive'; bs.append(b)
    for a in ('LogReg', 'RandomForest'):
        b = L.paired_bootstrap({f'H-{short[a]} [{s}]': oofs[(s, 'H_colours', a)], f'B-{short[a]} [{s}]': oofs[(s, 'B_shape', a)]}, f'H-{short[a]} [{s}]')
        b['set'] = s; b['model'] = f'B-{short[a]} vs H-{short[a]}'; b['comparison_type'] = 'v1-v3 headline inside the set'; b['role'] = 'descriptive'; bs.append(b)
bs = pd.concat(bs, ignore_index=True); bs.to_csv(R7/'exclusion_bootstrap.csv', index=False)
d = bs[bs.comparison.str.contains(' - ')].copy()
d['txt'] = d.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]{' *' if (r.ci2_5 > 0 or r.ci97_5 < 0) else ''}", axis=1)
print('\n' + d.pivot_table(index=['comparison_type', 'set', 'model'], columns='metric', values='txt', aggfunc='first').to_string())
p = bs[~bs.comparison.str.contains(' - ')].pivot_table(index=['set', 'comparison'], columns='metric', values='point', aggfunc='first')
print('\n' + p.round(3).to_string())
prim = bs[(bs.role == 'PRIMARY') & bs.comparison.str.contains(' - ')].set_index('metric')
print('\nPRIMARY (H-LR, MINBAR exclusion - v2 H-LR):\n' + prim[['point', 'ci2_5', 'ci97_5']].round(3).to_string())
ps = pd.concat([L.src_table(o).assign(set=s, model=f'{short[r]}-{short[a]}') for (s, r, a), o in oofs.items()]).reset_index()
ps.to_csv(R7/'exclusion_per_source.csv', index=False)
progress('v7b1_exclusion', f"PRIMARY H-LR minbar-excluded - v2: source BA {prim.loc['source_balanced_accuracy','point']:+.3f} "
         f"[{prim.loc['source_balanced_accuracy','ci2_5']:+.3f},{prim.loc['source_balanced_accuracy','ci97_5']:+.3f}], source AUC "
         f"{prim.loc['source_AUC','point']:+.3f} [{prim.loc['source_AUC','ci2_5']:+.3f},{prim.loc['source_AUC','ci97_5']:+.3f}]")
