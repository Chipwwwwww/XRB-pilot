"""v12 analysis (preregistration_v12.md sec. 3-6): 3C50 background correction and screening of the v10 + v11 NICER observations.
IC1 (3C50 total rate vs pipeline rate), IC2 (background fractions within [0, 1]), IC3 (Z sources soft-like after correction).
v12a PRIMARY: colour-conditional D(log10 nu_c) in the corrected, screened hard-like observations (source permutation).
v12b PRIMARY: hard-like observation-level AUC gain H_N+T_N-RF - H_N-RF, LOSO over sources on the corrected, screened data."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v12'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
import config as C
import v4lib as L, v5lib as L5, v6lib as L6, v7lib as L7, v8lib as L8, v10lib as L10
from plotstyle import plt, CLASS_COLOR, INK, INK2

T0 = time.time()
R12, FG = ROOT/'results/v12', ROOT/'figures/v12'
for p in (R12, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
cols = ['obsid', 'source', 'label', 'c1', 'c2', 'cA', 'cB', 'cC', 'T1', 'T2', 'T3', 'STATE', 'nu_c', 'rate_2_10', 'state']
V = pd.read_csv(ROOT/'data/v10/processed/nicer_full_features.csv', dtype={'obsid': str}); V = V[V.status == 'ok'][cols].assign(sample='v10')
N = pd.read_csv(ROOT/'data/v11/processed/nicer_new_features.csv', dtype={'obsid': str})
N = N[N.status == 'ok'][cols].assign(sample='v11')        # all 318 v11 observations (preregistration: 684 = 366 + 318)
F = pd.concat([V, N], ignore_index=True)
B = pd.read_csv(ROOT/'data/v12/processed/bkg3c50.csv', dtype={'obsid': str})
F = F.merge(B[['obsid', 'status', 'T_T', 'f_A', 'f_B', 'f_C', 'f_T']].rename(columns={'status': 'bkg_status'}), on='obsid', how='left')
F['bkg_status'] = np.where(F.rate_2_10 >= C.V12_BKG_MAX_RATE, 'bright (not run)', F.bkg_status.fillna('missing'))
print(f'{len(F)} NICER observations; 3C50 status:', F.bkg_status.str.slice(0, 25).value_counts().to_dict(), flush=True)

# ---------------- IC1 / IC2 ----------------
ok = F[F.bkg_status == 'ok']
ratio = ok.T_T / ok.rate_2_10; lo, hi = C.V12_IC_TOT_RATIO
ic = [dict(check='IC1 3C50 total 2-10 keV rate / pipeline rate in [0.7, 1.3]', value=float(ratio.between(lo, hi).mean()), threshold=0.90),
      dict(check='IC2 background fraction f in [0, 1]', value=float(ok.f_T.between(0, 1).mean()), threshold=0.95)]
ic = pd.DataFrame(ic); ic['passed'] = ic.value >= ic.threshold
print(ic.to_string(index=False), '| ratio median', round(float(ratio.median()), 3), flush=True)
if not ic.passed.all(): ic.to_csv(R12/'ic_checks.csv', index=False); sys.exit(3)


# ---------------- correction / screening ----------------
def corrected(F, fmax, correct=True):
    d = F.copy()
    f = np.where(d.bkg_status == 'bright (not run)', 0.0, d.f_T)
    keep = (d.bkg_status == 'bright (not run)') | ((d.bkg_status == 'ok') & (f <= fmax))
    d = d[keep].copy(); f = f[keep.values]
    if correct:
        k = 1.0 / (1.0 - f)
        for c in ('T1', 'T2', 'T3', 'STATE'): d[c] = d[c] * k
        fa, fb, fc = [np.where(d.bkg_status == 'ok', d[x], 0.0) for x in ('f_A', 'f_B', 'f_C')]
        A, Bb, Cc = d.cA * (1 - fa), d.cB * (1 - fb), d.cC * (1 - fc)
        d['c1'], d['c2'] = Bb / A, Cc / Bb
        d['state'] = np.where(d.STATE > C.V7_RMS_HARD, 'hard-like', np.where(d.STATE < C.V7_RMS_SOFT, 'soft-like', 'intermediate'))
    d['f_used'] = f
    return d.reset_index(drop=True)


P = corrected(F, C.V12_FBKG_MAX)
z = P[P.source.isin(C.V9_Z_SANITY)]; zf = float((z.state == 'soft-like').mean())
ic = pd.concat([ic, pd.DataFrame([dict(check='IC3 Z sources soft-like after correction', value=zf, threshold=C.V7_SANITY_FRAC, passed=bool(zf >= C.V7_SANITY_FRAC))])])
ic.to_csv(R12/'ic_checks.csv', index=False); print(ic.tail(1).to_string(index=False), flush=True)
if zf < C.V7_SANITY_FRAC: sys.exit(3)
print(f'screened/corrected: {len(P)} of {len(F)} kept; state changes vs uncorrected among kept:',
      int((P.state != P.obsid.map(F.set_index("obsid").state)).sum()), flush=True)
print(P.groupby(['label', 'state']).agg(n=('obsid', 'size'), src=('source', 'nunique')).to_string(), flush=True)


def nuc_test(d, tag, role='descriptive'):
    h = d[(d.state == 'hard-like') & d.nu_c.notna()].reset_index(drop=True)
    lab = h.drop_duplicates('source').set_index('source').label.eq('BH').astype(int)
    a = L6.perm_test(L6.source_residuals(h[['c1', 'c2']].values, np.log10(h.nu_c.values), h.source.values), lab)
    return dict(analysis=tag, D=a['D'], p=a['p'], n_obs=len(h), n_sources=a['n_sources'], n_bh=a['n_bh'], role=role)


rows = [nuc_test(P, 'v12a: corrected + screened (f <= 0.20), v10 + v11 observations', 'PRIMARY')]
rows[0]['verdict'] = 'difference (p < 0.05)' if rows[0]['p'] < 0.05 else 'not detected'
for fm in C.V12_FBKG_SENS: rows.append(nuc_test(corrected(F, fm), f'threshold f <= {fm:.2f}'))
rows.append(nuc_test(corrected(F, C.V12_FBKG_MAX, correct=False), 'screened only (no correction)'))
U = F.copy(); U['f_used'] = np.nan; rows.append(nuc_test(U, 'no screening, no correction (all v10 + v11 observations)'))
for smp in ('v10', 'v11'): rows.append(nuc_test(P[P['sample'] == smp], f'corrected + screened, {smp} observations only'))
M = F.copy(); M.loc[M.bkg_status.str.startswith(('failed', 'missing')), ['bkg_status', 'f_T', 'f_A', 'f_B', 'f_C']] = ['ok', 0.0, 0.0, 0.0, 0.0]
rows.append(nuc_test(corrected(M, C.V12_FBKG_MAX), '3C50-failed observations included without correction'))
# pooled with RXTE (RXTE background fraction from the Standard-1 / StdProd rates; same f <= 0.20 screen)
RT = pd.read_csv(ROOT/'data/v10/processed/rxte_timing_table.csv', dtype={'obs_id': str})
T5 = pd.concat([pd.read_csv(ROOT/'data/v5/processed/timing_features.csv', dtype={'obs_id': str}),
                pd.read_csv(ROOT/'data/v6/processed/timing_v5_new.csv', dtype={'obs_id': str})]).drop_duplicates('obs_id').set_index('obs_id')
miss = RT[~RT.obs_id.isin(T5.index)]
paths = pd.concat([pd.read_csv(ROOT/f'data/{v}/observations.csv', dtype={'obs_id': str}, low_memory=False)[['obs_id', 'path_src', 'path_bkg']]
                   for v in ('v7b2', 'v8b')]).drop_duplicates('obs_id').set_index('obs_id')
extra = pd.DataFrame(Parallel(n_jobs=4)(delayed(L5.obs_timing)(o, paths.loc[o].path_src, paths.loc[o].path_bkg) for o in miss.obs_id)).set_index('obs_id')
TT = pd.concat([T5[['bkg_rate_per_pcu', 'tot_rate_per_pcu']], extra[['bkg_rate_per_pcu', 'tot_rate_per_pcu']]])
RT['f_rxte'] = RT.obs_id.map(TT.bkg_rate_per_pcu / TT.tot_rate_per_pcu)
RTh = RT[(RT.state == 'hard-like') & (RT.role != 'stress_slow_pulsar') & RT.nu_c.notna() & (RT.f_rxte <= C.V12_FBKG_MAX)].reset_index(drop=True)
cm = pd.read_csv(ROOT/'results/v10a/source_identity.csv').set_index('rxte_source').canonical.to_dict()
RTh['source'] = RTh.source_id.map(lambda s: cm.get(s, s))
Ph = P[(P.state == 'hard-like') & P.nu_c.notna()].reset_index(drop=True)
resid = {'RXTE': L6.source_residuals(RTh[['c1R', 'c2R']].values, np.log10(RTh.nu_c.values), RTh.source.values),
         'NICER': L6.source_residuals(Ph[['c1', 'c2']].values, np.log10(Ph.nu_c.values), Ph.source.values)}
labB = {**RTh.drop_duplicates('source').set_index('source').label.to_dict(), **Ph.drop_duplicates('source').set_index('source').label.to_dict()}
a = L10.pooled_perm(resid, labB)
rows.append(dict(analysis=f'pooled RXTE (f <= 0.20, {len(RTh)} obs) + NICER (corrected, screened): mean D', D=a['D'], p=a['p'], n_obs=len(RTh) + len(Ph),
                 n_sources=len(labB), n_bh=sum(v == 'BH' for v in labB.values()), role='descriptive'))
R12a = pd.DataFrame(rows); R12a.to_csv(R12/'v12a_nuc.csv', index=False)
print('\n[v12a]\n' + R12a.round(4).to_string(index=False), flush=True)
# were the v11 'very hard' observations background-dominated?
vh = F[(F.c2 > 0.7) & (F.state == 'hard-like')]
print('\nuncorrected hard-like observations with c2 > 0.7:', len(vh), '| 3C50 f (2-10 keV):', vh.f_T.describe().round(3).to_dict(),
      '| status:', vh.bkg_status.value_counts().to_dict(), flush=True)
vh[['obsid', 'source', 'label', 'sample', 'c2', 'nu_c', 'rate_2_10', 'bkg_status', 'f_T']].to_csv(R12/'v12_very_hard_obs.csv', index=False)

# ---------------- v12b ----------------
y, g, o = P.label.eq('BH').astype(int).values, P.source.values, P.obsid.values
SP = {'H_N-RF': (['c1', 'c2'], 'RandomForest'), 'H_N+T_N-RF': (['c1', 'c2', 'T1', 'T2', 'T3'], 'RandomForest'),
      'H_N-LR': (['c1', 'c2'], 'LogReg'), 'H_N+T_N-LR': (['c1', 'c2', 'T1', 'T2', 'T3'], 'LogReg')}


def loso(cl, alg):
    X = P[cl].values.astype(float); s = np.full(len(y), np.nan)
    for src in np.unique(g):
        te = g == src; s[te] = L.V4Model(alg).fit(X[~te], y[~te]).score(X[te])
    return s


res = Parallel(n_jobs=2)(delayed(loso)(c, a_) for c, a_ in SP.values())
OOF = {k: L.to_oof(np.arange(len(y)), s, 0.5, y, g, o, 'NICER v12', k) for k, s in zip(SP, res)}
pd.concat([v.assign(name=k) for k, v in OOF.items()]).merge(P[['obsid', 'state', 'sample', 'f_used']].rename(columns={'obsid': 'obs_id'}), on='obs_id').to_csv(R12/'v12b_oof.csv', index=False)
draws = L7.boot_draws(P.drop_duplicates('source').set_index('source').label.to_dict()); stmap = P.set_index('obsid').state
sb = {k: L8.strat_boot(v, stmap, draws) for k, v in OOF.items()}
rows = []
for k, d in sb.items():
    for st in ('soft-like', 'hard-like'):
        if st in d: rows.append(dict(analysis=st, comparison=k, **L8.summarize(d[st][0][0], d[st][1][:, 0])))
for a_, b_ in (('H_N+T_N-RF', 'H_N-RF'), ('H_N+T_N-LR', 'H_N-LR')):
    for st in ('soft-like', 'hard-like'):
        r = dict(analysis=st, comparison=f'{a_} - {b_}', **L8.summarize(sb[a_][st][0][0] - sb[b_][st][0][0], sb[a_][st][1][:, 0] - sb[b_][st][1][:, 0]))
        r['role'] = 'PRIMARY' if (a_ == 'H_N+T_N-RF' and st == 'hard-like') else 'descriptive'; r['verdict'] = L8.verdict(r); rows.append(r)
hx = P[P.state == 'hard-like']
bsrc = L.paired_bootstrap({k: OOF[k][OOF[k].obs_id.isin(hx.obsid)] for k in ('H_N-RF', 'H_N+T_N-RF')}, 'H_N-RF')
for r in bsrc.to_dict('records'): r['analysis'] = 'hard-like source level'; r['role'] = 'descriptive'; rows.append(r)
R12b = pd.DataFrame(rows); R12b.to_csv(R12/'v12b_gain.csv', index=False)
print(f"\n[v12b] hard-like: {len(hx)} obs, {hx[hx.label == 'BH'].source.nunique()} BH / {hx[hx.label == 'NS'].source.nunique()} NS sources")
t = R12b.copy(); t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]" + (' *' if r.get('role') == 'PRIMARY' else ''), axis=1)
print(t.pivot_table(index='comparison', columns=['analysis', 'metric'] if 'metric' in t else 'analysis', values='txt', aggfunc='first').to_string(), flush=True)

# ---------------- figure ----------------
fig, ax = plt.subplots(1, 3, figsize=(17, 4.8), layout='constrained')
a = ax[0]; okb = F[F.bkg_status == 'ok']
for lab_, d in okb.groupby('label'): a.hist(np.log10(np.clip(d.f_T, 1e-4, None)), bins=40, alpha=.6, color=CLASS_COLOR[lab_], label=lab_)
a.axvline(np.log10(C.V12_FBKG_MAX), color=INK2, ls='--', lw=.8, label='f = 0.20 screen'); a.legend(frameon=False, fontsize=7)
a.set_xlabel('log10 background fraction f (3C50, 2-10 keV)'); a.set_ylabel('observations'); a.set_title('(a) NICER 3C50 background fractions (rate < 500 c/s)', loc='left', fontsize=9)
a = ax[1]
for lab_, d in Ph.groupby('label'): a.scatter(d.c2, d.nu_c, s=12, alpha=.7, color=CLASS_COLOR[lab_], label=f'{lab_} ({d.source.nunique()} src)')
a.set_yscale('log'); a.legend(frameon=False, fontsize=7); a.set_xlabel("corrected c2"); a.set_ylabel('nu_c (Hz)')
p1 = R12a.iloc[0]; a.set_title(f'(b) v12a: D(log nu_c) = {p1.D:+.3f}, p = {p1.p:.4f} (PRIMARY)', loc='left', fontsize=9)
a = ax[2]; names = ['H_N-LR', 'H_N+T_N-LR', 'H_N-RF', 'H_N+T_N-RF']
for i, m in enumerate(names):
    for st, dx, col in (('soft-like', -0.15, '#9aa5b1'), ('hard-like', 0.15, '#2a78d6')):
        r = R12b[(R12b.analysis == st) & (R12b.comparison == m)]
        if len(r): r = r.iloc[0]; a.errorbar([i + dx], [r.point], yerr=[[r.point - r.ci2_5], [r.ci97_5 - r.point]], fmt='o', color=col, capsize=2, ms=5, label=st if i == 0 else None)
pp = R12b[R12b.role == 'PRIMARY'].iloc[0]
a.set_xticks(range(4)); a.set_xticklabels(names, fontsize=8); a.axhline(.5, color=INK2, lw=.6, ls='--'); a.set_ylim(0.2, 1.03); a.legend(frameon=False, fontsize=7)
a.set_ylabel('observation-level AUC (NICER, corrected + screened)'); a.set_title(f'(c) v12b: RF hard-like gain = {pp.point:+.3f} [{pp.ci2_5:+.3f}, {pp.ci97_5:+.3f}] (PRIMARY)', loc='left', fontsize=9)
fig.savefig(FG/'v12_background.png'); plt.close(fig)
print(f"\nPRIMARY v12a D = {p1.D:+.3f}, p = {p1.p:.4f} -> {p1.verdict}")
print(f"PRIMARY v12b RF gain {pp.point:+.3f} [{pp.ci2_5:+.3f},{pp.ci97_5:+.3f}] -> {pp.verdict}")
progress('v12_analysis', f'v12a D {p1.D:+.3f} p {p1.p:.4f}; v12b {pp.point:+.3f} [{pp.ci2_5:+.3f},{pp.ci97_5:+.3f}]')
print(f'total {time.time() - T0:.0f} s')
