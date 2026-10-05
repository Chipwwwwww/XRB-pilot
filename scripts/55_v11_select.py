"""v11 step 1 (preregistration_v11.md sec. 2): never-used NICER observations.
(i) the 66 v9 sources: eligible observations (cached v9 TAP tables: target within 0.05 deg, exposure >= 1000 s) NOT among the 792
v9 tries; 8 time-stratified bins, candidates ranked by default_rng(SEED + 1000 + position in data/v9/sources.csv), <= 3 tries.
(ii) never-used NICER sources (v9 table: not included, not confused, 1-4 eligible observations): every eligible observation.
IC3: no overlap with the v9 tries. Outputs data/v11/observation_candidates.csv."""
import os, sys
os.environ['XRB_VERSION'] = 'v11'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import config as C
import numpy as np, pandas as pd
from astropy.time import Time

D11 = ROOT/'data/v11'; D11.mkdir(parents=True, exist_ok=True)
S = pd.read_csv(ROOT/'data/v9/sources.csv')
tried = set(pd.read_csv(ROOT/'data/v9/observations.csv', dtype={'obsid': str}).obsid)
cands = []
for k, r in enumerate(S.itertuples(), start=1):
    f = ROOT/f"data/raw/catalogs/nicer/nicermastr_{r.name.replace(' ', '_').replace('/', '_')}.csv"
    if not f.exists(): continue
    t = pd.read_csv(f, dtype={'DataLinkID': str, 'obsid': str})
    t['oid'] = (t['DataLinkID'] if 'DataLinkID' in t else t['obsid']).astype(str).str.strip()
    t = t[t.time.notna() & (t.exposure >= C.V9_MIN_EXPOSURE_S)].drop_duplicates('oid')
    el = t[~t.oid.isin(tried)].sort_values('time').reset_index(drop=True)
    if r.included:
        group, bins = 'v9 source, new observations', np.array_split(np.arange(len(el)), C.V11_N_PER_SOURCE)
    elif (not r.excluded_confused) and 1 <= len(el) <= 4:
        group, bins = 'never-used NICER source', [np.array([i]) for i in range(len(el))]
    else:
        continue
    rng = np.random.default_rng(C.SEED + C.V11_SEED_OFFSET + k)
    for b, idx in enumerate(bins):
        for rank, i in enumerate(rng.permutation(idx)):
            e = el.iloc[i]; ym = Time(float(e.time), format='mjd').strftime('%Y_%m')
            cands.append(dict(obsid=e.oid, source=r.name, label=r.label, group=group, time_bin=b, rank_in_bin=rank, mjd=round(float(e.time), 5),
                              exposure=float(e.exposure), ym=ym, url=f"{C.V9_ARCHIVE}{ym}/{e.oid}/xti/event_cl/ni{e.oid}_0mpu7_cl.evt.gz"))
cd = pd.DataFrame(cands)
ic3 = len(set(cd.obsid) & tried)
print(f'IC3: overlap with v9 tries = {ic3}', flush=True)
if ic3: sys.exit(3)
cd.to_csv(D11/'observation_candidates.csv', index=False)
print(cd.groupby(['group', 'label']).agg(sources=('source', 'nunique'), bins=('time_bin', lambda s: 0), candidates=('obsid', 'size')).to_string())
nb = cd.groupby(['source', 'time_bin']).ngroups
print('source x bin groups:', nb)
progress('v11_select', f'{nb} source-bin groups, {len(cd)} candidates; IC3 overlap 0')
