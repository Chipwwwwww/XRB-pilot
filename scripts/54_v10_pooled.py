"""v10a / v10b (preregistration_v10.md sec. 2, 4, 5): pooled cross-instrument tests over the union of sources.
IC3 source identity (labels consistent across instruments); IC2 (single-component pooled bootstrap reproduces v8a; single-
instrument pooled permutation D equals v6lib.perm_test D).
v10a PRIMARY: equal-weight mean of the hard-like observation-level AUC gains (LR) of RXTE S1 (v5 vs v2 OOF), RXTE X (frozen v6),
NICER (full-data LOSO). v10b PRIMARY: mean over RXTE and NICER of the colour-conditional D(log10 nu_c), joint label permutation."""
import os, sys, time, zlib
os.environ['XRB_VERSION'] = 'v10'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
import config as C
import v4lib as L, v6lib as L6, v7lib as L7, v8lib as L8, v10lib as L10
from plotstyle import plt, CLASS_COLOR, INK, INK2

T0 = time.time()
RA, RB, FG = ROOT/'results/v10a', ROOT/'results/v10b', ROOT/'figures/v10'
for p in (RA, RB, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)

# ---------------- IC3 source identity ----------------
rx = pd.concat([pd.read_csv(ROOT/f'data/{v}/sources.csv')[['source_id', 'ra_deg', 'dec_deg', 'label']] for v in ('v2', 'v4b2', 'v6', 'v7b2', 'v8b')])
rx = rx.drop_duplicates('source_id').rename(columns={'ra_deg': 'ra', 'dec_deg': 'dec'})
NF = pd.read_csv(ROOT/'data/v10/processed/nicer_full_features.csv', dtype={'obsid': str})
ns = pd.read_csv(ROOT/'data/v9/sources.csv'); ns = ns[ns.name.isin(NF.source)]
cmap, mt = L10.canonical_map(rx, ns[['name', 'ra', 'dec', 'label']])
mt.to_csv(RA/'source_identity.csv', index=False)
bad = mt[mt.nicer_name.notna() & (mt.rxte_label != mt.nicer_label)]
print(f'IC3: {int(mt.nicer_name.notna().sum())} RXTE sources matched to NICER; label conflicts: {len(bad)}', flush=True)
print(mt[mt.nicer_name.notna()][['rxte_source', 'nicer_name', 'rxte_label', 'sep_deg']].round(4).to_string(index=False), flush=True)
if len(bad): print(bad.to_string()); progress('v10_pooled', 'IC3 FAILED'); sys.exit(3)
canon = lambda d: d.assign(source_id=d.source_id.map(lambda s: cmap.get(s, s)))

# ---------------- components (v10a) ----------------
st = pd.read_csv(ROOT/'results/v7a/states.csv', dtype={'obs_id': str}); stS1 = st.set_index('obs_id').state
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
v5 = pd.read_csv(ROOT/'results/v5/v5_oof_predictions.csv', dtype={'obs_id': str})
S1A, S1B = v5[(v5['sample'] == 'S1') & (v5['name'] == 'H+T|LogReg')], v2[(v2.representation == 'H_colours') & (v2.model == 'LogReg')]
S1A_rf, S1B_rf = v5[(v5['sample'] == 'S1') & (v5['name'] == 'H+T|RandomForest')], v2[(v2.representation == 'H_colours') & (v2.model == 'RandomForest')]
xs = pd.read_csv(ROOT/'results/v8b/v8b_external_scores.csv', dtype={'obs_id': str}); xs = xs[xs.role != 'stress_slow_pulsar']
XA, XB = xs[xs.name == 'H_R+T-LR'], xs[xs.name == 'H_R-LR']; stX = XA.set_index('obs_id').state

# IC2a: single-component pooled bootstrap (original names) reproduces the v8a PRIMARY
labS1 = st.drop_duplicates('source_id').set_index('source_id').label.to_dict()
P, B, pp, pb = L10.pooled_boot([dict(name='S1', A=S1A, B=S1B, groups=stS1, stratum='hard-like')], labS1)
v8a = pd.read_csv(ROOT/'results/v8a/v8a_metrics.csv'); ref = v8a[v8a.role == 'PRIMARY'].iloc[0]
mine = L8.summarize(pp, pb)
ic2a = bool(np.allclose([ref.point, ref.ci2_5, ref.ci97_5], [mine['point'], mine['ci2_5'], mine['ci97_5']], atol=1e-12))
print('IC2a pooled_boot(S1 only) = v8a PRIMARY:', ic2a, (round(mine['point'], 4), round(mine['ci2_5'], 4), round(mine['ci97_5'], 4)), flush=True)
if not ic2a: sys.exit(3)

# NICER component: LOSO on the full-data features
F = NF[NF.status == 'ok'].rename(columns={'obsid': 'obs_id', 'source': 'source_id'}).reset_index(drop=True)
y, g, o = F.label.eq('BH').astype(int).values, F.source_id.values, F.obs_id.values
Hn, Tn = F[['c1', 'c2']].values.astype(float), F[['T1', 'T2', 'T3']].values.astype(float)


def loso(X, alg):
    s = np.full(len(y), np.nan)
    for src in np.unique(g):
        te = g == src; s[te] = L.V4Model(alg).fit(X[~te], y[~te]).score(X[te])
    return s


SP = {'H_N-LR': (Hn, 'LogReg'), 'H_N+T_N-LR': (np.c_[Hn, Tn], 'LogReg'), 'H_N-RF': (Hn, 'RandomForest'), 'H_N+T_N-RF': (np.c_[Hn, Tn], 'RandomForest')}
res = Parallel(n_jobs=4)(delayed(loso)(X, a) for X, a in SP.values())
NO = {k: L.to_oof(np.arange(len(y)), s, 0.5, y, g, o, 'NICER full', k) for k, s in zip(SP, res)}
pd.concat([v.assign(name=k) for k, v in NO.items()]).merge(F[['obs_id', 'state', 'rate_2_10', 'bkg_ratio_12_15']], on='obs_id').to_csv(RA/'v10_nicer_full_oof.csv', index=False)
stN = F.set_index('obs_id').state

COMP = [dict(name='RXTE S1', A=canon(S1A), B=canon(S1B), groups=stS1, stratum='hard-like'),
        dict(name='RXTE X', A=canon(XA), B=canon(XB), groups=stX, stratum='hard-like'),
        dict(name='NICER (full)', A=NO['H_N+T_N-LR'], B=NO['H_N-LR'], groups=stN, stratum='hard-like')]
lab = {}
for c in COMP:
    for d in (c['A'], c['B']): lab.update(d.drop_duplicates('source_id').set_index('source_id').true_label.to_dict())
nb = sum(v == 'BH' for v in lab.values()); print(f'union: {len(lab)} sources ({nb} BH)', flush=True)
P, B, pp, pb = L10.pooled_boot(COMP, lab)
rows = []
for c, p_, b_ in zip(COMP, P, B.T):
    hh = c['A'][c['A'].obs_id.map(c['groups']) == 'hard-like']
    rows.append(dict(component=c['name'], **L8.summarize(p_, b_), n_hard_obs=len(hh), n_BH_sources=hh[hh.true_label == 'BH'].source_id.nunique(),
                     n_NS_sources=hh[hh.true_label == 'NS'].source_id.nunique(), role='component'))
prim = dict(component='POOLED (equal weights)', **L8.summarize(pp, pb), role='PRIMARY'); prim['verdict'] = L8.verdict(prim); rows.append(prim)
w = np.array([r['n_BH_sources'] for r in rows[:3]], float); w /= w.sum()
rows.append(dict(component='pooled, weighted by BH sources', **L8.summarize(float(P @ w), B @ w), role='descriptive'))
# RF: RXTE S1 + NICER
Prf, Brf, pprf, pbrf = L10.pooled_boot([dict(name='RXTE S1 RF', A=canon(S1A_rf), B=canon(S1B_rf), groups=stS1, stratum='hard-like'),
                                        dict(name='NICER RF', A=NO['H_N+T_N-RF'], B=NO['H_N-RF'], groups=stN, stratum='hard-like')], lab)
for nm, p_, b_ in zip(('RXTE S1 (RF)', 'NICER full (RF)'), Prf, Brf.T): rows.append(dict(component=nm, **L8.summarize(p_, b_), role='descriptive'))
rows.append(dict(component='pooled RF (RXTE S1 + NICER)', **L8.summarize(pprf, pbrf), role='descriptive'))
# NICER background sensitivity
thr = float(np.nanquantile(F[F.rate_2_10 >= C.V10_BKG_BRIGHT_RATE].bkg_ratio_12_15, C.V10_BKG_QUANTILE))
keep = F[F.bkg_ratio_12_15 <= thr].obs_id
Pb, Bb, ppb, pbb = L10.pooled_boot(COMP[:2] + [dict(name='NICER bkg-screened', A=NO['H_N+T_N-LR'][NO['H_N+T_N-LR'].obs_id.isin(keep)],
                                                    B=NO['H_N-LR'][NO['H_N-LR'].obs_id.isin(keep)], groups=stN, stratum='hard-like')], lab)
rows.append(dict(component=f'NICER, background-screened (12-15/2-10 keV ratio <= {thr:.4f}; {len(F) - len(keep)} obs removed)', **L8.summarize(Pb[2], Bb[:, 2]), role='descriptive'))
rows.append(dict(component='pooled with background-screened NICER', **L8.summarize(ppb, pbb), role='descriptive'))
A10 = pd.DataFrame(rows); A10.to_csv(RA/'v10a_pooled_gain.csv', index=False)
print('\n[v10a]\n' + A10.drop(columns=[c for c in ('n_valid_draws',) if c in A10]).round(3).to_string(index=False), flush=True)
# influence: leave one BH source out (point estimates)
inf = []
for s in sorted(k for k, v in lab.items() if v == 'BH'):
    cc = [dict(c, A=c['A'][c['A'].source_id != s], B=c['B'][c['B'].source_id != s]) for c in COMP]
    pts = []
    for c in cc:
        sa = L8.strat_boot(c['A'], c['groups'], [])[c['stratum']][0][0] if (c['A'].obs_id.map(c['groups']) == 'hard-like').any() else np.nan
        sb_ = L8.strat_boot(c['B'], c['groups'], [])[c['stratum']][0][0]
        pts.append(sa - sb_)
    inf.append(dict(left_out=s, pooled=float(np.mean(pts)), **{c['name']: p_ for c, p_ in zip(COMP, pts)}))
INF = pd.DataFrame(inf); INF.to_csv(RA/'v10a_influence.csv', index=False)
print('\n[v10a influence, leave one BH source out]\n' + INF.round(3).to_string(index=False), flush=True)

# ---------------- v10b ----------------
RT = pd.read_csv(ROOT/'data/v10/processed/rxte_timing_table.csv', dtype={'obs_id': str})
RT = canon(RT[(RT.state == 'hard-like') & (RT.role != 'stress_slow_pulsar') & RT.nu_c.notna()].reset_index(drop=True))
NH = F[(F.state == 'hard-like') & F.nu_c.notna()].reset_index(drop=True)
resid = {'RXTE': L6.source_residuals(RT[['c1R', 'c2R']].values, np.log10(RT.nu_c.values), RT.source_id.values),
         'NICER': L6.source_residuals(NH[['c1', 'c2']].values, np.log10(NH.nu_c.values), NH.source_id.values)}
labB = {**RT.drop_duplicates('source_id').set_index('source_id').label.to_dict(), **NH.drop_duplicates('source_id').set_index('source_id').label.to_dict()}
# IC2b: single-instrument D equals v6lib.perm_test D
ic2b = []
for k, r in resid.items():
    lb = pd.Series({s: int(labB[s] == 'BH') for s in r.index})
    d6 = L6.perm_test(r, lb)['D']; d10 = L10.pooled_perm({k: r}, {s: labB[s] for s in r.index}, n_perm=200)['D']
    ic2b.append(dict(instrument=k, D_v6=d6, D_v10=d10, passed=bool(abs(d6 - d10) < 1e-12)))
ic2b = pd.DataFrame(ic2b); print('\nIC2b:\n' + ic2b.to_string(index=False), flush=True)
if not ic2b.passed.all(): sys.exit(3)
rows = []
for k in resid:
    sub = {s: labB[s] for s in resid[k].dropna().index}
    a = L10.pooled_perm({k: resid[k]}, sub)
    rows.append(dict(analysis=f'{k} alone (colour-conditional residual)', D=a['D'], p=a['p'], n_sources=len(sub), n_bh=sum(v == 'BH' for v in sub.values()), role='descriptive'))
a = L10.pooled_perm(resid, labB)
rows.append(dict(analysis='POOLED RXTE + NICER (colour-conditional residual)', D=a['D'], p=a['p'], n_sources=len(labB), n_bh=sum(v == 'BH' for v in labB.values()),
                 role='PRIMARY', verdict='difference (p < 0.05)' if a['p'] < 0.05 else 'not detected'))
# colour window (pre-registered in v10): source mean log10 nu_c inside the BH hard-like colour range
win = {}
for k, d, ax_ in (('RXTE', RT, 'c2R'), ('NICER', NH, 'c2')):
    lo, hi = d[d.label == 'BH'][ax_].min(), d[d.label == 'BH'][ax_].max()
    ww = d[(d[ax_] >= lo) & (d[ax_] <= hi)]
    win[k] = ww.groupby('source_id').nu_c.apply(lambda x: np.log10(x).mean())
    rows.append(dict(analysis=f'{k} colour window [{lo:.3f}, {hi:.3f}] on {ax_}', D=np.nan, p=np.nan, n_sources=len(win[k]),
                     n_bh=int(sum(labB[s] == 'BH' for s in win[k].index)), role='window'))
for k in win:
    sub = {s: labB[s] for s in win[k].index}; a = L10.pooled_perm({k: win[k]}, sub)
    rows.append(dict(analysis=f'{k} colour window: BH - NS mean log10 nu_c', D=a['D'], p=a['p'], n_sources=len(sub), n_bh=sum(v == 'BH' for v in sub.values()), role='descriptive'))
labW = {s: labB[s] for k in win for s in win[k].index}
a = L10.pooled_perm(win, labW)
rows.append(dict(analysis='POOLED colour window: BH - NS mean log10 nu_c (pre-registered descriptive)', D=a['D'], p=a['p'], n_sources=len(labW),
                 n_bh=sum(v == 'BH' for v in labW.values()), role='descriptive'))
B10 = pd.DataFrame(rows); B10.to_csv(RB/'v10b_pooled_nuc.csv', index=False)
print('\n[v10b]\n' + B10.round(4).to_string(index=False), flush=True)
infb = []
for s in sorted(k for k, v in labB.items() if v == 'BH'):
    rr = {k: v.drop(s, errors='ignore') for k, v in resid.items()}; lb_ = {k: v for k, v in labB.items() if k != s}
    infb.append(dict(left_out=s, D_pooled=L10.pooled_perm(rr, lb_, n_perm=1)['D']))
INFB = pd.DataFrame(infb); INFB.to_csv(RB/'v10b_influence.csv', index=False); print('\n[v10b influence]\n' + INFB.round(3).to_string(index=False), flush=True)

# ---------------- figure ----------------
fig, ax = plt.subplots(1, 3, figsize=(17, 4.8), layout='constrained')
a = ax[0]; d = A10[A10.role.isin(['component', 'PRIMARY'])].reset_index(drop=True)
yy = np.arange(len(d))
a.errorbar(d.point, yy, xerr=[d.point - d.ci2_5, d.ci97_5 - d.point], fmt='o', capsize=3, color=INK)
a.scatter(d.point.iloc[-1:], yy[-1:], s=80, color='#c2410c', zorder=3)
a.set_yticks(yy); a.set_yticklabels(d.component, fontsize=8); a.invert_yaxis(); a.axvline(0, color=INK2, lw=.7, ls='--')
a.set_xlabel('hard-like AUC gain from timing (H+T-LR - H-LR)')
a.set_title(f'(a) v10a: pooled = {pp:+.3f} [{prim["ci2_5"]:+.3f}, {prim["ci97_5"]:+.3f}] (PRIMARY)', loc='left', fontsize=9)
a = ax[1]
for i, (k, r) in enumerate(resid.items()):
    for s, v in r.dropna().items():
        a.scatter(v, i + np.random.default_rng(zlib.crc32(s.encode())).uniform(-0.2, 0.2), s=22, color=CLASS_COLOR[labB[s]], alpha=.8)
a.set_yticks([0, 1]); a.set_yticklabels(list(resid)); a.axvline(0, color=INK2, lw=.6)
pB = B10[B10.role == 'PRIMARY'].iloc[0]
a.set_xlabel('source-mean residual of log10 nu_c (colour-conditional; blue BH, orange NS)')
a.set_title(f'(b) v10b: pooled D = {pB.D:+.3f} dex, p = {pB.p:.4f} (PRIMARY)', loc='left', fontsize=9)
a = ax[2]
a.barh(np.arange(len(INF)), INF.pooled, color='#2a78d6'); a.set_yticks(np.arange(len(INF))); a.set_yticklabels(INF.left_out, fontsize=7)
a.axvline(pp, color='#c2410c', lw=1, ls='--', label='all sources'); a.axvline(0, color=INK2, lw=.6); a.legend(frameon=False, fontsize=7)
a.set_xlabel('pooled gain with this BH source left out'); a.set_title('(c) v10a influence (leave one BH source out)', loc='left', fontsize=9)
fig.savefig(FG/'v10_pooled.png'); plt.close(fig)
print(f"\nPRIMARY v10a pooled gain {pp:+.3f} [{prim['ci2_5']:+.3f},{prim['ci97_5']:+.3f}] -> {prim['verdict']}")
print(f"PRIMARY v10b pooled D {pB.D:+.3f}, p = {pB.p:.4f} -> {pB.verdict}")
progress('v10_pooled', f"v10a {pp:+.3f} [{prim['ci2_5']:+.3f},{prim['ci97_5']:+.3f}]; v10b D {pB.D:+.3f} p {pB.p:.4f}")
print(f'total {time.time() - T0:.0f} s')
