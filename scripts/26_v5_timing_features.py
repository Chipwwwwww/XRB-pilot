"""v5 step 1 (preregistration_v5.md §3-4): Standard-1 timing features for every observation of S1 (v2), S2 (v2 + v4b2)
and S3 (v4b1), then the implementation checks (4b auto-power cross-check, 4c within-BH rms-hardness sanity).
No new downloads. Outputs data/v5/processed/timing_features.csv, results/v5/v5_implementation_checks.csv.
Usage: python 26_v5_timing_features.py [--limit N]   (N observations per sample, smoke test; writes to *_smoke.csv)"""
import os, sys, time
os.environ['XRB_VERSION'] = 'v5'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
import config as C
import v4lib as L
import v5lib as L5

D5, R5 = ROOT/'data/v5/processed', ROOT/'results/v5'
for p in (D5, R5): p.mkdir(parents=True, exist_ok=True)
LIMIT = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
SUF = '_smoke' if LIMIT else ''
T0 = time.time()


def obs_table(v):
    o = pd.read_csv(ROOT/f'data/{v}/observations.csv', dtype={'obs_id': str}, low_memory=False)
    o = o[o.in_dataset.astype(str).str.lower().eq('true')]
    return o[['obs_id', 'source_id', 'label', 'path_src', 'path_bkg']].head(LIMIT) if LIMIT else o[['obs_id', 'source_id', 'label', 'path_src', 'path_bkg']]


tabs = {v: obs_table(v) for v in ('v2', 'v4b2', 'v4b1')}
allo = pd.concat([t.assign(sample=v) for v, t in tabs.items()]).drop_duplicates('obs_id').reset_index(drop=True)
print(len(allo), 'unique observations', {v: len(t) for v, t in tabs.items()}, flush=True)
recs = Parallel(n_jobs=16, verbose=2, batch_size=8)(delayed(L5.obs_timing)(r.obs_id, r.path_src, r.path_bkg) for r in allo.itertuples())
tf = allo[['obs_id', 'source_id', 'label']].merge(pd.DataFrame(recs), on='obs_id')
for v, t in tabs.items(): tf[f'in_{v}'] = tf.obs_id.isin(t.obs_id)
tf.to_csv(D5/f'timing_features{SUF}.csv', index=False)
print(f'features done ({time.time()-T0:.0f} s)')
print(tf.status.str.slice(0, 40).value_counts().to_string())
print(tf.groupby('label')[['T1', 'T2', 'T3', 'T_total']].describe().T.round(3).to_string())

# ---- 4b: cospectrum vs auto-power T2 on S1 (>= 2 PCUs, 20-500 source counts/s/PCU) ----
s1 = tf[tf.in_v2 & tf.status.eq('ok')].copy()
lo, hi = C.V5_CHECK_RATE
m = s1.src_rate_per_pcu.between(lo, hi)
rho_b = spearmanr(s1[m].T2, s1[m].T2_auto)[0] if m.sum() > 2 else np.nan
ok_b = bool(rho_b >= C.V5_CHECK_MIN_SPEARMAN)
# ---- 4c: within-BH-source Spearman(T_total, hard colour F(16-25)/F(10-16)) on S1 ----
z = np.load(ROOT/'data/v2/processed/features.npz')
H = pd.DataFrame(L.v2_representations(z['rate'], z['edges'], z['F'])['H_colours'], columns=['c1', 'c2']).assign(obs_id=z['obs_id'])
s1 = s1.merge(H, on='obs_id')
rows = []
for src, d in s1[s1.label == 'BH'].groupby('source_id'):
    rows.append(dict(source_id=src, n=len(d), spearman_Ttotal_vs_c2=spearmanr(d.T_total, d.c2)[0] if len(d) > 2 else np.nan))
cc = pd.DataFrame(rows); med_c = float(np.nanmedian(cc.spearman_Ttotal_vs_c2)) if len(cc) else np.nan
ok_c = bool(med_c >= 0)
chk = pd.DataFrame([dict(check='4b cospectrum vs auto-power T2 Spearman (S1, 20-500 c/s/PCU)', n=int(m.sum()), value=rho_b,
                         threshold=C.V5_CHECK_MIN_SPEARMAN, passed=ok_b),
                    dict(check='4c median within-BH Spearman(T_total, hard colour)', n=len(cc), value=med_c, threshold=0.0, passed=ok_c)])
chk.to_csv(R5/f'v5_implementation_checks{SUF}.csv', index=False); cc.to_csv(R5/f'v5_check_bh_rms_hardness{SUF}.csv', index=False)
print('\nIMPLEMENTATION CHECKS:\n' + chk.round(3).to_string(index=False) + '\n' + cc.round(3).to_string(index=False))
if not LIMIT:
    progress('v5_timing_features', f"{int(tf.status.eq('ok').sum())}/{len(tf)} obs with timing features; checks 4b rho={rho_b:.3f} "
             f"({'pass' if ok_b else 'FAIL'}), 4c median={med_c:.2f} ({'pass' if ok_c else 'FAIL'})")
    if not (ok_b and ok_c):
        print('IMPLEMENTATION CHECK FAILED -> stop (preregistration_v5 §4)'); sys.exit(3)
print(f'total {time.time()-T0:.0f} s')
