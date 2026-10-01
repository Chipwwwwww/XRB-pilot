"""v4 burst leakage check, part 2 (preregistration_v4.md §3, 2c). Exclude observations containing a type-I burst
(primary: automatic rule; sensitivity: visual set incl. 'possible'), re-run LOSO for H/B x LR/RF (+ H+B for the
v3a comparison) and compare paired with the v2 OOF restricted to the same kept observations."""
import os, sys
os.environ['XRB_VERSION'] = 'v4'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from sklearn.model_selection import LeaveOneGroupOut
import v4lib as L

R4 = ROOT/'results/v4'
pd.set_option('display.width', 250)
z = np.load(ROOT/'data/v2/processed/features.npz')
y, g, oid = z['y'], z['source_id'], z['obs_id']
reps = L.v2_representations(z['rate'], z['edges'], z['F'])
reps['H_plus_B'] = np.c_[reps['H_colours'], reps['B_shape']]
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
v3a = pd.read_csv(ROOT/'results/v3/v3a_oof_predictions.csv', dtype={'obs_id': str})
orig = pd.concat([v2[v2.representation.isin(['H_colours', 'B_shape'])], v3a[v3a.representation == 'H_plus_B']])
flags = pd.read_csv(R4/'burst_flags.csv', dtype={'obs_id': str}); vis = pd.read_csv(R4/'burst_visual.csv', dtype={'obs_id': str})
SETS = {'auto': set(flags[flags.contains_burst_auto == True].obs_id), 'visual': set(vis[vis.visual != 'not_burst'].obs_id)}

rows_n, boots, oofs_all = [], [], []
for sname, excl in SETS.items():
    keep = ~np.isin(oid, list(excl))
    cnt = pd.Series(g[keep]).value_counts()
    for s in sorted(set(g)):
        rows_n.append(dict(exclusion_set=sname, source_id=s, label='BH' if y[g == s][0] else 'NS', n_kept=int(cnt.get(s, 0)),
                           n_removed=int((g == s).sum() - cnt.get(s, 0)), below_5=int(cnt.get(s, 0)) < 5))
    yk, gk, ok = y[keep], g[keep], oid[keep]
    folds = list(LeaveOneGroupOut().split(np.zeros(len(yk)), yk, gk))
    new = {}
    for rep in ['H_colours', 'B_shape', 'H_plus_B']:
        for alg in ['LogReg', 'RandomForest']:
            s = L.loso_scores(reps[rep][keep], yk, gk, folds, alg)
            d = L.to_oof(np.arange(len(yk)), s, 0.5, yk, gk, ok, rep, alg); d['exclusion_set'] = sname
            new[(rep, alg)] = d; oofs_all.append(d)
            o = orig[(orig.representation == rep) & (orig.model == alg) & orig.obs_id.isin(ok)]
            b = L.paired_bootstrap({'original(v2/v3a, same obs)': o, 'burst-excluded': d}, 'original(v2/v3a, same obs)')
            b['exclusion_set'] = sname; b['representation'] = rep; b['model'] = alg; boots.append(b)
    # v1-v3 headline comparisons on the burst-excluded sample
    for alg in ['LogReg', 'RandomForest']:
        for r1 in ['B_shape', 'H_plus_B']:
            b = L.paired_bootstrap({'H_colours': new[('H_colours', alg)], r1: new[(r1, alg)]}, 'H_colours')
            b['exclusion_set'] = sname; b['representation'] = f'{r1} vs H_colours (both burst-excluded)'; b['model'] = alg; boots.append(b)
            o1 = orig[(orig.representation == r1) & (orig.model == alg)]; oh = orig[(orig.representation == 'H_colours') & (orig.model == alg)]
            b = L.paired_bootstrap({'H_colours': oh, r1: o1}, 'H_colours')
            b['exclusion_set'] = 'none (original 456)'; b['representation'] = f'{r1} vs H_colours (original)'; b['model'] = alg
            if sname == 'auto': boots.append(b)
    print(sname, f'excluded {len(excl)} obs; kept {keep.sum()}', flush=True)

pd.DataFrame(rows_n).to_csv(R4/'burst_exclusion_counts.csv', index=False)
pd.concat(oofs_all).to_csv(R4/'burst_exclusion_oof.csv', index=False)
bs = pd.concat(boots, ignore_index=True); bs.to_csv(R4/'burst_exclusion_bootstrap.csv', index=False)
cnt = pd.DataFrame(rows_n)
print('\nsources with <5 kept observations:\n' + cnt[cnt.below_5].to_string(index=False))
d = bs[bs.comparison.str.contains(' - ')].copy()
d['txt'] = d.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
print('\npaired differences:\n' + d.pivot_table(index=['exclusion_set', 'representation', 'model', 'comparison'], columns='metric',
                                                 values='txt', aggfunc='first').to_string())
pt = bs[~bs.comparison.str.contains(' - ') & (bs.name == 'burst-excluded')].copy()
pt['txt'] = pt.apply(lambda r: f"{r.point:.3f} [{r.ci2_5:.3f},{r.ci97_5:.3f}]", axis=1)
print('\nburst-excluded point metrics:\n' + pt.pivot_table(index=['exclusion_set', 'representation', 'model'], columns='metric',
                                                          values='txt', aggfunc='first').to_string())
progress('v4_burst_exclusion', f"auto set {len(SETS['auto'])} obs, visual set {len(SETS['visual'])} obs excluded; results/v4/burst_exclusion_*")
