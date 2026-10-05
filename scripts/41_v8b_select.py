"""v8b step 1 (preregistration_v8.md sec. 4): dynamically confirmed BHs of Marcel+2026 Table 1 not used in any earlier RXTE
sample (expected: GS 1354-64, SS 433). Pointings within 0.1 deg of the SIMBAD position (CDS Sesame, data/v7c/sesame_positions.csv),
all gain epochs, catalogue exposure >= 1000 s (missing exposure -> kept, decided by the spectrum exposure rule after download),
STD1RATE >= 5 c/s/PCU where a MissionLongData catalogue exists; >= 3 eligible; up to 15 time-stratified candidates with the
03_select_observations.py algorithm (default_rng(SEED + position)). Source of pointings: MissionLongData if it exists,
else the HEASARC master catalogue (xtemaster) via TAP. Outputs data/v8b/sources.csv, observation_candidates.csv,
results/v8b/attrition_catalog.csv; then run 21_v4b2_fetch_process.py with XRB_VERSION=v8b."""
import os, sys, io, urllib.error
os.environ['XRB_VERSION'] = 'v8b'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, ARCHIVE, download, progress, D, R
import config as C
import numpy as np, pandas as pd, requests
from astropy.io import fits
from astropy.table import Table
from astropy.io.votable import parse_single_table
import v7lib as L7

pos = pd.read_csv(ROOT/'data/v7c/sesame_positions.csv').set_index('name')
REF = 'https://arxiv.org/abs/2606.19952'
used = set()
for v in ('v2', 'v4b2', 'v6', 'v7b2'):
    used |= set(pd.read_csv(ROOT/f'data/{v}/sources.csv').name)
print('already used RXTE sources:', len(used))


def from_mld(cat):
    p = download(ARCHIVE + 'MissionLongData/' + cat + '.fits.gz', 'data/raw/catalogs/' + cat + '.fits.gz')
    with fits.open(p) as h:
        df = Table(h[1].data).to_pandas(); hdr = h[1].header
    df['OBSID'] = [v.decode().strip() if isinstance(v, bytes) else str(v).strip() for v in df.OBSID]
    df['mjd'] = df.TIME.astype(float) + hdr['MJDREFI'] + hdr['MJDREFF']
    return pd.DataFrame(dict(OBSID=df.OBSID, mjd=df.mjd, RA=df.RA.astype(float), DEC=df.DEC.astype(float), EXPOSURE=df.EXPOSURE.astype(float),
                             NPCU=df.NPCU.astype(float), STD1RATE=df.STD1RATE.astype(float), origin='MissionLongData/' + cat))


def from_tap(ra, dec, name):
    q = (f"SELECT obsid, target_name, ra, dec, time, exposure FROM xtemaster "
         f"WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{C.COORD_TOL_DEG}))=1")
    r = requests.post(C.V8_TAP_URL, data=dict(REQUEST='doQuery', LANG='ADQL', QUERY=q), timeout=120); r.raise_for_status()
    (ROOT/'data/raw/catalogs').mkdir(parents=True, exist_ok=True)
    (ROOT/f'data/raw/catalogs/xtemaster_{name.replace(" ", "")}.xml').write_bytes(r.content)
    t = parse_single_table(io.BytesIO(r.content)).to_table().to_pandas()
    t = t[t.time.notna()]
    return pd.DataFrame(dict(OBSID=t.DataLinkID.astype(str).str.strip() if 'DataLinkID' in t else t.obsid.astype(str).str.strip(),
                             mjd=t.time.astype(float), RA=t.ra.astype(float), DEC=t.dec.astype(float), EXPOSURE=t.exposure.astype(float),
                             NPCU=np.nan, STD1RATE=np.nan, origin='HEASARC TAP xtemaster'))


SRC = [(sid, name) for sid, name in C.V8_NEW_BH.items()]
assert not (set(n for _, n in SRC) & used), 'a v8b source was already used'
rows, cands, att = [], [], []
for k, (sid, name) in enumerate(SRC, start=1):
    ra_s, dec_s = float(pos.loc[name].ra), float(pos.loc[name].dec)
    try:
        df = from_mld(sid.replace('-', '-'))
    except urllib.error.HTTPError as e:
        if e.code != 404: raise
        df = from_tap(ra_s, dec_s, name)
    n0 = len(df); df = df[~df.OBSID.duplicated(keep='first')].copy()
    df['sep_deg'] = L7.sep_deg(df.RA, df.DEC, ra_s, dec_s)
    a = dict(source_id=sid, origin=df.origin.iloc[0], catalog_rows=n0, after_dedup=len(df))
    m = (df.mjd >= C.MJD_MIN) & (df.mjd < C.MJD_MAX); a['after_mjd_window'] = int(m.sum())
    m &= (df.EXPOSURE >= C.MIN_EXPOSURE_S) | df.EXPOSURE.isna(); a['after_exposure_or_missing'] = int(m.sum())
    a['exposure_missing'] = int((m & df.EXPOSURE.isna()).sum())
    m &= (df.STD1RATE >= C.MIN_STD1RATE) | df.STD1RATE.isna(); a['after_std1rate'] = int(m.sum())
    m &= df.sep_deg <= C.COORD_TOL_DEG; a['after_pointing_simbad'] = int(m.sum())
    att.append(a)
    el = df[m].sort_values('mjd').reset_index(drop=True)
    rows.append(dict(source_id=sid, name=name, aliases='', ra_deg=round(ra_s, 4), dec_deg=round(dec_s, 4), label='BH',
                     evidence='Dynamically confirmed BH (Marcel et al. 2026, arXiv:2606.19952, Table 1)', reference_url=REF,
                     status='confirmed', coord_origin='SIMBAD position (CDS Sesame)', n_eligible=len(el), included=len(el) >= C.MIN_ELIGIBLE,
                     pointing_origin=df.origin.iloc[0]))
    if len(el) < C.MIN_ELIGIBLE: print(sid, a, 'DROPPED'); continue
    rng = np.random.default_rng(C.SEED + k)
    for b, idx in enumerate(np.array_split(np.arange(len(el)), C.N_PER_SOURCE)):
        for rank, i in enumerate(rng.permutation(idx)):
            r = el.iloc[i]
            cands.append(dict(obs_id=r.OBSID, source_id=sid, label='BH', time_bin=b, rank_in_bin=rank, mjd=round(float(r.mjd), 5),
                              cat_exposure=float(r.EXPOSURE), cat_npcu=float(r.NPCU), cat_std1rate=float(r.STD1RATE),
                              pointing_sep_deg=round(float(r.sep_deg), 4)))
    print(sid, a, flush=True)
pd.DataFrame(rows).to_csv(D/'sources.csv', index=False)
pd.DataFrame(cands).to_csv(D/'observation_candidates.csv', index=False)
pd.DataFrame(att).to_csv(R/'attrition_catalog.csv', index=False)
print(pd.DataFrame(rows)[['source_id', 'n_eligible', 'included', 'pointing_origin']].to_string(index=False), '\ncandidates:', len(cands))
progress('v8b_select', f"{sum(r['included'] for r in rows)} new dynamical BHs, {len(cands)} ranked candidates")
