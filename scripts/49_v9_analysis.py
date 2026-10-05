"""v9a / v9b (preregistration_v9.md sec. 4-5) on the NICER features (data/v9/processed/nicer_features.csv).
Sanity check (IC3): Cyg X-2 + GX 17+2 >= 2/3 soft-like, else stop (exit 3).
v9a: LOSO over NICER sources on all observations; PRIMARY hard-like observation-level AUC H_N+T_N-LR - H_N-LR (v7a bootstrap).
v9b: colour-conditional source-permutation test of log10 nu_c in the hard-like observations (v6lib, k = 25, 20000 perms)."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v9'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
import config as C
import v4lib as L, v6lib as L6, v7lib as L7, v8lib as L8
from plotstyle import plt, CLASS_COLOR, INK, INK2

T0 = time.time()
RA, RB, FG = ROOT/'results/v9a', ROOT/'results/v9b', ROOT/'figures/v9'
for p in (RA, RB, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
F = pd.read_csv(ROOT/'data/v9/processed/nicer_features.csv', dtype={'obsid': str})
F = F.rename(columns={'obsid': 'obs_id', 'source': 'source_id'}).reset_index(drop=True)
print(F.groupby(['label', 'state']).agg(n=('obs_id', 'size'), src=('source_id', 'nunique')).to_string(), flush=True)

# ---------------- IC3 sanity ----------------
z = F[F.source_id.isin(C.V9_Z_SANITY)]
frac = float((z.state == 'soft-like').mean()) if len(z) else np.nan
san = dict(check='Cyg X-2 + GX 17+2 soft-like fraction', n=len(z), value=frac, threshold=C.V7_SANITY_FRAC, passed=bool(frac >= C.V7_SANITY_FRAC))
pd.DataFrame([san]).to_csv(RA/'v9_sanity_check.csv', index=False); print('IC3:', san, flush=True)
if not san['passed']: progress('v9_analysis', 'IC3 sanity check FAILED -> stop'); print('SANITY CHECK FAILED -> stop'); sys.exit(3)

# ---------------- v9a ----------------
y = F.label.eq('BH').astype(int).values; g = F.source_id.values; o = F.obs_id.values
H = F[['c1', 'c2']].values.astype(float); T = F[['T1', 'T2', 'T3']].values.astype(float); R = np.log10(F.rate_2_10.values)[:, None]
SPEC = {'H_N-LR': (H, 'LogReg'), 'H_N+T_N-LR': (np.c_[H, T], 'LogReg'), 'H_N-RF': (H, 'RandomForest'), 'H_N+T_N-RF': (np.c_[H, T], 'RandomForest'),
        'H_N+R-LR': (np.c_[H, R], 'LogReg'), 'H_N+R+T_N-LR': (np.c_[H, R, T], 'LogReg'),
        'H_N+T1-LR': (np.c_[H, T[:, :1]], 'LogReg'), 'H_N+T2-LR': (np.c_[H, T[:, 1:2]], 'LogReg'), 'H_N+T3-LR': (np.c_[H, T[:, 2:]], 'LogReg')}


def loso(X, alg, mask=None):
    idx = np.arange(len(y)) if mask is None else np.where(mask)[0]
    s = np.full(len(y), np.nan)
    for src in np.unique(g[idx]):
        te = idx[g[idx] == src]; tr = idx[g[idx] != src]
        if len(np.unique(y[tr])) < 2: continue
        s[te] = L.V4Model(alg).fit(X[tr], y[tr]).score(X[te])
    return s[idx], idx


res = Parallel(n_jobs=len(SPEC))(delayed(loso)(X, a) for X, a in SPEC.values())
OOF = {k: L.to_oof(idx, s, 0.5, y, g, o, 'NICER', k) for k, (s, idx) in zip(SPEC, res)}
hard = F.state.eq('hard-like').values
res2 = Parallel(n_jobs=2)(delayed(loso)(X, 'LogReg', hard) for X in (H, np.c_[H, T]))
OOF.update({k: L.to_oof(idx, s, 0.5, y, g, o, 'NICER', k) for k, (s, idx) in zip(('H_N-LR [hard-only]', 'H_N+T_N-LR [hard-only]'), res2)})
pd.concat([v.assign(name=k) for k, v in OOF.items()]).merge(F[['obs_id', 'state', 'rate_2_10']], on='obs_id').to_csv(RA/'v9a_oof_predictions.csv', index=False)

srcs = F.drop_duplicates('source_id').set_index('source_id').label.to_dict()
draws = L7.boot_draws(srcs)
stmap = F.set_index('obs_id').state
hx = F[hard]; nbh, nns = hx[hx.label == 'BH'].source_id.nunique(), hx[hx.label == 'NS'].source_id.nunique()
testable = nbh >= C.V9_MIN_SOURCES_PER_CLASS and nns >= C.V9_MIN_SOURCES_PER_CLASS
print(f'hard-like: {len(hx)} obs, {nbh} BH / {nns} NS sources -> testable {testable}', flush=True)
ROWS = []


def rec(analysis, name, metric, pt, bt, role='descriptive'):
    r = dict(analysis=analysis, comparison=name, metric=metric, **L8.summarize(pt, bt), role=role)
    if ' - ' in name: r['verdict'] = L8.verdict(r)
    ROWS.append(r)


def strat(analysis, oofs, groups, dr, pairs, strata, primary=None):
    sb = {k: L8.strat_boot(v, groups, dr) for k, v in oofs.items()}
    for k, d in sb.items():
        for st in strata:
            if st in d: rec(f'{analysis} | {st}', k, 'obs_AUC', d[st][0][0], d[st][1][:, 0])
    for a, b in pairs:
        for st in strata:
            if st in sb[a] and st in sb[b]:
                rec(f'{analysis} | {st}', f'{a} - {b}', 'obs_AUC', sb[a][st][0][0] - sb[b][st][0][0], sb[a][st][1][:, 0] - sb[b][st][1][:, 0],
                    role='PRIMARY' if primary == (a, b, st) and testable else 'descriptive')
    return sb


ST = ['soft-like', 'intermediate', 'hard-like']
sb = strat('NICER all-state LOSO', {k: OOF[k] for k in SPEC}, stmap, draws,
           [('H_N+T_N-LR', 'H_N-LR'), ('H_N+T_N-RF', 'H_N-RF'), ('H_N+R+T_N-LR', 'H_N+R-LR'), ('H_N+T1-LR', 'H_N-LR'), ('H_N+T2-LR', 'H_N-LR'),
            ('H_N+T3-LR', 'H_N-LR')], ST, primary=('H_N+T_N-LR', 'H_N-LR', 'hard-like'))
for a, b in (('H_N+T_N-LR', 'H_N-LR'), ('H_N+T_N-RF', 'H_N-RF')):
    if all(s in sb[m] for s in ('soft-like', 'hard-like') for m in (a, b)):
        ga = sb[a]['soft-like'][1][:, 0] - sb[a]['hard-like'][1][:, 0]; gb = sb[b]['soft-like'][1][:, 0] - sb[b]['hard-like'][1][:, 0]
        pa = sb[a]['soft-like'][0][0] - sb[a]['hard-like'][0][0]; pb = sb[b]['soft-like'][0][0] - sb[b]['hard-like'][0][0]
        rec('NICER | soft-like - hard-like gap', f'{b} gap', 'obs_AUC', pb, gb); rec('NICER | soft-like - hard-like gap', f'{a} gap', 'obs_AUC', pa, ga)
        rec('NICER | difference in differences', f'{a} gap - {b} gap', 'obs_AUC', pa - pb, ga - gb)
strat('NICER trained on hard-like only', {k: OOF[k] for k in ('H_N-LR [hard-only]', 'H_N+T_N-LR [hard-only]')}, stmap, draws,
      [('H_N+T_N-LR [hard-only]', 'H_N-LR [hard-only]')], ['hard-like'])
# new-BH sensitivity: hard-like observations of the never-used BHs + all NS
NEW = ['MAXI J1820+070', 'Swift J1727.8-1613']
keep = F[(F.label == 'NS') | F.source_id.isin(NEW)]
dr_new = L7.boot_draws(keep.drop_duplicates('source_id').set_index('source_id').label.to_dict())
strat('NICER new BHs only (MAXI J1820+070, Swift J1727.8-1613) + NS', {k: OOF[k][OOF[k].obs_id.isin(keep.obs_id)] for k in ('H_N-LR', 'H_N+T_N-LR')},
      stmap, dr_new, [('H_N+T_N-LR', 'H_N-LR')], ['hard-like'])
bright = F[F.rate_2_10 >= 100]
strat('NICER rate >= 100 c/s', {k: OOF[k][OOF[k].obs_id.isin(bright.obs_id)] for k in ('H_N-LR', 'H_N+T_N-LR')}, stmap, draws,
      [('H_N+T_N-LR', 'H_N-LR')], ['hard-like'])
b = L.paired_bootstrap({k: OOF[k][OOF[k].obs_id.isin(hx.obs_id)] for k in ('H_N-LR', 'H_N+T_N-LR')}, 'H_N-LR')
for r in b.to_dict('records'):
    r['analysis'] = 'NICER hard-like | source level (restricted OOF)'; r['role'] = 'descriptive'; ROWS.append(r)
per = pd.concat([v.assign(name=k) for k, v in OOF.items() if k in ('H_N-LR', 'H_N+T_N-LR')]).merge(F[['obs_id', 'state']], on='obs_id')
per = per.groupby(['true_label', 'source_id', 'state', 'name']).BH_score.agg(['mean', 'size']).unstack('name')
per.to_csv(RA/'v9a_per_source_state.csv'); print('\nper source x state (mean score):\n' + per.round(2).to_string(), flush=True)
out = pd.DataFrame(ROWS); out.to_csv(RA/'v9a_metrics.csv', index=False)
t = out[out.metric.isin(['obs_AUC', 'source_AUC', 'source_balanced_accuracy'])].copy()
t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]" + (' *' if r.role == 'PRIMARY' else ''), axis=1)
print('\n' + t.pivot_table(index=['analysis', 'comparison'], columns='metric', values='txt', aggfunc='first').to_string(), flush=True)

# ---------------- v9b ----------------
hb = F[hard].copy(); lab = hb.drop_duplicates('source_id').set_index('source_id').label.eq('BH').astype(int)
Hh = hb[['c1', 'c2']].values.astype(float); gh = hb.source_id.values
feats = {'log10 nu_c': np.log10(hb.nu_c.values), 'T1': hb.T1.values, 'T2': hb.T2.values, 'T3': hb.T3.values, 'rms 0.1-10 Hz': hb.STATE.values}
pr = []
for k, v in feats.items():
    rr = L6.source_residuals(Hh, v.astype(float), gh)
    a = L6.perm_test(rr, lab)
    pr.append(dict(feature=k, D=a['D'], p=a['p'], n_sources=a['n_sources'], n_bh=a['n_bh'], null_sd=a['null_sd'],
                   n_obs=int(np.isfinite(v).sum()), role='PRIMARY' if k == 'log10 nu_c' else 'descriptive'))
pr = pd.DataFrame(pr); pr['p_holm'] = L6.holm(pr.p); pr['verdict'] = np.where(pr.p < 0.05, 'difference (p < 0.05)', 'not detected')
pr.to_csv(RB/'v9b_permutation_test.csv', index=False); print('\n[v9b]\n' + pr.round(4).to_string(index=False), flush=True)

# ---------------- figure ----------------
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6), layout='constrained')
a = ax[0]
for lab_, d in hb.groupby('label'):
    a.scatter(d.c2, d.T1, s=14, color=CLASS_COLOR[lab_], alpha=.7, label=f'{lab_} ({d.source_id.nunique()} src)')
a.set_xlabel('NICER colour c2 = C(6-10 keV)/C(4-6 keV)'); a.set_ylabel('T1: rms 0.016-0.094 Hz'); a.legend(frameon=False, fontsize=7)
a.set_title('(a) NICER hard-like observations', loc='left', fontsize=9)
a = ax[1]
for lab_, d in hb.groupby('label'):
    a.scatter(d.c2, d.nu_c, s=14, color=CLASS_COLOR[lab_], alpha=.7, label=lab_)
a.set_yscale('log'); a.set_xlabel('c2'); a.set_ylabel('nu_c (Hz; nuPnu centroid 1/128-64 Hz)')
p1 = pr[pr.role == 'PRIMARY'].iloc[0]
a.set_title(f'(b) v9b: colour-conditional D(log nu_c) = {p1.D:+.2f}, p = {p1.p:.3f}', loc='left', fontsize=9)
a = ax[2]
names = ['H_N-LR', 'H_N+T_N-LR', 'H_N-RF', 'H_N+T_N-RF', 'H_N+R-LR', 'H_N+R+T_N-LR']
for i, m in enumerate(names):
    for stt, dx, col in (('soft-like', -0.15, '#9aa5b1'), ('hard-like', 0.15, '#2a78d6')):
        r = out[(out.analysis == f'NICER all-state LOSO | {stt}') & (out.comparison == m)]
        if len(r):
            r = r.iloc[0]; a.errorbar([i + dx], [r.point], yerr=[[r.point - r.ci2_5], [r.ci97_5 - r.point]], fmt='o', color=col, capsize=2, ms=4,
                                      label=stt if i == 0 else None)
pp = out[out.role == 'PRIMARY']
ttl = f'{pp.iloc[0].point:+.3f} [{pp.iloc[0].ci2_5:+.3f}, {pp.iloc[0].ci97_5:+.3f}]' if len(pp) else 'not testable'
a.set_xticks(range(len(names))); a.set_xticklabels(names, rotation=30, fontsize=7); a.axhline(.5, color=INK2, lw=.6, ls='--'); a.set_ylim(0.2, 1.03)
a.set_ylabel('observation-level AUC (NICER LOSO)'); a.legend(frameon=False, fontsize=7)
a.set_title(f'(c) v9a: hard-like H_N+T_N-LR - H_N-LR = {ttl}', loc='left', fontsize=9)
fig.savefig(FG/'v9_nicer.png'); plt.close(fig)
for r in pp.itertuples(): print(f'PRIMARY v9a {r.analysis} {r.comparison}: {r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}] -> {r.verdict}')
print(f"PRIMARY v9b log10 nu_c: D = {p1.D:+.3f}, p = {p1.p:.4f} -> {p1.verdict}")
progress('v9_analysis', (f'v9a {pp.iloc[0].point:+.3f} [{pp.iloc[0].ci2_5:+.3f},{pp.iloc[0].ci97_5:+.3f}]' if len(pp) else 'v9a not testable')
         + f'; v9b D {p1.D:+.3f} p {p1.p:.4f}')
print(f'total {time.time() - T0:.0f} s')
