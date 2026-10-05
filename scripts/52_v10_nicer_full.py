"""v10c (preregistration_v10.md sec. 3): NICER full observations for the 368 v9-accepted observations.
IC1: prefix + tail read equals a one-shot download of a whole small file. Tail = bytes after the v9 prefix up to 1 GB (curl
range requests, HEASARC AWS mirror; logged). Features: v9lib.obs_features on all valid 128-s segments (+ odd/even split-half,
12-15 / 2-10 keV background ratio). IC4: Cyg X-2 + GX 17+2 >= 2/3 soft-like. Outputs data/v10/processed/nicer_full_features.csv,
results/v10c/{ic1_concatenation.csv, prefix_vs_full.csv, split_half.csv}."""
import os, sys, time, subprocess
os.environ['XRB_VERSION'] = 'v10'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import config as C
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from concurrent.futures import ThreadPoolExecutor
from scipy.stats import spearmanr
import v9lib as L9, v10lib as L10

T0 = time.time()
D10, RC = ROOT/'data/v10/processed', ROOT/'results/v10c'
for p in (D10, RC): p.mkdir(parents=True, exist_ok=True)
obs = pd.read_csv(ROOT/'data/v9/observations.csv', dtype={'obsid': str})
obs = obs[obs.status == 'ok'].reset_index(drop=True)
print(len(obs), 'v9-accepted observations;', int((obs.stop != 'eof').sum()), 'need a tail', flush=True)

# ---------------- IC1 ----------------
c = obs[(obs.stop != 'eof') & (obs.file_bytes.between(10e6, 40e6))].sort_values('file_bytes').iloc[0]
tmp = L10.EXT/'nicer_ic1'/f'ni{c.obsid}_0mpu7_cl.evt.gz'; tmp.parent.mkdir(parents=True, exist_ok=True)
if not tmp.exists():
    r = L9._curl(['-f', '-o', str(tmp), c.url]); assert r.returncode == 0, r.stderr[:200]
one, _, comp1 = L9.read_prefix(tmp)
L10.download_tail(c.obsid)
two, _, comp2 = L10.read_full(c.obsid)
ok = comp1 and comp2 and all(np.array_equal(one[k], two[k]) for k in ('TIME', 'PI', 'DET_ID'))
pd.DataFrame([dict(check='IC1 prefix + tail == one-shot download', obsid=c.obsid, file_bytes=c.file_bytes, n_events=len(one['TIME']),
                   passed=bool(ok))]).to_csv(RC/'ic1_concatenation.csv', index=False)
print('IC1:', c.obsid, int(c.file_bytes), 'bytes,', len(one['TIME']), 'events -> passed' if ok else '-> FAILED', flush=True)
if not ok: progress('v10_nicer_full', 'IC1 FAILED -> stop'); sys.exit(3)
tmp.unlink()

# ---------------- tails ----------------
need = obs[obs.stop != 'eof'].obsid.tolist()
with ThreadPoolExecutor(8) as ex:
    infos = list(ex.map(L10.download_tail, need))
print(f'tails: {len(infos)} files, {sum(i["bytes"] for i in infos) / 1e9:.2f} GB, complete {sum(i["complete"] for i in infos)} '
      f'({time.time() - T0:.0f} s)', flush=True)


# ---------------- features ----------------
def one_obs(o):
    arr, h, complete = L10.read_full(o)
    rec, S = L9.obs_features(arr, return_segments=True)
    rec = dict(obsid=o, read_complete=bool(complete), bkg_ratio_12_15=L10.bkg_ratio(arr), **rec)
    if len(S) >= 2 * C.V9_MIN_SEG:
        for tag, idx in (('odd', np.arange(0, len(S), 2)), ('even', np.arange(1, len(S), 2))):
            for k, v in L10.half_features(S, idx).items(): rec[f'{k}_{tag}'] = v
    return rec


recs = Parallel(n_jobs=2, batch_size=1)(delayed(one_obs)(o) for o in obs.obsid)   # 2 workers: ~3 GB peak each for 1-GB files
F = obs[['obsid', 'source', 'label', 'time_bin', 'mjd']].merge(pd.DataFrame(recs), on='obsid')
F.to_csv(D10/'nicer_full_features.csv', index=False)
print(f'features ({time.time() - T0:.0f} s):', F.status.str.slice(0, 30).value_counts().to_dict(), flush=True)
ok = F[F.status == 'ok']
print(ok.groupby(['label', 'state']).agg(n=('obsid', 'size'), src=('source', 'nunique')).to_string(), flush=True)
print('segments per observation: prefix (v9) median', obs.n_seg.median(), '-> full median', ok.n_seg.median())

# ---------------- reliability ----------------
v9 = pd.read_csv(ROOT/'data/v9/processed/nicer_features.csv', dtype={'obsid': str}).set_index('obsid')
m = ok.set_index('obsid').join(v9[['T1', 'T2', 'T3', 'STATE', 'nu_c', 'c1', 'c2']], rsuffix='_v9')
rows = []
for k in ('T1', 'T2', 'T3', 'STATE', 'nu_c', 'c1', 'c2'):
    d = m[[k, k + '_v9']].dropna()
    rows.append(dict(feature=k, n=len(d), spearman_prefix_vs_full=spearmanr(d[k], d[k + '_v9'])[0]))
pd.DataFrame(rows).to_csv(RC/'prefix_vs_full.csv', index=False); print('\nprefix (v9) vs full:\n' + pd.DataFrame(rows).round(3).to_string(index=False))
rows = []
for k in ('T1', 'T2', 'T3', 'STATE', 'nu_c'):
    d = ok[[f'{k}_odd', f'{k}_even']].dropna() if f'{k}_odd' in ok else pd.DataFrame()
    rho = spearmanr(np.log10(d[f'{k}_odd']), np.log10(d[f'{k}_even']))[0] if k == 'nu_c' and len(d) else (spearmanr(d[f'{k}_odd'], d[f'{k}_even'])[0] if len(d) else np.nan)
    rows.append(dict(feature=k, n=len(d), spearman_odd_even=rho, spearman_brown=2 * rho / (1 + rho) if np.isfinite(rho) else np.nan))
pd.DataFrame(rows).to_csv(RC/'split_half.csv', index=False); print('\nsplit-half (full data):\n' + pd.DataFrame(rows).round(3).to_string(index=False))
st_v9 = v9.state.reindex(ok.obsid).values
print('\nstate change prefix -> full:\n' + pd.crosstab(pd.Series(st_v9, name='v9 prefix'), pd.Series(ok.state.values, name='full')).to_string())

# ---------------- IC4 ----------------
z = ok[ok.source.isin(C.V9_Z_SANITY)]; frac = float((z.state == 'soft-like').mean())
pd.DataFrame([dict(check='IC4 Cyg X-2 + GX 17+2 soft-like (full data)', n=len(z), value=frac, passed=bool(frac >= C.V7_SANITY_FRAC))]).to_csv(RC/'ic4_sanity.csv', index=False)
print(f'IC4: {frac:.3f} of {len(z)} -> {"passed" if frac >= C.V7_SANITY_FRAC else "FAILED"}')
progress('v10_nicer_full', f"{len(ok)} ok of {len(F)}; tails {sum(i['bytes'] for i in infos) / 1e9:.1f} GB; IC4 {frac:.2f}")
if frac < C.V7_SANITY_FRAC: sys.exit(3)
print(f'total {time.time() - T0:.0f} s')
