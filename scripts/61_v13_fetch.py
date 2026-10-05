"""v13 step 2 (preregistration_v13.md; identical to 56_v11_fetch.py except the paths): for every source x time bin try up to V11_MAX_TRIES never-used candidates; stream the
whole cleaned event file (<= 1 GB, raw bytes not stored) into the frozen feature pipeline (v9lib.obs_features) and accept the first
with status 'ok'. 404/403 -> adjacent month folders. Outputs data/v13/observations.csv (every try) and
data/v13/processed/nicer_new_features.csv (accepted). Checkpoint: data/v13/observations_partial.jsonl (resumable)."""
import os, sys, time, json, threading
os.environ['XRB_VERSION'] = 'v13'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import config as C
import numpy as np, pandas as pd
from astropy.time import Time
from concurrent.futures import ThreadPoolExecutor
import v11lib as L11

T0 = time.time()
D11 = ROOT/'data/v13'; (D11/'processed').mkdir(parents=True, exist_ok=True)
cand = pd.read_csv(D11/'observation_candidates.csv', dtype={'obsid': str})
CK = D11/'observations_partial.jsonl'; LK = threading.Lock()
done = {}
if CK.exists():
    for l in CK.read_text(encoding='utf-8').splitlines():
        r = json.loads(l); done[r['obsid']] = r


def month_variants(ym):
    t = Time(ym.replace('_', '-') + '-15', format='iso')
    return [ym] + [Time(t.mjd + d, format='mjd').strftime('%Y_%m') for d in (-31, 31)]


def try_one(c):
    if c.obsid in done: return done[c.obsid]
    rec = dict(obsid=c.obsid, source=c.source, label=c.label, group=c.group, time_bin=c.time_bin, rank_in_bin=c.rank_in_bin, mjd=c.mjd, exposure_cat=c.exposure)
    last = None
    for ym in month_variants(c.ym):
        url = f"{C.V9_ARCHIVE}{ym}/{c.obsid}/xti/event_cl/ni{c.obsid}_0mpu7_cl.evt.gz"
        try:
            rec.update(L11.obs_features_stream(url)); break
        except FileNotFoundError as e:
            last = e
        except Exception as e:
            rec['status'] = f'error: {type(e).__name__}: {e}'[:200]; break
    else:
        rec['status'] = f'missing (event file not found: {last})'[:200]
    rec = {k: (v.item() if hasattr(v, 'item') else v) for k, v in rec.items()}
    with LK, CK.open('a', encoding='utf-8') as f: f.write(json.dumps(rec, default=str) + '\n')
    done[c.obsid] = rec
    return rec


def process_bin(key, grp):
    rows, acc = [], None
    for c in grp.sort_values('rank_in_bin').head(C.V11_MAX_TRIES).itertuples():
        r = try_one(c); rows.append(r)
        if r.get('status') == 'ok': acc = r; break
    print(f"{key[0]:22s} bin {key[1]} {'accepted ' + acc['obsid'] + ' ' + acc['state'] if acc else 'EMPTY'} "
          f"({rows[-1].get('status', '')[:40]}; {sum((r.get('bytes') or 0) for r in rows) / 1e6:.0f} MB) [{time.time() - T0:.0f} s]", flush=True)
    return rows


groups = list(cand.groupby(['source', 'time_bin'], sort=False))
with ThreadPoolExecutor(C.V11_N_WORKERS) as ex:
    res = list(ex.map(lambda kg: process_bin(*kg), groups))
obs = pd.DataFrame([r for rr in res for r in rr])
obs.to_csv(D11/'observations.csv', index=False)
acc = obs[obs.status == 'ok']; acc.to_csv(D11/'processed/nicer_new_features.csv', index=False)
print(f'\n{len(acc)} accepted of {len(groups)} bins; tried {len(obs)}; streamed {obs.bytes.fillna(0).sum() / 1e9:.2f} GB ({time.time() - T0:.0f} s)')
print(obs.status.astype(str).str.slice(0, 45).value_counts().to_string())
print(acc.groupby(['group', 'label', 'state']).agg(n=('obsid', 'size'), src=('source', 'nunique')).to_string())
progress('v13_fetch', f"{len(acc)} accepted new obs; {acc.source.nunique()} sources; {obs.bytes.fillna(0).sum() / 1e9:.1f} GB streamed")
