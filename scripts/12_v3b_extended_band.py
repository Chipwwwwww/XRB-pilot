"""v3b (preregistration_v3.md §2): does adding 3-5 keV carry information beyond hardness?
Runs on the user's machine: needs the v2 raw StdProd files already under data/raw/spectra/ (no new downloads).
Same 456 accepted v2 observations, same deadtime factors (observations.csv 'dcor'), same processing (spectra.py),
only the common energy grid is extended down to ~3 keV.  Outputs: data/v3/processed/features_3_25.npz,
results/v3/v3b_*.csv, figures/v3/v3b_*.png."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, progress
from spectra import read_pha, read_rsp, overlap_matrix, net_spectrum
from v3lib import *
from plotstyle import plt, INK2, CLASS_COLOR

E_LO_EXT, E_HI = 3.0, 25.0
REFERENCE_OBS = '91702-01-66-05'
D3, R3, FG3 = ROOT/'data/v3/processed', ROOT/'results/v3', ROOT/'figures/v3'
for p in (D3, R3, FG3): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 220)

obs = pd.read_csv(ROOT/'data/v2/observations.csv', dtype={'obs_id': str})
obs = obs[obs.in_dataset.astype(str).str.lower().eq('true')].reset_index(drop=True)
z2 = np.load(ROOT/'data/v2/processed/features.npz')
assert list(obs.obs_id) == list(z2['obs_id']), 'observations.csv order differs from v2 features.npz'
fix = lambda p: ROOT / str(p).replace('\\', '/')                  # Windows-written relative paths

# ---- extended common grid from the same reference observation ----
ref = read_rsp(ROOT/f'data/raw/spectra/{REFERENCE_OBS}/xp{REFERENCE_OBS.replace("-", "")}.rsp.gz')
bounds = np.unique(np.r_[ref['ch_lo'], ref['ch_hi']])
lo = bounds[np.argmin(abs(bounds - E_LO_EXT))]; hi = bounds[np.argmin(abs(bounds - E_HI))]
EDGES = bounds[(bounds >= lo) & (bounds <= hi)]; WID = np.diff(EDGES)
assert np.isclose(EDGES[-1], z2['edges'][-1]), 'upper grid edge must match v2'
n_new = int(np.sum(EDGES[:-1] < z2['edges'][0] - 1e-6))
assert np.allclose(EDGES[n_new:], z2['edges']), 'v2 grid must be a sub-grid of the extended grid'
print(f'Extended grid: {len(WID)} bins, {EDGES[0]:.3f}-{EDGES[-1]:.3f} keV ({n_new} new bins below {z2["edges"][0]:.2f} keV)')

rows, rates, errs = [], [], []
for r in obs.itertuples():
    rec = dict(obs_id=r.obs_id, source_id=r.source_id)
    try:
        s, b, rsp = read_pha(fix(r.path_src)), read_pha(fix(r.path_bkg)), read_rsp(fix(r.path_rsp))
        net, err, *_ = net_spectrum(s, b, float(r.dcor))
        W = overlap_matrix(rsp['ch_lo'], rsp['ch_hi'], EDGES)
        rate = (W @ net) / s['npcu'] / WID; rerr = np.sqrt((W**2) @ err**2) / s['npcu'] / WID
        reasons = []
        if rsp['ch_lo'][0] > EDGES[0] or rsp['ch_hi'][-1] < EDGES[-1]: reasons.append('ebounds_coverage')
        if not (np.isfinite(rate).all() and np.isfinite(rerr).all()): reasons.append('nonfinite')
        # consistency: the 5-25 keV part must reproduce the v2 feature vector
        k = list(z2['obs_id']).index(r.obs_id)
        dv2 = float(np.max(np.abs(rate[n_new:] - z2['rate'][k]) / np.maximum(np.abs(z2['rate'][k]), 1e-6)))
        rec.update(max_rel_diff_vs_v2=dv2, F_3_5=float(np.sum((rate*WID)[EDGES[1:] <= z2['edges'][0] + 1e-6])),
                   n_nonpositive_3_5=int(np.sum(rate[:n_new] <= 0)), status='excluded' if reasons else 'accepted',
                   reason=';'.join(reasons))
        if dv2 > 1e-6: rec.update(status='excluded', reason=(rec['reason'] + ';v2_mismatch').strip(';'))
    except Exception as e:
        rec.update(status='excluded', reason=f'read_error: {type(e).__name__}: {e}'[:200])
        rate = rerr = np.full(len(WID), np.nan)
    rows.append(rec); rates.append(rate); errs.append(rerr)
chk = pd.DataFrame(rows); chk.to_csv(R3/'v3b_extraction_checks.csv', index=False)
print(chk.status.value_counts().to_string()); print(chk[chk.status != 'accepted'].reason.value_counts().to_string())
keep = chk.status.eq('accepted').values
rate, err = np.array(rates)[keep], np.array(errs)[keep]
y, g, oid = z2['y'][keep], z2['source_id'][keep], z2['obs_id'][keep]
np.savez_compressed(D3/'features_3_25.npz', rate=rate, err=err, edges=EDGES, obs_id=oid, source_id=g, y=y)
print(f'{keep.sum()} of {len(keep)} observations kept; non-positive 3-5 keV bins in {int((chk.n_nonpositive_3_5 > 0).sum())} spectra (kept, values unchanged)')

# ---- representations (pre-registered) ----
F325 = np.sum(rate * WID, 1); assert (F325 > 0).all()
f35, f57, f710 = band(rate, EDGES, E_LO_EXT - 0.2, 5), band(rate, EDGES, 5, 7), band(rate, EDGES, 7, 10)
f1016, f1625 = band(rate, EDGES, 10, 16), band(rate, EDGES, 16, 25.1)
assert (np.r_[f57, f1016] > 0).all()
H3 = np.c_[f35 / f57, f710 / f57, f1625 / f1016]
v2reps = v2_representations(z2['rate'][keep], z2['edges'], z2['F'][keep])
reps = {'B_shape': v2reps['B_shape'], 'H_colours': v2reps['H_colours'],
        'B3_shape_3_25': rate / F325[:, None], 'H3_colours_3_25': H3,
        'H3_plus_B3': np.c_[H3, rate / F325[:, None]]}
for k, X in reps.items(): print(f'  {k:<18s} {X.shape[1]} features')

OOF_FILE = R3/'v3b_oof_predictions.csv'
if OOF_FILE.exists() and '--retrain' not in sys.argv:
    oof = pd.read_csv(OOF_FILE, dtype={'obs_id': str}); print('re-using', OOF_FILE.name)
else:
    oof, _ = run_loso(reps, y, g, oid); oof.to_csv(OOF_FILE, index=False)
pm, ps = point_metrics(oof)
pm.to_csv(R3/'v3b_metrics.csv', index=False); ps.to_csv(R3/'v3b_per_source.csv', index=False)
print('\n' + pm.drop(columns='misclassified_sources').round(3).to_string(index=False))
bs = bootstrap(oof, [('B3_shape_3_25', 'B_shape'), ('H3_colours_3_25', 'H_colours'), ('H3_plus_B3', 'H3_colours_3_25')])
bs.to_csv(R3/'v3b_bootstrap.csv', index=False)
print('\n' + bs[bs.comparison.str.contains(' - ')].round(3).to_string(index=False))

# ---- figure: soft colour distribution per source (diagnostic for the N_H caveat) ----
src = pd.DataFrame(dict(source_id=g, y=y, soft=H3[:, 0])).groupby('source_id').agg(y=('y', 'first'), med=('soft', 'median'),
      lo=('soft', lambda v: np.percentile(v, 16)), hi=('soft', lambda v: np.percentile(v, 84))).sort_values('med')
fig, a = plt.subplots(figsize=(7, 0.22 * len(src) + 1.2))
for i, (sid, r) in enumerate(src.iterrows()):
    c = CLASS_COLOR['BH' if r.y else 'NS']
    a.plot([r.lo, r.hi], [i, i], color=c, lw=2); a.plot(r.med, i, 'o', color=c, ms=4)
a.set_yticks(range(len(src))); a.set_yticklabels(src.index, fontsize=7)
a.set_xlabel('soft colour F(3–5 keV) / F(5–7 keV)  [instrument count space; median and 16–84%]')
a.set_title('v3b: soft colour by source (blue = BH, orange = NS). Differences may reflect N_H, not BH/NS physics', loc='left', fontsize=8.5)
fig.savefig(FG3/'v3b_soft_colour_by_source.png'); plt.close(fig)
progress('v3b_extended_band', f'{keep.sum()} observations on {len(WID)}-bin 3-25 keV grid; results/v3/v3b_* written')
