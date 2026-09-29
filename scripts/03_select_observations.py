"""Step 3a: source table + pre-registered, time-stratified candidate list (no spectra used)."""
from common import *
from config import *
from astropy.io import fits
from astropy.table import Table
import numpy as np, pandas as pd

rows, cands, attrition = [], [], []
for sid, cat, name, alias, label, ev, url, status in SOURCES:
    p = download(ARCHIVE + 'MissionLongData/' + cat + '.fits.gz', 'data/raw/catalogs/' + cat + '.fits.gz')
    with fits.open(p) as h:
        df = Table(h[1].data).to_pandas()
        hdr = h[1].header
    df['OBSID'] = [v.decode().strip() if isinstance(v, bytes) else str(v).strip() for v in df.OBSID]
    df['mjd'] = df.TIME.astype(float) + hdr['MJDREFI'] + hdr['MJDREFF']
    df["RA"] = df.RA.astype(float); df["DEC"] = df.DEC.astype(float)
    ra0, dec0 = float(np.nanmedian(df.RA)), float(np.nanmedian(df.DEC))
    rows.append(dict(source_id=sid, name=name, aliases=alias, ra_deg=round(ra0, 4), dec_deg=round(dec0, 4),
                     label=label, evidence=ev, reference_url=url, status=status,
                     coord_origin='median pointing of RXTE MissionLongData catalogue'))
    n0 = len(df)
    dup = df.OBSID.duplicated(keep='first'); df = df[~dup]
    sep = np.degrees(np.arccos(np.clip(np.sin(np.radians(df.DEC))*np.sin(np.radians(dec0)) +
          np.cos(np.radians(df.DEC))*np.cos(np.radians(dec0))*np.cos(np.radians(df.RA-ra0)), -1, 1)))
    df['sep_deg'] = sep
    m_time = (df.mjd >= MJD_MIN) & (df.mjd < MJD_MAX)
    m_exp = df.EXPOSURE >= MIN_EXPOSURE_S
    m_rate = df.STD1RATE >= MIN_STD1RATE
    m_pos = sep <= COORD_TOL_DEG
    a = dict(source_id=sid, catalog_rows=n0, after_dedup=len(df))
    m = m_time; a['after_epoch5_window'] = int(m.sum())
    m = m & m_exp; a['after_exposure'] = int(m.sum())
    m = m & m_rate; a['after_std1rate'] = int(m.sum())
    m = m & m_pos; a['after_pointing'] = int(m.sum())
    attrition.append(a)
    el = df[m].sort_values('mjd').reset_index(drop=True)
    rng = np.random.default_rng(SEED + len(rows))
    bins = np.array_split(np.arange(len(el)), N_PER_SOURCE)
    for b, idx in enumerate(bins):
        for rank, i in enumerate(rng.permutation(idx)):
            r = el.iloc[i]
            cands.append(dict(obs_id=r.OBSID, source_id=sid, label=label, time_bin=b, rank_in_bin=rank,
                              mjd=round(float(r.mjd), 5), cat_exposure=float(r.EXPOSURE), cat_npcu=int(r.NPCU),
                              cat_std1rate=float(r.STD1RATE), pointing_sep_deg=round(float(r.sep_deg), 4)))
    print(sid, a, flush=True)

pd.DataFrame(rows).to_csv(ROOT/'data/sources.csv', index=False)
c = pd.DataFrame(cands)
c.to_csv(ROOT/'data/observation_candidates.csv', index=False)
pd.DataFrame(attrition).to_csv(ROOT/'results/attrition_catalog.csv', index=False)
progress('3a_selection', f'sources.csv ({len(rows)}) and {len(c)} ranked candidates written')
