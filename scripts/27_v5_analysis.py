"""v5 step 2 (preregistration_v5.md §5): do Standard-1 timing features T add BH/NS information beyond the two colours H?
PRIMARY (S1, v2 456 obs): H+T-LR vs the v2 H-LR OOF. Descriptive: T-only models, H+T-RF vs v2 H-RF, colour-overlap box,
burst-excluded re-fit, S2 (v2+v4b2, 46 sources) vs same-sample H-LR, S3 (v4b1, 7949 obs, source-equal weights) vs v2 H-LR
and vs the v4b1 H-LR[srcw]. Fixed v2 hyperparameters, threshold 0.5, missing T -> train-fold median + indicator."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v5'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import LeaveOneGroupOut
import config as C
import v4lib as L
import v5lib as L5
from plotstyle import plt, CLASS_COLOR, INK2

R5, FG = ROOT/'results/v5', ROOT/'figures/v5'
for p in (R5, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
T0 = time.time()
TF = pd.read_csv(ROOT/'data/v5/processed/timing_features.csv', dtype={'obs_id': str}).set_index('obs_id')
TCOLS = ['T1', 'T2', 'T3']
v2oof = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
REF_LR = v2oof[(v2oof.representation == 'H_colours') & (v2oof.model == 'LogReg')]
REF_RF = v2oof[(v2oof.representation == 'H_colours') & (v2oof.model == 'RandomForest')]


def tmat(oid):
    return TF.reindex(oid)[TCOLS].values.astype(float)       # NaN where missing (status != ok -> T columns empty)


def fold_scores(k, tr, te, H, T, y, g, alg, weighting):
    if H is None: a, b = L5.fill_missing(T[tr], T[te])
    else:
        a, b = L5.fill_missing(T[tr], T[te]); a, b = np.c_[H[tr], a], np.c_[H[te], b]
    w = L.source_equal_weights(y[tr], g[tr]) if weighting == 'source_equal' else None
    return k, L.V4Model(alg).fit(a, y[tr], w).score(b)


def loso(H, T, y, g, folds, alg, weighting=None, jobs=16):
    s = np.full(len(y), np.nan)
    for k, sc in Parallel(n_jobs=jobs)(delayed(fold_scores)(k, tr, te, H, T, y, g, alg, weighting) for k, (tr, te) in enumerate(folds)):
        s[folds[k][1]] = sc
    return s


def txt(bs):
    t = bs[bs.comparison.str.contains(' - ')].copy()
    t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]{' *' if r.ci2_5 > 0 else ''}", axis=1)
    return t.pivot_table(index='comparison', columns='metric', values='txt', aggfunc='first').to_string()


def points(bs):
    t = bs[~bs.comparison.str.contains(' - ')]
    return t.pivot_table(index='comparison', columns='metric', values='point', aggfunc='first').round(3).to_string()


allbs, allo = [], []

# ======================= S1: v2 456 observations =======================
z = np.load(ROOT/'data/v2/processed/features.npz')
y, g, oid = z['y'], z['source_id'], z['obs_id']
H = L.v2_representations(z['rate'], z['edges'], z['F'])['H_colours']
T = tmat(oid)
folds = list(LeaveOneGroupOut().split(np.zeros(len(y)), y, g))
ff = pd.read_csv(ROOT/'results/v2/folds_loso.csv', dtype={'obs_id': str})
assert all((ff[ff.fold == k].obs_id.values == oid[te]).all() for k, (tr, te) in enumerate(folds)), 'folds differ from v2'
fold_of = np.empty(len(y), int)
for k, (tr, te) in enumerate(folds): fold_of[te] = k
pd.DataFrame(dict(obs_id=oid, source_id=g, fold=fold_of)).to_csv(R5/'folds_loso_S1.csv', index=False)
miss = ~np.isfinite(T).all(1)
print(f'S1: {len(y)} obs; timing missing {miss.sum()} ({int(miss[y == 1].sum())} BH, {int(miss[y == 0].sum())} NS)', flush=True)
print(pd.Series(g[miss]).value_counts().to_string())
o1 = {}
for name, HH, TT, alg in (('H+T|LogReg', H, T, 'LogReg'), ('H+T|RandomForest', H, T, 'RandomForest'),
                          ('T|LogReg', None, T, 'LogReg'), ('T|RandomForest', None, T, 'RandomForest')):
    s = loso(HH, TT, y, g, folds, alg)
    d = L.to_oof(np.arange(len(y)), s, 0.5, y, g, oid, name.split('|')[0], alg); d['fold'] = fold_of; o1[name] = d
o1['H-LR (v2)'] = REF_LR; o1['H-RF (v2)'] = REF_RF
allo.append(pd.concat([o1[k].assign(sample='S1', name=k) for k in o1 if '(v2)' not in k]))
b = L.paired_bootstrap({k: o1[k] for k in ('H-LR (v2)', 'H+T|LogReg', 'H+T|RandomForest', 'T|LogReg', 'T|RandomForest')}, 'H-LR (v2)')
b['sample'] = 'S1 v2 456 obs'; b['role'] = np.where(b['name'] == 'H+T|LogReg', 'PRIMARY', 'descriptive'); allbs.append(b)
b = L.paired_bootstrap({'H-RF (v2)': o1['H-RF (v2)'], 'H+T|RandomForest': o1['H+T|RandomForest']}, 'H-RF (v2)')
b['sample'] = 'S1 v2 456 obs'; b['role'] = 'descriptive'; allbs.append(b)
print('\n[S1] point metrics\n' + points(pd.concat(allbs)) + '\n[S1] paired differences\n' + txt(pd.concat(allbs)), flush=True)

# overlap box (v4 definition; sources with >= 3 box observations)
box = (H[:, 0] >= C.V4_OVERLAP_BOX['c1_min']) & (H[:, 1] >= C.V4_OVERLAP_BOX['c2_min'])
nbox = pd.Series(g[box]).value_counts(); srcs = set(nbox[nbox >= 3].index); inbox = set(oid[box])
print(f'\noverlap box: {box.sum()} obs, {len(srcs)} sources with >=3 box obs ({sum(y[g == s][0] for s in srcs)} BH)')
for alg, ref in (('LogReg', 'H-LR (v2)'), ('RandomForest', 'H-RF (v2)')):
    sub = {k: o1[k][o1[k].obs_id.isin(inbox) & o1[k].source_id.isin(srcs)] for k in (ref, f'H+T|{alg}')}
    b = L.paired_bootstrap(sub, ref); b['sample'] = 'S1 overlap box'; b['role'] = 'descriptive'; allbs.append(b)

# burst-excluded re-fit (v4 automatic flags), same kept observations for H and H+T
bf = pd.read_csv(ROOT/'results/v4/burst_flags.csv', dtype={'obs_id': str})
keep = ~pd.Series(oid).isin(set(bf[bf.contains_burst_auto == True].obs_id)).values
yk, gk, ok_ = y[keep], g[keep], oid[keep]
fk = list(LeaveOneGroupOut().split(np.zeros(keep.sum()), yk, gk))
ob = {}
for name, HH, alg in (('H|LogReg', H[keep], 'LogReg'), ('H+T|LogReg', H[keep], 'LogReg'), ('H|RandomForest', H[keep], 'RandomForest'), ('H+T|RandomForest', H[keep], 'RandomForest')):
    s = L.loso_scores(HH, yk, gk, fk, alg) if name.startswith('H|') else loso(HH, T[keep], yk, gk, fk, alg)
    ob[name] = L.to_oof(np.arange(keep.sum()), s, 0.5, yk, gk, ok_, name.split('|')[0], alg)
for alg in ('LogReg', 'RandomForest'):
    b = L.paired_bootstrap({f'H|{alg}': ob[f'H|{alg}'], f'H+T|{alg}': ob[f'H+T|{alg}']}, f'H|{alg}')
    b['sample'] = f'S1 burst-excluded ({keep.sum()} obs)'; b['role'] = 'descriptive'; allbs.append(b)
allo.append(pd.concat([v.assign(sample='S1 burst-excluded', name=k) for k, v in ob.items()]))
print(f'[S1] done ({time.time()-T0:.0f} s)', flush=True)

# ======================= S2: v2 + v4b2 (46 sources) =======================
z3 = np.load(ROOT/'data/v4b2/processed/features.npz')
y2 = np.r_[y, z3['y']]; g2 = np.r_[g, z3['source_id']]; o2 = np.r_[oid, z3['obs_id']]
H2 = np.r_[H, L.v2_representations(z3['rate'], z3['edges'], z3['F'])['H_colours']]; T2 = tmat(o2)
f2 = list(LeaveOneGroupOut().split(np.zeros(len(y2)), y2, g2))
v4b2 = pd.read_csv(ROOT/'results/v4b2/v4b2_oof_predictions.csv', dtype={'obs_id': str})
ref2 = v4b2[(v4b2.representation == 'H_count_space') & (v4b2.model == 'LogReg')]
chk = L.loso_scores(H2, y2, g2, f2, 'LogReg')
assert np.allclose(ref2.set_index('obs_id').loc[o2].raw_score.values, chk, atol=1e-10), 'S2 H-LR does not reproduce v4b2'
os2 = {'H-LR (S2 same sample)': ref2}
for alg in ('LogReg', 'RandomForest'):
    s = loso(H2, T2, y2, g2, f2, alg); os2[f'H+T|{alg}'] = L.to_oof(np.arange(len(y2)), s, 0.5, y2, g2, o2, 'H+T', alg)
b = L.paired_bootstrap(os2, 'H-LR (S2 same sample)'); b['sample'] = f'S2 v2+v4b2 ({len(set(g2))} sources, {len(y2)} obs)'; b['role'] = 'descriptive'
allbs.append(b); allo.append(pd.concat([v.assign(sample='S2', name=k) for k, v in os2.items() if k.startswith('H+T')]))
print(f'[S2] {len(y2)} obs, timing missing {int((~np.isfinite(T2).all(1)).sum())}; done ({time.time()-T0:.0f} s)', flush=True)

# ======================= S3: v4b1 (7949 obs, 31 sources, source-equal weights) =======================
z4 = np.load(ROOT/'data/v4b1/processed/features.npz')
y3, g3, o3 = z4['y'], z4['source_id'], z4['obs_id']
H3 = L.v2_representations(z4['rate'], z4['edges'], z4['F'])['H_colours']; T3 = tmat(o3)
f3 = list(LeaveOneGroupOut().split(np.zeros(len(y3)), y3, g3))
v4b1 = pd.read_csv(ROOT/'results/v4b1/v4b1_oof_predictions.csv', dtype={'obs_id': str})
ref3 = v4b1[(v4b1.representation == 'H_colours') & (v4b1.model == 'LogReg[srcw]')]
os3 = {'H-LR[srcw] (S3 same sample)': ref3, 'H-LR (v2)': REF_LR}
for alg in ('LogReg', 'RandomForest'):
    s = loso(H3, T3, y3, g3, f3, alg, 'source_equal'); os3[f'H+T|{alg}[srcw]'] = L.to_oof(np.arange(len(y3)), s, 0.5, y3, g3, o3, 'H+T', f'{alg}[srcw]')
for ref in ('H-LR (v2)', 'H-LR[srcw] (S3 same sample)'):
    other = [k for k in os3 if k not in ('H-LR (v2)', 'H-LR[srcw] (S3 same sample)')]
    b = L.paired_bootstrap({ref: os3[ref], **{k: os3[k] for k in other}}, ref)
    b['sample'] = f'S3 v4b1 ({len(y3)} obs)'; b['role'] = 'descriptive'; allbs.append(b)
allo.append(pd.concat([v.assign(sample='S3', name=k) for k, v in os3.items() if k.startswith('H+T')]))
print(f'[S3] {len(y3)} obs, timing missing {int((~np.isfinite(T3).all(1)).sum())}; done ({time.time()-T0:.0f} s)', flush=True)

# ======================= outputs =======================
bs = pd.concat(allbs, ignore_index=True); bs.to_csv(R5/'v5_bootstrap.csv', index=False)
pd.concat(allo, ignore_index=True).to_csv(R5/'v5_oof_predictions.csv', index=False)
ps = pd.concat([L.src_table(v).assign(name=k) for k, v in o1.items()]).reset_index(); ps.to_csv(R5/'v5_per_source_S1.csv', index=False)
for smp, d in bs.groupby('sample', sort=False):
    print(f'\n=== {smp} ===\n' + points(d) + '\n' + txt(d))
print('\n[S1] per-source mean scores\n' + ps.pivot_table(index=['source_id', 'true_label'], columns='name', values='score').round(2).to_string())
prim = bs[(bs.role == 'PRIMARY') & bs.comparison.str.contains(' - ')].set_index('metric')
print('\nPRIMARY H+T-LR - H-LR (v2):\n' + prim[['point', 'ci2_5', 'ci97_5', 'verdict']].round(3).to_string())

# figure: timing features vs hard colour (S1) and class distributions
S1 = TF.reindex(oid).assign(c2=H[:, 1], label=np.where(y == 1, 'BH', 'NS'))
fig, axes = plt.subplots(1, 4, figsize=(15, 3.8))
for a, col in zip(axes, TCOLS + ['T_total']):
    for lab in ('NS', 'BH'):
        d = S1[S1.label == lab]; a.scatter(d.c2, d[col], s=7, alpha=.55, color=CLASS_COLOR[lab], lw=0, label=lab)
    a.axhline(0, color=INK2, lw=.6); a.set_xlabel('hard colour F(16–25)/F(10–16)'); a.set_title(col, loc='left')
axes[0].set_ylabel('fractional rms (signed sqrt of cospectral variance)'); axes[0].legend(frameon=False, fontsize=7)
fig.suptitle('v5: Standard-1 timing features vs hard colour (S1, 456 v2 observations; missing not shown)', x=.01, ha='left')
fig.savefig(FG/'v5_timing_vs_colour.png'); plt.close(fig)
progress('v5_analysis', f"PRIMARY H+T-LR - H-LR: source BA {prim.loc['source_balanced_accuracy','point']:+.3f} "
         f"[{prim.loc['source_balanced_accuracy','ci2_5']:+.3f},{prim.loc['source_balanced_accuracy','ci97_5']:+.3f}], "
         f"source AUC {prim.loc['source_AUC','point']:+.3f} [{prim.loc['source_AUC','ci2_5']:+.3f},{prim.loc['source_AUC','ci97_5']:+.3f}]")
print(f'total {time.time()-T0:.0f} s')
