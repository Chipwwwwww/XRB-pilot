"""v9 step 2 (preregistration_v9.md sec. 3): for every source x time bin, try up to V9_MAX_TRIES ranked candidates: stream the
start of the cleaned event file (v9lib.stream_prefix; 404 -> adjacent month folders), parse it (v9lib.read_prefix) and compute
the features (v9lib.obs_features); accept the first candidate with status 'ok'. Outputs data/v9/observations.csv (every try),
data/v9/processed/nicer_features.csv (accepted). V9_SMOKE=<n> processes only the first n bins of a BH and an NS source."""
import os, sys, time, json
os.environ['XRB_VERSION'] = 'v9'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import config as C
import numpy as np, pandas as pd, requests
from astropy.time import Time
from concurrent.futures import ThreadPoolExecutor
import v9lib as L9

T0 = time.time()
D9 = ROOT/'data/v9'; (D9/'processed').mkdir(parents=True, exist_ok=True)
cand = pd.read_csv(D9/'observation_candidates.csv', dtype={'obsid': str})
SMOKE = int(os.environ.get('V9_SMOKE', '0'))
if SMOKE:
    keep = ['MAXI J1820+070', 'Aql X-1']
    cand = cand[cand.source.isin(keep) & (cand.time_bin < SMOKE)]


def month_variants(ym):
    t = Time(ym.replace('_', '-') + '-15', format='iso')
    return [ym] + [Time(t.mjd + d, format='mjd').strftime('%Y_%m') for d in (-31, 31)]


def fetch(c):
    last = None
    for ym in month_variants(c.ym):
        url = f"{C.V9_ARCHIVE}{ym}/{c.obsid}/xti/event_cl/ni{c.obsid}_0mpu7_cl.evt.gz"
        try:
            return L9.stream_prefix(url, f'nicer/{c.obsid}/ni{c.obsid}_0mpu7_cl.evt.gz.prefix')
        except FileNotFoundError as e:
            last = e
    raise FileNotFoundError(f'event file not found ({last})')


def process_bin(key, grp):
    rows, acc = [], None
    for c in grp.sort_values('rank_in_bin').head(C.V9_MAX_TRIES).itertuples():
        rec = dict(obsid=c.obsid, source=c.source, label=c.label, time_bin=c.time_bin, rank_in_bin=c.rank_in_bin, mjd=c.mjd, exposure_cat=c.exposure)
        try:
            info = fetch(c); rec.update(url=info['url'], bytes=info['bytes'], file_bytes=info['file_bytes'], stop=info['stop'], rows_read=info['rows'])
            arr, h, complete = L9.read_prefix(L9.EXT/info['path'].replace('XRB_EXTERNAL_RAW/', ''))
            rec.update(L9.obs_features(arr))
        except Exception as e:
            rec['status'] = f'error: {type(e).__name__}: {e}'[:200]
        rows.append(rec)
        if rec.get('status') == 'ok': acc = rec; break
    print(f"{key[0]:22s} bin {key[1]} {'accepted ' + acc['obsid'] + ' ' + acc['state'] if acc else 'EMPTY'} "
          f"({rows[-1].get('status', '')[:40]}; {sum(r.get('bytes', 0) or 0 for r in rows) / 1e6:.0f} MB) [{time.time() - T0:.0f} s]", flush=True)
    return rows


groups = list(cand.groupby(['source', 'time_bin'], sort=False))
with ThreadPoolExecutor(int(os.environ.get('V9_THREADS', '8'))) as ex:
    res = list(ex.map(lambda kg: process_bin(*kg), groups))
obs = pd.DataFrame([r for rr in res for r in rr])
tag = '_smoke' if SMOKE else ''
obs.to_csv(D9/f'observations{tag}.csv', index=False)
acc = obs[obs.status == 'ok']
acc.to_csv(D9/f'processed/nicer_features{tag}.csv', index=False)
print(f'\n{len(acc)} accepted of {len(groups)} bins; tried {len(obs)}; downloaded {obs.bytes.fillna(0).sum() / 1e9:.2f} GB ({time.time() - T0:.0f} s)')
print(obs.status.str.slice(0, 45).value_counts().to_string())
print(acc.groupby(['label', 'state']).agg(n=('obsid', 'size'), src=('source', 'nunique')).to_string())
if not SMOKE: progress('v9_nicer', f"{len(acc)} accepted obs; {acc.source.nunique()} sources; {obs.bytes.fillna(0).sum() / 1e9:.2f} GB")
