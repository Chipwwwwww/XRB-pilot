"""v7b2 step 1 (preregistration_v7.md §5, 3b): persistent dynamical BHs Cyg X-1, LMC X-1, LMC X-3 (Marcel+2026 Table 1)
with the v2 rules: gain epoch 5 (MJD 51677-55931), catalogue EXPOSURE >= 1000 s, STD1RATE >= 5 c/s/PCU, >= 10 eligible,
15 time-stratified candidates with the 03_select_observations.py algorithm (default_rng(SEED + position)).
Pointing rule (approved, sec. 7 item 1): pointing within 0.1 deg of the SIMBAD position (CDS Sesame, cached in
data/v6/source_positions.csv). sources.csv carries the SIMBAD position so that 04's header check uses it too."""
import os, sys
os.environ['XRB_VERSION'] = 'v7b2'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, ARCHIVE, download, progress, D, R
import config as C
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.table import Table
import v7lib as L7

pos = pd.read_csv(ROOT/'data/v6/source_positions.csv').set_index('name')
REF = 'https://arxiv.org/abs/2606.19952'
SRC = [('CYGX1', 'CYGX1', 'Cyg X-1', 'HD 226868 (O9.7 Iab)'), ('LMCX1', 'LMCX1', 'LMC X-1', 'O8(f)p'), ('LMCX3', 'LMCX3', 'LMC X-3', 'B2.5 Ve')]
rows, cands, att = [], [], []
for k, (sid, cat, name, comp) in enumerate(SRC, start=1):
    p = download(ARCHIVE + 'MissionLongData/' + cat + '.fits.gz', 'data/raw/catalogs/' + cat + '.fits.gz')
    with fits.open(p) as h:
        df = Table(h[1].data).to_pandas(); hdr = h[1].header
    df['OBSID'] = [v.decode().strip() if isinstance(v, bytes) else str(v).strip() for v in df.OBSID]
    df['mjd'] = df.TIME.astype(float) + hdr['MJDREFI'] + hdr['MJDREFF']
    df['RA'] = df.RA.astype(float); df['DEC'] = df.DEC.astype(float)
    ra_s, dec_s = float(pos.loc[name].ra), float(pos.loc[name].dec)
    ra0, dec0 = float(np.nanmedian(df.RA)), float(np.nanmedian(df.DEC))
    n0 = len(df); df = df[~df.OBSID.duplicated(keep='first')].copy()
    df['sep_deg'] = L7.sep_deg(df.RA, df.DEC, ra_s, dec_s)
    a = dict(source_id=sid, catalog_rows=n0, after_dedup=len(df), catalogue_median_sep_from_simbad_deg=round(float(L7.sep_deg(ra0, dec0, ra_s, dec_s)), 4))
    m = (df.mjd >= C.MJD_MIN) & (df.mjd < C.MJD_MAX); a['after_epoch5_window'] = int(m.sum())
    m &= df.EXPOSURE >= C.MIN_EXPOSURE_S; a['after_exposure'] = int(m.sum())
    m &= df.STD1RATE >= C.MIN_STD1RATE; a['after_std1rate'] = int(m.sum())
    m &= df.sep_deg <= C.COORD_TOL_DEG; a['after_pointing_simbad'] = int(m.sum())
    att.append(a)
    el = df[m].sort_values('mjd').reset_index(drop=True)
    rows.append(dict(source_id=sid, name=name, aliases=comp, ra_deg=round(ra_s, 4), dec_deg=round(dec_s, 4), label='BH',
                     evidence='Dynamically confirmed BH (Marcel et al. 2026, arXiv:2606.19952, Table 1; '
                              + ('above the high-/low-mass line)' if sid != 'LMCX3' else 'below the high-/low-mass line)'),
                     reference_url=REF, status='confirmed', coord_origin='SIMBAD position (CDS Sesame)', n_eligible=len(el),
                     included=len(el) >= C.MIN_ELIGIBLE, hmxb_above_line=sid != 'LMCX3'))
    if len(el) < C.MIN_ELIGIBLE: print(sid, a, 'DROPPED'); continue
    rng = np.random.default_rng(C.SEED + k)
    for b, idx in enumerate(np.array_split(np.arange(len(el)), C.N_PER_SOURCE)):
        for rank, i in enumerate(rng.permutation(idx)):
            r = el.iloc[i]
            cands.append(dict(obs_id=r.OBSID, source_id=sid, label='BH', time_bin=b, rank_in_bin=rank, mjd=round(float(r.mjd), 5),
                              cat_exposure=float(r.EXPOSURE), cat_npcu=int(r.NPCU), cat_std1rate=float(r.STD1RATE),
                              pointing_sep_deg=round(float(r.sep_deg), 4)))
    print(sid, a, flush=True)
pd.DataFrame(rows).to_csv(D/'sources.csv', index=False)
pd.DataFrame(cands).to_csv(D/'observation_candidates.csv', index=False)
pd.DataFrame(att).to_csv(R/'attrition_catalog.csv', index=False)
print(pd.DataFrame(rows)[['source_id', 'n_eligible', 'included']].to_string(index=False), '\ncandidates:', len(cands))
progress('v7b2_select', f"{sum(r['included'] for r in rows)} persistent BHs, {len(cands)} ranked candidates")
