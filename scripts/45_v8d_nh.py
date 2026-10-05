"""v8d (preregistration_v8.md sec. 6): MAXI/GSC 2-4 keV increment after an N_H correction.
1. HI4PI N_H (HEASoft nh, avwnh, 0.1 deg) at the v7c2 source positions; tbabs(wilm, vern) x powerlaw(Gamma=2) photon-flux
   transmission per MAXI band on a log N_H grid (XSPEC) -- both run in WSL by scripts/v8d_heasoft.sh. IC5 checks.
2. Corrected band fluxes L' = L/t_L(N_H), M' = M/t_M, H' = H/t_H -> SC', HC', C4', RelInt'.
3. Main task BH vs NPNS, the v7c2 LOSO pipeline unchanged (cap 200 points per training source, seed 42; KNN k by inner LOSO):
   LR / RF / KNN on C2D, C1D (IC6: must equal the v7c2 OOF), C2D_NH, C1D_NH, CCI_NH, C2D+logNH, C1D+logNH.
   PRIMARY: RF[C2D_NH] - RF[C1D_NH], source AUC (class-stratified source bootstrap, 2000 draws, seed 42).
Outputs: data/v8d/{positions,nh_hi4pi,tbabs_transmission}.csv, results/v8d/*, figures/v8d/*."""
import os, sys, time, subprocess
os.environ['XRB_VERSION'] = 'v8d'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
import config as C
import v4lib as L, v7lib as L7, v8lib as L8
from plotstyle import plt, CLASS_COLOR, INK2

T0 = time.time()
D8, R8, FG = ROOT/'data/v8d', ROOT/'results/v8d', ROOT/'figures/v8d'
for p in (D8, R8, FG, R8/'cache'): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)


def wsl(p):
    p = str(p.resolve()).replace('\\', '/'); return '/mnt/' + p[0].lower() + p[2:]


# ---------------- 1. N_H and transmission (HEASoft in WSL) ----------------
pts = pd.read_csv(ROOT/'data/v7c/maxi_points.csv')
mt = pd.read_csv(ROOT/'data/v7c/c2_sources_matched.csv').drop_duplicates('maxi_id').set_index('maxi_id')
srcs = pts.drop_duplicates('source')[['source', 'name', 'cls']]
posf = D8/'positions.csv'
srcs.assign(ra=srcs.source.map(mt.ra), dec=srcs.source.map(mt.dec))[['source', 'ra', 'dec']].rename(columns={'source': 'name'}).to_csv(posf, index=False)
lo, hi, n = C.V8_NH_GRID
grid = np.r_[0.0, np.logspace(lo, hi, int(n)) / 1e22]
gridf = D8/'nh_grid_1e22.txt'; gridf.write_text('\n'.join(f'{g:.8g}' for g in grid) + '\n')
nhf, trf = D8/'nh_hi4pi.csv', D8/'tbabs_transmission.csv'
if not (nhf.exists() and trf.exists()):
    r = subprocess.run(['wsl', '-d', 'Ubuntu-22.04', '-u', 'root', '--', 'bash', wsl(ROOT/'scripts/v8d_heasoft.sh'), wsl(posf), wsl(nhf),
                        wsl(gridf), wsl(trf), str(C.V8_NH_GAMMA)], capture_output=True, text=True)
    print(r.stdout[-500:], r.stderr[-500:])
NH = pd.read_csv(nhf).set_index('name'); TR = pd.read_csv(trf)
assert set(NH.index) == set(srcs.source), 'N_H missing for some sources'
t0 = TR.iloc[0]; T = TR.copy()
for b in 'LMH': T[b] = TR[b] / t0[b]
ic5 = dict(t_at_0_equals_1=bool(np.allclose(T.iloc[0][list('LMH')], 1.0)),
           monotone=bool(all((np.diff(T[b].values) <= 1e-12).all() for b in 'LMH')),
           band_order=bool(((T.L <= T.M + 1e-12) & (T.M <= T.H + 1e-12)).all()))
print('IC5 tbabs transmission:', ic5, '| t(1e22):', T.iloc[np.argmin(abs(T.nh_1e22 - 1))][list('LMH')].round(4).to_dict(), flush=True)
lg = np.log10(np.clip(T.nh_1e22.values[1:], 1e-12, None))


def trans(band, nh_1e22):
    return np.interp(np.log10(nh_1e22), lg, T[band].values[1:])


srcs['nh_1e22'] = srcs.source.map(NH.avwnh) / 1e22
srcs['logNH'] = np.log10(srcs.nh_1e22 * 1e22)
for b in 'LMH': srcs[f't_{b}'] = trans(b, srcs.nh_1e22.values)
srcs.to_csv(R8/'v8d_source_nh.csv', index=False)
print(srcs.groupby('cls').nh_1e22.describe().round(3).to_string(), flush=True)

# ---------------- 2. features ----------------
pts['SC'] = (pts.M - pts.L) / (pts.M + pts.L); pts['HC'] = (pts.H - pts.L) / (pts.H + pts.L); pts['C4'] = (pts.H - pts.M) / (pts.H + pts.M)
tot = pts.L + pts.M + pts.H
pts['RelInt'] = tot / pts.assign(t=tot).groupby('source').t.transform(lambda s: np.percentile(s, 99.99))
pts['obs_id'] = pts.source + '_' + pts.mjd.round(1).astype(str)
tt = srcs.set_index('source')
Lc, Mc, Hc = pts.L / pts.source.map(tt.t_L), pts.M / pts.source.map(tt.t_M), pts.H / pts.source.map(tt.t_H)
pts['SCn'] = (Mc - Lc) / (Mc + Lc); pts['HCn'] = (Hc - Lc) / (Hc + Lc); pts['C4n'] = (Hc - Mc) / (Hc + Mc)
totc = Lc + Mc + Hc
pts['RelIntn'] = totc / pts.assign(t=totc).groupby('source').t.transform(lambda s: np.percentile(s, 99.99))
pts['logNH'] = pts.source.map(tt.logNH)
FS = {'C2D': ['SC', 'HC'], 'C1D': ['C4'], 'C2D_NH': ['SCn', 'HCn'], 'C1D_NH': ['C4n'], 'CCI_NH': ['SCn', 'HCn', 'RelIntn'],
      'C2D+logNH': ['SC', 'HC', 'logNH'], 'C1D+logNH': ['C4', 'logNH']}
GRID = {'KNN': [dict(k=k) for k in C.V7_C2_KNN_GRID]}

# ---------------- 3. models (main task, v7c2 pipeline) ----------------
data = pts[pts.cls.isin(['BH', 'NPNS'])].copy(); data['y'] = (data.cls == 'BH').astype(int)
ids = sorted(data.source.unique())
print(f'\nmain task: {len(ids)} sources ({data[data.y == 1].source.nunique()} BH), {len(data)} points', flush=True)


def oof_frame(res, name):
    rows = []
    for src, alg, cfg, s, _ in res:
        te = data[data.source == src]
        rows.append(pd.DataFrame(dict(source_id=src, obs_id=te.obs_id.values, true_label=np.where(te.y.values == 1, 'BH', 'NS'),
                                      BH_score=s, predicted_label=np.where(s >= 0.5, 'BH', 'NS'), model=name, cfg=cfg)))
    return pd.concat(rows, ignore_index=True)


oofs = {}
for alg in ('RF', 'LR', 'KNN'):
    for fs, cols in FS.items():
        res = Parallel(n_jobs=16)(delayed(L7.c2_outer_cached)(str(R8/'cache'/f'main_{alg}_{fs}_{s}.pkl'), s, data, alg, cols, GRID,
                                                               C.V7_MAXI_TRAIN_CAP, C.SEED) for s in ids)
        oofs[f'{alg} [{fs}]'] = oof_frame(res, f'{alg} [{fs}]')
        print(f'  {alg} [{fs}] done ({time.time() - T0:.0f} s)', flush=True)
pd.concat(oofs.values()).to_csv(R8/'v8d_oof_predictions.csv.gz', index=False)

# IC6: uncorrected models reproduce v7c2
v7 = pd.read_csv(ROOT/'results/v7c/v7c2_oof_predictions.csv.gz')
v7 = v7[v7.task.str.startswith('main')]
ic6 = []
for nm in ('RF [C2D]', 'RF [C1D]', 'LR [C2D]', 'LR [C1D]', 'KNN [C2D]', 'KNN [C1D]'):
    a = oofs[nm].set_index('obs_id').BH_score; b = v7[v7.model == nm].set_index('obs_id').BH_score
    ic6.append(dict(model=nm, n=len(a), n_v7=len(b), max_abs_diff=float((a - b.reindex(a.index)).abs().max())))
ic6 = pd.DataFrame(ic6); ic6['passed'] = ic6.max_abs_diff < 1e-9
ic6.to_csv(R8/'ic6_reproduce_v7c2.csv', index=False); print('\nIC6:\n' + ic6.to_string(index=False), flush=True)
if not ic6[ic6.model.str.startswith('RF')].passed.all():
    progress('v8d_nh', 'IC6 FAILED -> stop'); print('IC6 FAILED -> v8d stops'); sys.exit(3)

# ---------------- 4. bootstrap ----------------
B = L8.src_boot(oofs, 'RF [C2D]')
# log N_H alone as a source score (AUC only; rescaled to 0-1 so that src_table works)
ln = data.drop_duplicates('source').set_index('source').logNH
sc = (ln - ln.min()) / (ln.max() - ln.min())
nh_oof = pd.DataFrame(dict(source_id=data.source.values, obs_id=data.obs_id.values, true_label=np.where(data.y == 1, 'BH', 'NS'),
                           BH_score=data.source.map(sc).values)).assign(predicted_label=lambda d: np.where(d.BH_score >= 0.5, 'BH', 'NS'))
B.update(L8.src_boot({'RF [C2D]': oofs['RF [C2D]'], 'log N_H alone': nh_oof}, 'RF [C2D]'))
M = L.METRICS
rows = []


def add(name, pt, bt, role='descriptive'):
    for j, m in enumerate(M):
        r = dict(comparison=name, metric=m, **L8.summarize(pt[j], bt[:, j]), role=role)
        if ' - ' in name: r['verdict'] = L8.verdict(r); r['frac_first_better'] = float(np.mean(bt[:, j] > 0))
        rows.append(r)


for k, (p, b) in B.items(): add(k, p, b)
pairs = [('C2D_NH', 'C1D_NH'), ('C2D', 'C1D'), ('CCI_NH', 'C2D_NH'), ('C2D+logNH', 'C1D+logNH'), ('C1D+logNH', 'C1D'), ('C2D_NH', 'C2D')]
for alg in ('RF', 'LR', 'KNN'):
    for a, b in pairs:
        A, Bb = B[f'{alg} [{a}]'], B[f'{alg} [{b}]']
        add(f'{alg} [{a}] - {alg} [{b}]', A[0] - Bb[0], A[1] - Bb[1], role='PRIMARY' if (alg == 'RF' and (a, b) == ('C2D_NH', 'C1D_NH')) else 'descriptive')
    # difference in differences: (C2D_NH - C1D_NH) - (C2D - C1D)
    d1 = [B[f'{alg} [C2D_NH]'][i] - B[f'{alg} [C1D_NH]'][i] for i in (0, 1)]; d0 = [B[f'{alg} [C2D]'][i] - B[f'{alg} [C1D]'][i] for i in (0, 1)]
    add(f'{alg} DiD: (C2D_NH - C1D_NH) - (C2D - C1D)', d1[0] - d0[0], d1[1] - d0[1])
res = pd.DataFrame(rows); res.to_csv(R8/'v8d_bootstrap.csv', index=False)
t = res[res.metric != 'obs_balanced_accuracy'].copy(); t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
print('\n' + t.pivot_table(index='comparison', columns='metric', values='txt', aggfunc='first').to_string())
prim = res[(res.role == 'PRIMARY') & (res.metric == 'source_AUC')].iloc[0]
print(f'\nPRIMARY RF[C2D_NH] - RF[C1D_NH] source AUC: {prim.point:+.3f} [{prim.ci2_5:+.3f},{prim.ci97_5:+.3f}] -> {prim.verdict}')
ps = pd.concat([L.src_table(v).assign(model=k) for k, v in oofs.items()]).reset_index()
ps = ps.merge(srcs.rename(columns={'source': 'source_id'}), on='source_id', how='left'); ps.to_csv(R8/'v8d_per_source.csv', index=False)

# ---------------- 5. figures ----------------
fig, ax = plt.subplots(1, 3, figsize=(14, 4.2), layout='constrained')
a = ax[0]; d = srcs[srcs.cls.isin(['BH', 'NPNS'])]
for c, lab in (('NPNS', 'NS'), ('BH', 'BH')):
    v = d[d.cls == c].logNH.sort_values(); a.plot(v.values, np.linspace(0, 1, len(v)), drawstyle='steps-post', color=CLASS_COLOR[lab], label=f'{c} ({len(v)})')
pr = res[(res.comparison == 'log N_H alone') & (res.metric == 'source_AUC')].iloc[0]
a.set_xlabel('log10 N_H (HI4PI, cm$^{-2}$)'); a.set_ylabel('cumulative fraction of sources'); a.legend(frameon=False, fontsize=7)
a.set_title(f'(a) HI4PI N_H by class; AUC(log N_H) = {pr.point:.2f} [{pr.ci2_5:.2f}, {pr.ci97_5:.2f}]', loc='left', fontsize=8)
a = ax[1]
for c, lab in (('NPNS', 'NS'), ('BH', 'BH')):
    g = data[data.cls == c].groupby('source')[['SC', 'SCn']].median()
    a.scatter(g.SC, g.SCn, s=14, color=CLASS_COLOR[lab], label=c)
a.plot([-1, 1], [-1, 1], color=INK2, lw=.5); a.set_xlabel('median SC (observed)'); a.set_ylabel("median SC' (N_H-corrected)")
a.set_title('(b) soft colour SC = (M-L)/(M+L) per source, before / after correction', loc='left', fontsize=8); a.legend(frameon=False, fontsize=7)
a = ax[2]
names = [f'{alg} [{fs}]' for alg in ('LR', 'RF', 'KNN') for fs in ('C1D', 'C2D', 'C1D_NH', 'C2D_NH', 'CCI_NH', 'C1D+logNH', 'C2D+logNH')]
r2 = res[(res.metric == 'source_AUC')].set_index('comparison').reindex(names)
y = np.arange(len(names))
a.errorbar(r2.point, y, xerr=[r2.point - r2.ci2_5, r2.ci97_5 - r2.point], fmt='o', ms=3, capsize=2, color='#2a78d6')
a.set_yticks(y); a.set_yticklabels(names, fontsize=6); a.invert_yaxis(); a.axvline(.5, color=INK2, lw=.6, ls='--')
a.set_xlabel('source-level AUC, MAXI BH vs NPNS (LOSO)')
a.set_title(f'(c) PRIMARY RF[C2D_NH] - RF[C1D_NH] = {prim.point:+.3f} [{prim.ci2_5:+.3f}, {prim.ci97_5:+.3f}]', loc='left', fontsize=8)
fig.savefig(FG/'v8d_nh_control.png'); plt.close(fig)
progress('v8d_nh', f"PRIMARY RF[C2D_NH]-RF[C1D_NH] source AUC {prim.point:+.3f} [{prim.ci2_5:+.3f},{prim.ci97_5:+.3f}]")
print(f'total {time.time() - T0:.0f} s')
