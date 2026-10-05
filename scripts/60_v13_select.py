"""v13 step 1 (preregistration_v13.md): a third, disjoint set of never-used NICER observations of the v9 sources: eligible
observations (cached v9 TAP tables: target within 0.05 deg, exposure >= 1000 s) NOT among the v9 tries (792) nor the v11 tries
(588); 8 time-stratified bins, candidates ranked by default_rng(SEED + 2000 + position in data/v9/sources.csv), <= 3 tries per bin.
IC: no overlap with v9 / v11 tries. Output data/v13/observation_candidates.csv."""
import os, sys
os.environ['XRB_VERSION'] = 'v13'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import config as C
import numpy as np, pandas as pd
from astropy.time import Time

D13 = ROOT/'data/v13'; D13.mkdir(parents=True, exist_ok=True)
S = pd.read_csv(ROOT/'data/v9/sources.csv')
tried = set(pd.read_csv(ROOT/'data/v9/observations.csv', dtype={'obsid': str}).obsid) | set(pd.read_csv(ROOT/'data/v11/observations.csv', dtype={'obsid': str}).obsid)
cands = []
for k, r in enumerate(S.itertuples(), start=1):
    if not r.included: continue
    f = ROOT/f"data/raw/catalogs/nicer/nicermastr_{r.name.replace(' ', '_').replace('/', '_')}.csv"
    if not f.exists(): continue
    t = pd.read_csv(f, dtype={'DataLinkID': str, 'obsid': str})
    t['oid'] = (t['DataLinkID'] if 'DataLinkID' in t else t['obsid']).astype(str).str.strip()
    t = t[t.time.notna() & (t.exposure >= C.V9_MIN_EXPOSURE_S)].drop_duplicates('oid')
    el = t[~t.oid.isin(tried)].sort_values('time').reset_index(drop=True)
    rng = np.random.default_rng(C.SEED + C.V13_SEED_OFFSET + k)
    for b, idx in enumerate(np.array_split(np.arange(len(el)), C.V11_N_PER_SOURCE)):
        for rank, i in enumerate(rng.permutation(idx)):
            e = el.iloc[i]; ym = Time(float(e.time), format='mjd').strftime('%Y_%m')
            cands.append(dict(obsid=e.oid, source=r.name, label=r.label, group='v9 source, third set', time_bin=b, rank_in_bin=rank,
                              mjd=round(float(e.time), 5), exposure=float(e.exposure), ym=ym,
                              url=f"{C.V9_ARCHIVE}{ym}/{e.oid}/xti/event_cl/ni{e.oid}_0mpu7_cl.evt.gz"))
cd = pd.DataFrame(cands)
ov = len(set(cd.obsid) & tried); print('IC: overlap with v9 / v11 tries =', ov)
if ov: sys.exit(3)
cd.to_csv(D13/'observation_candidates.csv', index=False)
print(cd.groupby('label').agg(sources=('source', 'nunique'), candidates=('obsid', 'size')).to_string(), '\nsource x bin groups:', cd.groupby(['source', 'time_bin']).ngroups)
progress('v13_select', f"{cd.groupby(['source', 'time_bin']).ngroups} source-bin groups, {len(cd)} candidates; overlap 0")
