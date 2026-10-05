"""v11 analysis (preregistration_v11.md sec. 3-7). Frozen v10 NICER pipeline and models applied to never-used observations.
IC1: LOSO refit on the v10 NICER full features reproduces results/v10a/v10_nicer_full_oof.csv. IC2: Z sources soft-like in the new
data. Frozen rule nu* from v10. v11a PRIMARY: hard-like AUC gain of the out-of-source frozen H_N+T_N-LR over H_N-LR on the new
observations of the v9 sources. v11b PRIMARY: colour-conditional D(log10 nu_c) in the new hard-like observations.
v11c Lorentzian widths, v11d never-used sources, brightness-controlled nu_c (descriptive)."""
import os, sys, time, zlib
os.environ['XRB_VERSION'] = 'v11'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
import config as C
import v4lib as L, v6lib as L6, v7lib as L7, v8lib as L8, v11lib as L11
from plotstyle import plt, CLASS_COLOR, INK, INK2

T0 = time.time()
R11, FG = ROOT/'results/v11', ROOT/'figures/v11'
for p in (R11, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
FEAT_H, FEAT_T = ['c1', 'c2'], ['T1', 'T2', 'T3']
MOD = {'H_N-LR': (FEAT_H, 'LogReg'), 'H_N+T_N-LR': (FEAT_H + FEAT_T, 'LogReg'), 'H_N-RF': (FEAT_H, 'RandomForest'), 'H_N+T_N-RF': (FEAT_H + FEAT_T, 'RandomForest')}

# ---------------- training data (v10 NICER full) and IC1 ----------------
V = pd.read_csv(ROOT/'data/v10/processed/nicer_full_features.csv', dtype={'obsid': str})
V = V[V.status == 'ok'].reset_index(drop=True)
yv, gv = V.label.eq('BH').astype(int).values, V.source.values


def fit(cols, alg, mask):
    return L.V4Model(alg).fit(V.loc[mask, cols].values.astype(float), yv[mask])


ref = pd.read_csv(ROOT/'results/v10a/v10_nicer_full_oof.csv', dtype={'obs_id': str})
ic1 = []
for name, (cols, alg) in MOD.items():
    s = np.full(len(V), np.nan)
    for src in np.unique(gv):
        te = gv == src; s[te] = fit(cols, alg, ~te).score(V.loc[te, cols].values.astype(float))
    r = ref[ref.name == name].set_index('obs_id').BH_score.reindex(V.obsid).values
    ic1.append(dict(model=name, max_abs_diff=float(np.nanmax(np.abs(s - r)))))
ic1 = pd.DataFrame(ic1); ic1['passed'] = ic1.max_abs_diff < 1e-9
print('IC1 (LOSO refit = v10 OOF):\n' + ic1.to_string(index=False), flush=True)
ic1.to_csv(R11/'ic1_refit.csv', index=False)
if not ic1.passed.all(): sys.exit(3)

# frozen simple rule from v10 hard-like observations
vh = V[(V.state == 'hard-like') & V.nu_c.notna()]
nu_star = float(np.sqrt(vh[vh.label == 'BH'].nu_c.median() * vh[vh.label == 'NS'].nu_c.median()))
print(f'frozen rule: nu* = sqrt(median BH {vh[vh.label == "BH"].nu_c.median():.3f} x median NS {vh[vh.label == "NS"].nu_c.median():.3f}) = {nu_star:.3f} Hz', flush=True)

# ---------------- new data ----------------
N = pd.read_csv(ROOT/'data/v11/processed/nicer_new_features.csv', dtype={'obsid': str}).reset_index(drop=True)
print(N.groupby(['group', 'label', 'state']).agg(n=('obsid', 'size'), src=('source', 'nunique')).to_string(), flush=True)
z = N[N.source.isin(C.V9_Z_SANITY)]; frac = float((z.state == 'soft-like').mean()) if len(z) else np.nan
ic2 = dict(check='IC2 Cyg X-2 + GX 17+2 soft-like (new observations)', n=len(z), value=frac, passed=bool(frac >= C.V7_SANITY_FRAC))
pd.DataFrame([ic2]).to_csv(R11/'ic2_sanity.csv', index=False); print('IC2:', ic2, flush=True)
if not ic2['passed']: sys.exit(3)

# frozen out-of-source predictions
pred = {k: np.full(len(N), np.nan) for k in MOD}
for src in N.source.unique():
    te = (N.source == src).values; tr = gv != src          # all v10 data if src was never in v10
    for name, (cols, alg) in MOD.items():
        pred[name][te] = fit(cols, alg, tr).score(N.loc[te, cols].values.astype(float))
yn, gn, on = N.label.eq('BH').astype(int).values, N.source.values, N.obsid.values
OOF = {k: L.to_oof(np.arange(len(N)), s, 0.5, yn, gn, on, 'NICER new (frozen)', k).assign(group=N.group.values) for k, s in pred.items()}
N['rule_BH'] = (N.state == 'hard-like') & (N.nu_c < nu_star)
pd.concat([v.assign(name=k) for k, v in OOF.items()]).merge(N[['obsid', 'state', 'nu_c', 'rule_BH']].rename(columns={'obsid': 'obs_id'}), on='obs_id').to_csv(R11/'v11_frozen_predictions.csv', index=False)

# ---------------- v11a ----------------
M9 = N.group.eq('v9 source, new observations').values
Nm = N[M9]; stmap = Nm.set_index('obsid').state
labs = Nm.drop_duplicates('source').set_index('source').label.to_dict(); draws = L7.boot_draws(labs)
hx = Nm[Nm.state == 'hard-like']; nbh, nns = hx[hx.label == 'BH'].source.nunique(), hx[hx.label == 'NS'].source.nunique()
testable = nbh >= C.V9_MIN_SOURCES_PER_CLASS and nns >= C.V9_MIN_SOURCES_PER_CLASS
print(f'new hard-like (v9 sources): {len(hx)} obs, {nbh} BH / {nns} NS sources -> testable {testable}', flush=True)
ROWS = []


def rec(analysis, name, metric, pt, bt, role='descriptive'):
    r = dict(analysis=analysis, comparison=name, metric=metric, **L8.summarize(pt, bt), role=role)
    if ' - ' in name: r['verdict'] = L8.verdict(r)
    ROWS.append(r)


sb = {k: L8.strat_boot(v[M9], stmap, draws) for k, v in OOF.items()}
for k, d in sb.items():
    for st in ('soft-like', 'intermediate', 'hard-like'):
        if st in d: rec(f'new obs | {st}', k, 'obs_AUC', d[st][0][0], d[st][1][:, 0])
for a, b in (('H_N+T_N-LR', 'H_N-LR'), ('H_N+T_N-RF', 'H_N-RF')):
    for st in ('soft-like', 'hard-like'):
        if st in sb[a] and st in sb[b]:
            rec(f'new obs | {st}', f'{a} - {b}', 'obs_AUC', sb[a][st][0][0] - sb[b][st][0][0], sb[a][st][1][:, 0] - sb[b][st][1][:, 0],
                role='PRIMARY' if (a == 'H_N+T_N-LR' and st == 'hard-like' and testable) else 'descriptive')
bsrc = L.paired_bootstrap({k: OOF[k][M9][OOF[k][M9].obs_id.isin(hx.obsid)] for k in ('H_N-LR', 'H_N+T_N-LR')}, 'H_N-LR')
for r in bsrc.to_dict('records'): r['analysis'] = 'new obs hard-like | source level'; r['role'] = 'descriptive'; ROWS.append(r)
# frozen rule
rr = hx.assign(rule=hx.nu_c < nu_star)
sr = rr.groupby(['source', 'label']).rule.mean().reset_index()
sens_o = float(rr[rr.label == 'BH'].rule.mean()); spec_o = float(1 - rr[rr.label == 'NS'].rule.mean())
sens_s = float((sr[sr.label == 'BH'].rule >= 0.5).mean()); spec_s = float((sr[sr.label == 'NS'].rule < 0.5).mean())
rule = pd.DataFrame([dict(nu_star_Hz=nu_star, obs_sensitivity=sens_o, obs_specificity=spec_o, source_sensitivity=sens_s, source_specificity=spec_s,
                          n_BH_obs=int((rr.label == 'BH').sum()), n_NS_obs=int((rr.label == 'NS').sum()), n_BH_src=int((sr.label == 'BH').sum()), n_NS_src=int((sr.label == 'NS').sum()))])
rule.to_csv(R11/'v11_frozen_rule.csv', index=False); sr.to_csv(R11/'v11_frozen_rule_per_source.csv', index=False)
print('\nfrozen rule on new hard-like obs:\n' + rule.round(3).to_string(index=False), flush=True)
inf = []
for s in sorted(hx[hx.label == 'BH'].source.unique()):
    keep = ~OOF['H_N-LR'][M9].source_id.eq(s).values
    a_ = L8.strat_boot(OOF['H_N+T_N-LR'][M9][keep], stmap, [])['hard-like'][0][0]; b_ = L8.strat_boot(OOF['H_N-LR'][M9][keep], stmap, [])['hard-like'][0][0]
    inf.append(dict(left_out=s, gain=a_ - b_))
pd.DataFrame(inf).to_csv(R11/'v11a_influence.csv', index=False); print('\nv11a influence:\n' + pd.DataFrame(inf).round(3).to_string(index=False), flush=True)

# ---------------- v11b ----------------
hb = hx[hx.nu_c.notna()].reset_index(drop=True)
lab_b = hb.drop_duplicates('source').set_index('source').label.eq('BH').astype(int)
rB = []
r_prim = L6.source_residuals(hb[FEAT_H].values, np.log10(hb.nu_c.values), hb.source.values)
a = L6.perm_test(r_prim, lab_b)
rB.append(dict(analysis='new hard-like obs: colour-conditional D(log10 nu_c)', D=a['D'], p=a['p'], n_sources=a['n_sources'], n_bh=a['n_bh'], role='PRIMARY',
               verdict='difference (p < 0.05)' if a['p'] < 0.05 else 'not detected'))
for tag, d in (('new', hb), ('v10 full', vh.reset_index(drop=True))):
    Xc = np.c_[d[FEAT_H].values, np.log10(d.rate_2_10.values)]
    lb_ = d.drop_duplicates('source').set_index('source').label.eq('BH').astype(int)
    a = L6.perm_test(L6.source_residuals(Xc, np.log10(d.nu_c.values), d.source.values), lb_)
    rB.append(dict(analysis=f'{tag}: D(log10 nu_c) controlling colour + log count rate (brightness proxy)', D=a['D'], p=a['p'], n_sources=a['n_sources'], n_bh=a['n_bh'], role='descriptive'))
for s in sorted(hb[hb.label == 'BH'].source.unique()):
    rr_ = r_prim.drop(s); rB.append(dict(analysis=f'influence: without {s}', D=float(rr_[lab_b.reindex(rr_.index) == 1].mean() - rr_[lab_b.reindex(rr_.index) == 0].mean()), role='influence'))

# ---------------- v11c Lorentzian ----------------
fits = []
for r in hb.itertuples():
    lb = [getattr(r, f'lb{i}') for i in range(13)]; se = [getattr(r, f'lb{i}_se') for i in range(13)]
    fits.append(dict(obsid=r.obsid, **L11.fit_lorentz(lb, se)))
FL = hb[['obsid', 'source', 'label', 'c1', 'c2', 'nu_c']].merge(pd.DataFrame(fits), on='obsid'); FL.to_csv(R11/'v11c_lorentz_fits.csv', index=False)
fl = FL[FL.nu_L.notna()].reset_index(drop=True)
a = L6.perm_test(L6.source_residuals(fl[FEAT_H].values, np.log10(fl.nu_L.values), fl.source.values), fl.drop_duplicates('source').set_index('source').label.eq('BH').astype(int))
rB.append(dict(analysis='v11c new hard-like: colour-conditional D(log10 nu_L, lowest Lorentzian width)', D=a['D'], p=a['p'], n_sources=a['n_sources'], n_bh=a['n_bh'], role='descriptive'))
print(f"\nLorentzian fits: {len(fl)} of {len(FL)}; two components chosen in {float((fl.n_lor == 2).mean()):.2f}; median nu_L BH {fl[fl.label == 'BH'].nu_L.median():.3f}, NS {fl[fl.label == 'NS'].nu_L.median():.3f} Hz", flush=True)
B11 = pd.DataFrame(rB); B11.to_csv(R11/'v11b_nuc.csv', index=False); print('\n[v11b / v11c]\n' + B11.round(4).to_string(index=False), flush=True)

# ---------------- v11d never-used sources ----------------
U = N[~M9]
if len(U):
    t = pd.concat([v[~M9].assign(name=k) for k, v in OOF.items()]).merge(U[['obsid', 'state', 'nu_c', 'rule_BH']].rename(columns={'obsid': 'obs_id'}), on='obs_id')
    t = t.pivot_table(index=['source_id', 'true_label', 'obs_id', 'state', 'nu_c', 'rule_BH'], columns='name', values='BH_score').reset_index()
    t.to_csv(R11/'v11d_never_used_sources.csv', index=False); print('\n[v11d never-used sources]\n' + t.round(3).to_string(index=False), flush=True)

out = pd.DataFrame(ROWS); out.to_csv(R11/'v11a_metrics.csv', index=False)
tt = out[out.metric.isin(['obs_AUC', 'source_AUC', 'source_balanced_accuracy'])].copy()
tt['txt'] = tt.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]" + (' *' if r.role == 'PRIMARY' else ''), axis=1)
print('\n' + tt.pivot_table(index=['analysis', 'comparison'], columns='metric', values='txt', aggfunc='first').to_string(), flush=True)

# ---------------- figure ----------------
fig, ax = plt.subplots(1, 3, figsize=(17, 4.8), layout='constrained')
a = ax[0]; names = ['H_N-LR', 'H_N+T_N-LR', 'H_N-RF', 'H_N+T_N-RF']
for i, m in enumerate(names):
    for st, dx, col in (('soft-like', -0.15, '#9aa5b1'), ('hard-like', 0.15, '#2a78d6')):
        r = out[(out.analysis == f'new obs | {st}') & (out.comparison == m)]
        if len(r):
            r = r.iloc[0]; a.errorbar([i + dx], [r.point], yerr=[[r.point - r.ci2_5], [r.ci97_5 - r.point]], fmt='o', color=col, capsize=2, ms=5, label=st if i == 0 else None)
pp = out[out.role == 'PRIMARY']
ttl = f'{pp.iloc[0].point:+.3f} [{pp.iloc[0].ci2_5:+.3f}, {pp.iloc[0].ci97_5:+.3f}]' if len(pp) else 'not testable'
a.set_xticks(range(4)); a.set_xticklabels(names, fontsize=8); a.axhline(.5, color=INK2, lw=.6, ls='--'); a.set_ylim(0.2, 1.03); a.legend(frameon=False, fontsize=7)
a.set_ylabel('observation-level AUC (never-used NICER obs, frozen models)'); a.set_title(f'(a) v11a: hard-like gain = {ttl} (PRIMARY)', loc='left', fontsize=9)
a = ax[1]
for lab_, d in hb.groupby('label'): a.scatter(d.c2, d.nu_c, s=14, alpha=.7, color=CLASS_COLOR[lab_], label=f'{lab_} ({d.source.nunique()} src)')
a.axhline(nu_star, color=INK2, lw=.8, ls='--', label=f'frozen nu* = {nu_star:.2f} Hz'); a.set_yscale('log'); a.legend(frameon=False, fontsize=7)
p1 = B11[B11.role == 'PRIMARY'].iloc[0]
a.set_xlabel('c2 = C(6-10)/C(4-6 keV)'); a.set_ylabel('nu_c (Hz)'); a.set_title(f'(b) v11b: D(log nu_c) = {p1.D:+.3f}, p = {p1.p:.4f} (PRIMARY)', loc='left', fontsize=9)
a = ax[2]
for lab_, d in fl.groupby('label'): a.scatter(d.nu_c, d.nu_L, s=14, alpha=.7, color=CLASS_COLOR[lab_], label=lab_)
a.set_xscale('log'); a.set_yscale('log'); a.plot([1e-2, 1e2], [1e-2, 1e2], color=INK2, lw=.5); a.legend(frameon=False, fontsize=7)
a.set_xlabel('nu_c (nuPnu centroid, Hz)'); a.set_ylabel('nu_L (lowest Lorentzian width, Hz)'); a.set_title('(c) v11c: Lorentzian width vs centroid (descriptive)', loc='left', fontsize=9)
fig.savefig(FG/'v11_prospective.png'); plt.close(fig)
for r in pp.itertuples(): print(f'PRIMARY v11a {r.comparison}: {r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}] -> {r.verdict}')
print(f'PRIMARY v11b D = {p1.D:+.3f}, p = {p1.p:.4f} -> {p1.verdict}')
progress('v11_analysis', (f'v11a {pp.iloc[0].point:+.3f} [{pp.iloc[0].ci2_5:+.3f},{pp.iloc[0].ci97_5:+.3f}]' if len(pp) else 'v11a not testable') + f'; v11b D {p1.D:+.3f} p {p1.p:.4f}')
print(f'total {time.time() - T0:.0f} s')
