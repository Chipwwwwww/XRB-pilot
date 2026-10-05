"""v9 step 1 (preregistration_v9.md sec. 3): NICER sources and candidate observations.
BH: Marcel+2026 Table 1 (Sesame positions, data/v7c/sesame_positions.csv); NS: MINBAR DR1 burst sources (MINBAR positions),
excluding entries with another MINBAR entry within 0.05 deg (unresolvable by NICER). Observations: nicermastr target position
within 0.05 deg, exposure >= 1000 s; >= 5 eligible; 8 time-stratified bins, candidates ranked by default_rng(SEED + position).
Outputs data/v9/sources.csv, data/v9/observation_candidates.csv, results/v9/attrition_catalog.csv."""
import os, sys, io, time
os.environ['XRB_VERSION'] = 'v9'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import config as C
import numpy as np, pandas as pd, requests
from astropy.io.votable import parse_single_table
from astropy.time import Time
from concurrent.futures import ThreadPoolExecutor
import v7lib as L7

D9, R9 = ROOT/'data/v9', ROOT/'results/v9'
for p in (D9, R9, ROOT/'data/raw/catalogs/nicer'): p.mkdir(parents=True, exist_ok=True)
MARCEL = ['M33 X-7', 'Cyg X-1', 'LMC X-1', 'SS 433', 'LMC X-3', 'SAX J1819.3-2525', '4U 1543-475', 'GRO J1655-40', 'GRO J0422+32',
          'GRS 1124-684', 'GX 339-4', 'GS 1354-64', 'Swift J1727.8-1613', 'XTE J1650-500', 'GS 2023+338', 'MAXI J1820+070',
          'XTE J1859+226', 'GRS 1915+105', 'V616 Mon', 'MAXI J1305-704', 'H 1705-250', 'XTE J1550-564', 'GS 2000+25', 'GRS 1009-45',
          'XTE J1118+480']
pos = pd.read_csv(ROOT/'data/v7c/sesame_positions.csv').set_index('name')
ms = L7.load_minbar_sources()
src = [dict(name=n, label='BH', ra=float(pos.loc[n].ra), dec=float(pos.loc[n].dec), evidence='Marcel+2026 Table 1 (dynamical BH)',
            pos_origin='SIMBAD (Sesame)') for n in MARCEL]
ns = ms.copy(); ns['n_close'] = [int((L7.sep_deg(ns.ra.values, ns.dec.values, r.ra, r.dec) <= C.V9_TOL_DEG).sum() - 1) for r in ns.itertuples()]
for n, r in ns.sort_index().iterrows():
    src.append(dict(name=n, label='NS', ra=float(r.ra), dec=float(r.dec), evidence='MINBAR DR1 burst source (type-I bursts)',
                    pos_origin='MINBAR source table', excluded_confused=bool(r.n_close > 0)))
S = pd.DataFrame(src); S['excluded_confused'] = S.excluded_confused.astype('boolean').fillna(False).astype(bool)
print(f"sources: {len(S)} ({(S.label == 'BH').sum()} BH, {(S.label == 'NS').sum()} NS; {int(S.excluded_confused.sum())} NS excluded as confused)", flush=True)


def tap(ra, dec, name):
    q = (f"SELECT obsid, name, ra, dec, time, exposure, num_fpm FROM nicermastr "
         f"WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{C.V9_TOL_DEG}))=1")
    for k in range(4):
        try:
            r = requests.post(C.V9_TAP_URL, data=dict(REQUEST='doQuery', LANG='ADQL', QUERY=q), timeout=120); r.raise_for_status()
            t = parse_single_table(io.BytesIO(r.content)).to_table().to_pandas(); break
        except Exception:
            if k == 3: raise
            time.sleep(5)
    t.to_csv(ROOT/f"data/raw/catalogs/nicer/nicermastr_{name.replace(' ', '_').replace('/', '_')}.csv", index=False)
    return t


with ThreadPoolExecutor(6) as ex:
    tabs = list(ex.map(lambda r: tap(r.ra, r.dec, r.name), S.itertuples()))
cands, att = [], []
for k, (r, t) in enumerate(zip(S.itertuples(), tabs), start=1):
    t = t[t.time.notna()].copy(); t['obsid'] = (t['DataLinkID'] if 'DataLinkID' in t else t['obsid']).astype(str).str.strip()   # VOTable ID column
    a = dict(name=r.name, label=r.label, rows=len(t))
    t = t[~t.obsid.duplicated()]; m = t.exposure >= C.V9_MIN_EXPOSURE_S; a['after_exposure'] = int(m.sum())
    el = t[m].sort_values('time').reset_index(drop=True); a['eligible'] = len(el)
    a['included'] = bool(len(el) >= C.V9_MIN_ELIGIBLE and not r.excluded_confused)
    att.append(a)
    if not a['included']: continue
    rng = np.random.default_rng(C.SEED + k)
    for b, idx in enumerate(np.array_split(np.arange(len(el)), C.V9_N_PER_SOURCE)):
        for rank, i in enumerate(rng.permutation(idx)):
            e = el.iloc[i]; ym = Time(float(e.time), format='mjd').strftime('%Y_%m')
            cands.append(dict(obsid=e.obsid, source=r.name, label=r.label, time_bin=b, rank_in_bin=rank, mjd=round(float(e.time), 5),
                              exposure=float(e.exposure), num_fpm=e.num_fpm, ym=ym,
                              url=f"{C.V9_ARCHIVE}{ym}/{e.obsid}/xti/event_cl/ni{e.obsid}_0mpu7_cl.evt.gz"))
A = pd.DataFrame(att); S = S.merge(A[['name', 'eligible', 'included']], on='name')
S.to_csv(D9/'sources.csv', index=False); A.to_csv(R9/'attrition_catalog.csv', index=False)
cd = pd.DataFrame(cands); cd.to_csv(D9/'observation_candidates.csv', index=False)
inc = S[S.included]
print(inc.groupby('label').size().to_string(), '\nBH included:', ', '.join(inc[inc.label == 'BH'].name), '\ncandidates:', len(cd), flush=True)
progress('v9_select', f"{(inc.label == 'BH').sum()} BH, {(inc.label == 'NS').sum()} NS sources; {len(cd)} ranked candidates")
