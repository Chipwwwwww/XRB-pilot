"""v13 analysis (preregistration_v13.md): third disjoint NICER set, frozen v12 pipeline (3C50 correction + screening, identical to
59_v12_analysis.corrected) and out-of-source models fitted on data/v12/processed/nicer_corrected_screened.csv.
IC1 Z sources soft-like. v13a PRIMARY: hard-like AUC gain frozen H_N+T_N-RF - H_N-RF. v13b PRIMARY: colour-conditional D(log10 nu_c).
Descriptive: LR, soft-like, source level, frozen rule nu* = 1.3361 Hz, uncorrected/unscreened, influence, 3C50-GTI-restricted features."""
import os, sys, time, json
os.environ['XRB_VERSION'] = 'v13'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from astropy.io import fits
import config as C
import v4lib as L, v6lib as L6, v7lib as L7, v8lib as L8, v9lib as L9, v10lib as L10
from plotstyle import plt, CLASS_COLOR, INK, INK2

T0 = time.time()
R13, FG = ROOT/'results/v13', ROOT/'figures/v13'
for p in (R13, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
NU_STAR = 1.3361                     # frozen before any v13 data (logs/v13/nu_star_frozen.txt)
HC, TC = ['c1', 'c2'], ['T1', 'T2', 'T3']
MOD = {'H_N-RF': (HC, 'RandomForest'), 'H_N+T_N-RF': (HC + TC, 'RandomForest'), 'H_N-LR': (HC, 'LogReg'), 'H_N+T_N-LR': (HC + TC, 'LogReg')}


def corrected(F, fmax, correct=True):                      # identical to 59_v12_analysis.corrected
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


P = pd.read_csv(ROOT/'data/v12/processed/nicer_corrected_screened.csv', dtype={'obsid': str})
cols = ['obsid', 'source', 'label', 'c1', 'c2', 'cA', 'cB', 'cC', 'T1', 'T2', 'T3', 'STATE', 'nu_c', 'rate_2_10', 'state', 'url']
N = pd.read_csv(ROOT/'data/v13/processed/nicer_new_features.csv', dtype={'obsid': str}); N = N[N.status == 'ok'][cols]
B = pd.read_csv(ROOT/'data/v13/processed/bkg3c50.csv', dtype={'obsid': str})
F = N.merge(B[['obsid', 'status', 'T_T', 'f_A', 'f_B', 'f_C', 'f_T']].rename(columns={'status': 'bkg_status'}), on='obsid', how='left')
F['bkg_status'] = np.where(F.rate_2_10 >= C.V12_BKG_MAX_RATE, 'bright (not run)', F.bkg_status.fillna('missing'))
Q = corrected(F, C.V12_FBKG_MAX)
print(f'v13: {len(F)} accepted, {len(Q)} kept after 3C50 screening; 3C50 status:', F.bkg_status.str.slice(0, 22).value_counts().to_dict(), flush=True)
print(Q.groupby(['label', 'state']).agg(n=('obsid', 'size'), src=('source', 'nunique')).to_string(), flush=True)
z = Q[Q.source.isin(C.V9_Z_SANITY)]; zf = float((z.state == 'soft-like').mean()) if len(z) else np.nan
ic = pd.DataFrame([dict(check='IC1 Z sources soft-like (v13, corrected)', n=len(z), value=zf, passed=bool(zf >= C.V7_SANITY_FRAC))])
ic.to_csv(R13/'ic_checks.csv', index=False); print(ic.to_string(index=False), flush=True)
if not ic.passed.all(): sys.exit(3)


# ---------------- frozen out-of-source predictions ----------------
def predict(Qd):
    out = {k: np.full(len(Qd), np.nan) for k in MOD}
    yP = P.label.eq('BH').astype(int).values
    for src in Qd.source.unique():
        te = (Qd.source == src).values; tr = (P.source != src).values
        for name, (cl, alg) in MOD.items():
            out[name][te] = L.V4Model(alg).fit(P.loc[tr, cl].values.astype(float), yP[tr]).score(Qd.loc[te, cl].values.astype(float))
    y, g, o = Qd.label.eq('BH').astype(int).values, Qd.source.values, Qd.obsid.values
    return {k: L.to_oof(np.arange(len(Qd)), s, 0.5, y, g, o, 'NICER v13 (frozen)', k) for k, s in out.items()}


OOF = predict(Q)
pd.concat([v.assign(name=k) for k, v in OOF.items()]).merge(Q[['obsid', 'state', 'nu_c', 'f_used']].rename(columns={'obsid': 'obs_id'}), on='obs_id').to_csv(R13/'v13_frozen_predictions.csv', index=False)
labs = Q.drop_duplicates('source').set_index('source').label.to_dict(); draws = L7.boot_draws(labs); stmap = Q.set_index('obsid').state
hx = Q[Q.state == 'hard-like']; nbh, nns = hx[hx.label == 'BH'].source.nunique(), hx[hx.label == 'NS'].source.nunique()
testable = nbh >= C.V9_MIN_SOURCES_PER_CLASS and nns >= C.V9_MIN_SOURCES_PER_CLASS
print(f'v13 hard-like: {len(hx)} obs, {nbh} BH / {nns} NS sources -> testable {testable}', flush=True)
sb = {k: L8.strat_boot(v, stmap, draws) for k, v in OOF.items()}
rows = []
for k, d in sb.items():
    for st in ('soft-like', 'hard-like'):
        if st in d: rows.append(dict(analysis=st, comparison=k, **L8.summarize(d[st][0][0], d[st][1][:, 0])))
for a_, b_ in (('H_N+T_N-RF', 'H_N-RF'), ('H_N+T_N-LR', 'H_N-LR')):
    for st in ('soft-like', 'hard-like'):
        if st in sb[a_] and st in sb[b_]:
            r = dict(analysis=st, comparison=f'{a_} - {b_}', **L8.summarize(sb[a_][st][0][0] - sb[b_][st][0][0], sb[a_][st][1][:, 0] - sb[b_][st][1][:, 0]))
            r['role'] = 'PRIMARY' if (a_ == 'H_N+T_N-RF' and st == 'hard-like' and testable) else 'descriptive'; r['verdict'] = L8.verdict(r); rows.append(r)
bsrc = L.paired_bootstrap({k: OOF[k][OOF[k].obs_id.isin(hx.obsid)] for k in ('H_N-RF', 'H_N+T_N-RF')}, 'H_N-RF')
for r in bsrc.to_dict('records'): r['analysis'] = 'hard-like source level'; r['role'] = 'descriptive'; rows.append(r)
inf = []
for s in sorted(hx[hx.label == 'BH'].source.unique()):
    kk = OOF['H_N-RF'].source_id != s
    inf.append(dict(left_out=s, rf_gain=L8.strat_boot(OOF['H_N+T_N-RF'][kk], stmap, [])['hard-like'][0][0] - L8.strat_boot(OOF['H_N-RF'][kk], stmap, [])['hard-like'][0][0]))
R13a = pd.DataFrame(rows); R13a.to_csv(R13/'v13a_gain.csv', index=False); pd.DataFrame(inf).to_csv(R13/'v13a_influence.csv', index=False)
rr = hx.assign(rule=hx.nu_c < NU_STAR); srr = rr.groupby(['source', 'label']).rule.mean().reset_index()
rule = pd.DataFrame([dict(nu_star_Hz=NU_STAR, obs_sensitivity=float(rr[rr.label == 'BH'].rule.mean()), obs_specificity=float(1 - rr[rr.label == 'NS'].rule.mean()),
                          source_sensitivity=float((srr[srr.label == 'BH'].rule >= .5).mean()), source_specificity=float((srr[srr.label == 'NS'].rule < .5).mean()),
                          n_BH_src=int((srr.label == 'BH').sum()), n_NS_src=int((srr.label == 'NS').sum()))])
rule.to_csv(R13/'v13_frozen_rule.csv', index=False)
print('\n[v13a]\n' + R13a[R13a.metric.isna() | (R13a.metric == 'source_AUC')][['analysis', 'comparison', 'point', 'ci2_5', 'ci97_5']].round(3).to_string(index=False), flush=True)
print('influence (RF gain, leave one BH out):', pd.DataFrame(inf).rf_gain.round(3).tolist(), '\nfrozen rule:\n' + rule.round(3).to_string(index=False), flush=True)


# ---------------- v13b ----------------
def nuc(d, tag, role='descriptive'):
    h = d[(d.state == 'hard-like') & d.nu_c.notna()].reset_index(drop=True)
    lab = h.drop_duplicates('source').set_index('source').label.eq('BH').astype(int)
    r_ = L6.source_residuals(h[HC].values, np.log10(h.nu_c.values), h.source.values); a = L6.perm_test(r_, lab)
    return dict(analysis=tag, D=a['D'], p=a['p'], n_obs=len(h), n_sources=a['n_sources'], n_bh=a['n_bh'], role=role), r_, lab


rowsB = []
rb, r_prim, lab_prim = nuc(Q, 'v13b: corrected + screened (frozen v12 pipeline)', 'PRIMARY'); rb['verdict'] = 'difference (p < 0.05)' if rb['p'] < 0.05 else 'not detected'; rowsB.append(rb)
U = F.copy(); rowsB.append(nuc(U, 'no screening, no correction')[0])
for s in sorted(lab_prim[lab_prim == 1].index):
    r2 = r_prim.drop(s); l2 = lab_prim.drop(s)
    rowsB.append(dict(analysis=f'influence: without {s}', D=float(r2[l2 == 1].mean() - r2[l2 == 0].mean()), role='influence'))


# ---------------- 3C50-GTI-restricted features (descriptive) ----------------
def gti_restricted(o):
    try:
        cl = L10.EXT/'nicer_v13_cl'/o/f'ni{o}_0mpu7_cl.evt.gz'; tot = L10.EXT.parent/'nicer_bkg_spectra'/o/f'tot_{o}.pi'
        if not (cl.exists() and tot.exists()): return dict(obsid=o, gstatus='missing files')
        arr, h, comp = L9.read_prefix(cl)
        with fits.open(tot) as hh: g = np.c_[hh['GTI'].data.field(0), hh['GTI'].data.field(1)]
        m = np.zeros(len(arr['TIME']), bool)
        for a, b in g: m |= (arr['TIME'] >= a) & (arr['TIME'] < b)
        rec = L9.obs_features({k: v[m] for k, v in arr.items()})
        return dict(obsid=o, gstatus=rec.get('status'), **{f'g_{k}': rec.get(k) for k in ('T1', 'T2', 'T3', 'STATE', 'nu_c', 'c1', 'c2', 'cA', 'cB', 'cC', 'rate_2_10', 'n_seg')})
    except Exception as e:
        return dict(obsid=o, gstatus=f'error {type(e).__name__}: {e}'[:120])


faint = F[F.bkg_status == 'ok'].obsid.tolist()
G = pd.DataFrame(Parallel(n_jobs=2)(delayed(gti_restricted)(o) for o in faint)); G.to_csv(R13/'v13_gti_restricted_features.csv', index=False)
FG2 = F.merge(G, on='obsid', how='left')
use = FG2.gstatus.eq('ok')
for k in ('T1', 'T2', 'T3', 'STATE', 'nu_c', 'cA', 'cB', 'cC'): FG2.loc[use, k] = FG2.loc[use, f'g_{k}']
FG2 = FG2[(FG2.bkg_status == 'bright (not run)') | use]
rowsB.append(nuc(corrected(FG2, C.V12_FBKG_MAX), f'3C50-GTI-restricted features for faint observations ({int(use.sum())} recomputed)')[0])
Qg = corrected(FG2, C.V12_FBKG_MAX); Og = predict(Qg); stg = Qg.set_index('obsid').state
dg = L7.boot_draws(Qg.drop_duplicates('source').set_index('source').label.to_dict())
sa, sb_ = L8.strat_boot(Og['H_N+T_N-RF'], stg, dg)['hard-like'], L8.strat_boot(Og['H_N-RF'], stg, dg)['hard-like']
R13gti = dict(analysis='3C50-GTI-restricted: RF hard-like gain', **L8.summarize(sa[0][0] - sb_[0][0], sa[1][:, 0] - sb_[1][:, 0]))
R13b = pd.DataFrame(rowsB); R13b.to_csv(R13/'v13b_nuc.csv', index=False); pd.DataFrame([R13gti]).to_csv(R13/'v13a_gti_restricted.csv', index=False)
print('\n[v13b]\n' + R13b.round(4).to_string(index=False), '\n', R13gti, flush=True)

# ---------------- figure ----------------
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), layout='constrained')
a = ax[0]; names = ['H_N-LR', 'H_N+T_N-LR', 'H_N-RF', 'H_N+T_N-RF']
for i, m in enumerate(names):
    for st, dx, col in (('soft-like', -0.15, '#9aa5b1'), ('hard-like', 0.15, '#2a78d6')):
        r = R13a[(R13a.analysis == st) & (R13a.comparison == m)]
        if len(r): r = r.iloc[0]; a.errorbar([i + dx], [r.point], yerr=[[r.point - r.ci2_5], [r.ci97_5 - r.point]], fmt='o', color=col, capsize=2, ms=5, label=st if i == 0 else None)
pp = R13a[R13a.role == 'PRIMARY']
ttl = f'{pp.iloc[0].point:+.3f} [{pp.iloc[0].ci2_5:+.3f}, {pp.iloc[0].ci97_5:+.3f}]' if len(pp) else 'not testable'
a.set_xticks(range(4)); a.set_xticklabels(names, fontsize=8); a.axhline(.5, color=INK2, lw=.6, ls='--'); a.set_ylim(0.2, 1.03); a.legend(frameon=False, fontsize=7)
a.set_ylabel('observation-level AUC (v13, frozen out-of-source)'); a.set_title(f'(a) v13a: RF hard-like gain = {ttl} (PRIMARY)', loc='left', fontsize=9)
a = ax[1]; h = Q[(Q.state == 'hard-like') & Q.nu_c.notna()]
for lab_, d in h.groupby('label'): a.scatter(d.c2, d.nu_c, s=14, alpha=.7, color=CLASS_COLOR[lab_], label=f'{lab_} ({d.source.nunique()} src)')
a.axhline(NU_STAR, color=INK2, ls='--', lw=.8, label=f'frozen nu* = {NU_STAR} Hz'); a.set_yscale('log'); a.legend(frameon=False, fontsize=7)
a.set_xlabel('corrected c2'); a.set_ylabel('nu_c (Hz)'); a.set_title(f"(b) v13b: D(log nu_c) = {rb['D']:+.3f}, p = {rb['p']:.4f} (PRIMARY)", loc='left', fontsize=9)
fig.savefig(FG/'v13_prospective.png'); plt.close(fig)
for r in pp.itertuples(): print(f'PRIMARY v13a {r.comparison}: {r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}] -> {r.verdict}')
print(f"PRIMARY v13b D = {rb['D']:+.3f}, p = {rb['p']:.4f} -> {rb['verdict']}")
progress('v13_analysis', (f'v13a {pp.iloc[0].point:+.3f} [{pp.iloc[0].ci2_5:+.3f},{pp.iloc[0].ci97_5:+.3f}]' if len(pp) else 'v13a not testable') + f"; v13b D {rb['D']:+.3f} p {rb['p']:.4f}")
print(f'total {time.time() - T0:.0f} s')
