"""v12 step 1 (preregistration_v12.md sec. 2): 3C50 background (HEASoft nibackgen3C50, NICER CALDB) for every v10 / v11 NICER
observation with 2-10 keV rate < V12_BKG_MAX_RATE. Each observation is processed inside WSL on the native file system by
scripts/v12_bkg3c50.sh (download cl + ufa from the HEASARC AWS mirror, run 3C50, keep only the total and background spectra,
delete the event files). Downloads (URL, bytes, SHA256) are logged in logs/downloads.jsonl. Resumable (checkpoint jsonl).
Output: data/v12/processed/bkg3c50.csv (band rates of the total and background spectra, background fractions)."""
import os, sys, json, time, subprocess, threading, datetime
os.environ['XRB_VERSION'] = 'v12'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress, _LOCK
import config as C
import numpy as np, pandas as pd
from astropy.io import fits
from concurrent.futures import ThreadPoolExecutor
import v10lib as L10

T0 = time.time()
D12 = ROOT/'data/v12/processed'; D12.mkdir(parents=True, exist_ok=True)
SPEC = L10.EXT.parent/'nicer_bkg_spectra'; CAL = L10.EXT.parent/C.V12_CALDB


def wsl(p):
    p = str(p.resolve()).replace('\\', '/'); return '/mnt/' + p[0].lower() + p[2:]


V = pd.read_csv(ROOT/'data/v10/processed/nicer_full_features.csv', dtype={'obsid': str}); V = V[V.status == 'ok']
U9 = pd.read_csv(ROOT/'data/v9/observations.csv', dtype={'obsid': str}).set_index('obsid').url
N = pd.read_csv(ROOT/'data/v11/processed/nicer_new_features.csv', dtype={'obsid': str}); N = N[N.status == 'ok']
obs = pd.concat([V[['obsid', 'source', 'label', 'rate_2_10']].assign(url=V.obsid.map(U9), sample='v10'),
                 N[['obsid', 'source', 'label', 'rate_2_10', 'url']].assign(sample='v11')], ignore_index=True)
todo = obs[obs.rate_2_10 < C.V12_BKG_MAX_RATE].reset_index(drop=True)
print(f'{len(obs)} NICER observations (v10 {int((obs["sample"] == "v10").sum())}, v11 {int((obs["sample"] == "v11").sum())}); '
      f'3C50 for {len(todo)} with 2-10 keV < {C.V12_BKG_MAX_RATE:g} c/s', flush=True)
CK = ROOT/'data/v12/bkg3c50_partial.jsonl'; LK = threading.Lock(); done = {}
if CK.exists():
    for l in CK.read_text(encoding='utf-8').splitlines(): r = json.loads(l); done[r['obsid']] = r


def band_rates(path):
    with fits.open(path) as h:
        d = h[1].data; hd = h[1].header; ch = np.asarray(d['CHANNEL'])
        r = np.asarray(d['RATE'], float) if 'RATE' in d.columns.names else np.asarray(d['COUNTS'], float) / float(hd['EXPOSURE'])
        return {k: float(r[(ch >= a) & (ch < b)].sum()) for k, (a, b) in C.V12_PI_BANDS.items()}, float(hd['EXPOSURE'])


def one(r):
    if r.obsid in done and done[r.obsid].get('status') == 'ok': return done[r.obsid]
    out = SPEC/r.obsid; out.mkdir(parents=True, exist_ok=True)
    ufa = r.url.replace('_cl.evt.gz', '_ufa.evt.gz')
    p = subprocess.run(['wsl', '-d', 'Ubuntu-22.04', '-u', 'root', '--', 'bash', wsl(ROOT/'scripts/v12_bkg3c50.sh'), r.obsid, r.url, ufa, wsl(out), wsl(CAL)],
                       capture_output=True, text=True)
    rec = dict(obsid=r.obsid, source=r.source, label=r.label, sample=r.sample, rate_2_10=r.rate_2_10)
    for l in p.stdout.splitlines():
        if l.startswith('SHA256 '):
            _, fn, h, nb = l.split()
            info = dict(url=r.url if '_cl.' in fn else ufa, path='deleted after 3C50 (WSL /tmp)', bytes=int(nb), sha256=h,
                        utc=datetime.datetime.now(datetime.UTC).isoformat(), tool='curl in WSL (v12 3C50)')
            with _LOCK, (ROOT/'logs/downloads.jsonl').open('a', encoding='utf-8') as f: f.write(json.dumps(info) + '\n')
    rc = [l for l in p.stdout.splitlines() if l.startswith('DONE ')]
    rec['rc'] = int(rc[-1].split()[1]) if rc else -1
    try:
        T, et = band_rates(out/f'tot_{r.obsid}.pi'); B, eb = band_rates(out/f'bkg_{r.obsid}.pi')
        rec.update({f'T_{k}': v for k, v in T.items()}); rec.update({f'B_{k}': v for k, v in B.items()})
        rec.update({f'f_{k}': (B[k] / T[k] if T[k] > 0 else np.nan) for k in T}); rec['exposure_3c50'] = et
        rec['status'] = 'ok'
    except Exception as e:
        rec['status'] = f'failed (rc {rec["rc"]}): {type(e).__name__}: {e}'[:200]
    with LK, CK.open('a', encoding='utf-8') as f: f.write(json.dumps(rec) + '\n')
    done[r.obsid] = rec
    if len(done) % 25 == 0: print(f'{len(done)}/{len(todo)} done ({time.time() - T0:.0f} s)', flush=True)
    return rec


with ThreadPoolExecutor(C.V12_N_WORKERS) as ex:
    res = list(ex.map(one, todo.itertuples()))
B = pd.DataFrame(res); B.to_csv(D12/'bkg3c50.csv', index=False)
ok = B[B.status == 'ok']
print(f'\n3C50: {len(ok)} ok of {len(B)} ({time.time() - T0:.0f} s)\n' + B.status.str.slice(0, 40).value_counts().to_string())
print('f (2-10 keV) quantiles:', ok.f_T.quantile([.1, .5, .9, .99]).round(4).to_dict(), '| f > 0.20:', int((ok.f_T > C.V12_FBKG_MAX).sum()))
progress('v12_bkg', f'3C50 ok {len(ok)}/{len(B)}; f>0.2: {int((ok.f_T > C.V12_FBKG_MAX).sum())}')
