"""v6 step 1 (preregistration_v6.md §2): external (held-out) confirmed sources, verified by POSITION.
BH: dynamical BHs in HMXBs, Casares & Jonker 2014 (SSRv 183, 223) sec. 3 / Table 2.
NS: AMXPs in Patruno & Watts 2021 (arXiv:1206.2727) Table 1 not already used; stress set: its slow LMXB/IMXB pulsars.
Positions from CDS Sesame; RXTE MissionLongData catalogue median pointing within COORD_TOL_DEG; sources within
COORD_TOL_DEG of any v2 / v4b2 source (same field) or sharing its catalogue are excluded. Eligibility as v4b2
(all gain epochs); >= MIN_ELIGIBLE -> 15 time-stratified candidates (03 algorithm). Outputs data/v6/*."""
import os, sys, json, urllib.request, urllib.parse
os.environ['XRB_VERSION'] = 'v6'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress, D
import config as C
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.table import Table

D.mkdir(parents=True, exist_ok=True)
CJ14 = 'Casares & Jonker 2014, SSRv 183, 223, sec. 3 / Table 2 (dynamical BH in HMXB)'
PW21 = 'Patruno & Watts 2021, arXiv:1206.2727, Table 1'
TARGETS = ([(n, 'BH', 'E_new', CJ14, 'https://arxiv.org/abs/1311.5118') for n in ('Cyg X-1', 'LMC X-1', 'LMC X-3', 'M33 X-7')] +
           [(n, 'NS', 'E_new', f'{PW21} (accreting millisecond X-ray pulsar)', 'https://arxiv.org/abs/1206.2727') for n in
            ('XTE J1751-305', 'XTE J0929-314', 'XTE J1807-294', 'IGR J00291+5934', 'Swift J1756.9-2508', 'NGC 6440 X-2',
             'IGR J17511-3057', 'Swift J1749.4-2807', 'IGR J17498-2921', 'IGR J18245-2452')] +
           [(n, 'NS', 'stress_slow_pulsar', f'{PW21} (slow X-ray pulsar in LMXB/IMXB)', 'https://arxiv.org/abs/1206.2727') for n in
            ('2A 1822-371', '4U 1626-67', 'GRO J1744-28', 'Her X-1')])
cats = pd.read_csv(ROOT/'data/v4b2/missionlongdata_positions.csv')          # all MissionLongData catalogues (v4b2)
known = pd.concat([pd.read_csv(ROOT/'data/v2/sources.csv'), pd.read_csv(ROOT/'data/v4b2/sources.csv')])
known = known[known.included.astype(str).str.lower().eq('true')]


def sep(ra1, dec1, ra2, dec2):
    r = np.radians
    return np.degrees(np.arccos(np.clip(np.sin(r(dec1))*np.sin(r(dec2)) + np.cos(r(dec1))*np.cos(r(dec2))*np.cos(r(ra1-ra2)), -1, 1)))


PF = D/'source_positions.csv'
pos = pd.read_csv(PF) if PF.exists() else pd.DataFrame(columns=['name', 'ra', 'dec', 'simbad_main_id', 'resolver_url'])
for n, *_ in TARGETS:
    if n in set(pos.name): continue
    u = 'https://cds.unistra.fr/cgi-bin/nph-sesame/-oI/SNV?' + urllib.parse.quote(n)
    t = urllib.request.urlopen(u, timeout=60).read().decode(errors='ignore')
    j = [l for l in t.splitlines() if l.startswith('%J ')]; i0 = [l for l in t.splitlines() if l.startswith('%I.0')]
    ra, dec = (map(float, j[0].split()[1:3]) if j else (np.nan, np.nan))
    pos = pd.concat([pos, pd.DataFrame([dict(name=n, ra=ra, dec=dec, simbad_main_id=i0[0][5:].strip() if i0 else '', resolver_url=u)])])
pos.to_csv(PF, index=False)


def eligibility(cat):
    with fits.open(ROOT/'data/raw/catalogs'/f'{cat}.fits.gz') as h:
        df = Table(h[1].data).to_pandas(); hdr = h[1].header
    df['OBSID'] = [v.decode().strip() if isinstance(v, bytes) else str(v).strip() for v in df.OBSID]
    df = df[~df.OBSID.duplicated(keep='first')].copy()
    df['mjd'] = df.TIME.astype(float) + hdr['MJDREFI'] + hdr['MJDREFF']
    df['RA'] = df.RA.astype(float); df['DEC'] = df.DEC.astype(float)
    ra0, dec0 = float(np.nanmedian(df.RA)), float(np.nanmedian(df.DEC))
    df['sep_deg'] = sep(df.RA, df.DEC, ra0, dec0)
    ok = (df.EXPOSURE >= C.MIN_EXPOSURE_S) & (df.STD1RATE >= C.MIN_STD1RATE) & (df.sep_deg <= C.COORD_TOL_DEG) & (df.mjd < C.MJD_MAX)
    el = df[ok].sort_values('mjd').reset_index(drop=True)
    el['epoch'] = np.searchsorted([C.V4_EPOCH_STOP_MJD[k] for k in (1, 2, 3, 4)], el.mjd.values, side='right') + 1
    return el, ra0, dec0


rows, new = [], []
for n, lab, role, ev, url in TARGETS:
    p = pos[pos.name == n].iloc[0]
    rec = dict(name=n, label=lab, role=role, evidence=ev, simbad_ra=p.ra, simbad_dec=p.dec, simbad_main_id=p.simbad_main_id)
    if not np.isfinite(p.ra):
        rec.update(decision='excluded: name not resolved by Sesame'); rows.append(rec); continue
    dk = sep(known.ra_deg.values, known.dec_deg.values, p.ra, p.dec)
    d = sep(cats.ra.values, cats.dec.values, p.ra, p.dec)
    m = cats[(d <= C.COORD_TOL_DEG) & (cats.n_rows > 0)].assign(sep=d[(d <= C.COORD_TOL_DEG) & (cats.n_rows > 0)]).sort_values('n_rows', ascending=False)
    rec['matched_catalogs'] = ';'.join(f'{a} ({s:.3f} deg, {k} rows)' for a, s, k in zip(m.catalog_name, m.sep, m.n_rows))
    rec['nearest_known_source'] = f'{known.source_id.values[dk.argmin()]} ({dk.min():.3f} deg)'
    if dk.min() <= C.COORD_TOL_DEG or any(a in set(known.source_id) for a in m.catalog_name):
        rec.update(decision='excluded: same field as a v2/v4b2 source'); rows.append(rec); continue
    if not len(m):
        rec.update(decision='excluded: no RXTE MissionLongData catalogue within 0.1 deg'); rows.append(rec); continue
    cat = m.catalog_name.iloc[0]; el, ra0, dec0 = eligibility(cat)
    rec.update(catalog_name=cat, eligible_all=len(el), eligible_by_epoch=json.dumps(el.epoch.value_counts().sort_index().to_dict()))
    if len(el) < C.MIN_ELIGIBLE:
        rec.update(decision=f'excluded: {len(el)} eligible pointings (< {C.MIN_ELIGIBLE})'); rows.append(rec); continue
    rec.update(decision='included'); rows.append(rec); new.append((cat, n, lab, role, ev, url, el, ra0, dec0))
ver = pd.DataFrame(rows); ver.to_csv(D/'source_verification.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 80)
print(ver[['name', 'label', 'role', 'catalog_name', 'eligible_all', 'nearest_known_source', 'decision']].to_string())

srows, cands = [], []
for i, (cat, n, lab, role, ev, url, el, ra0, dec0) in enumerate(sorted(new, key=lambda t: (t[3], t[2], t[0]))):
    srows.append(dict(source_id=cat, name=n, aliases='', ra_deg=round(ra0, 4), dec_deg=round(dec0, 4), label=lab, evidence=ev,
                      reference_url=url, status='confirmed', coord_origin='median pointing of RXTE MissionLongData catalogue',
                      n_eligible=len(el), included=True, role=role))
    rng = np.random.default_rng(C.SEED + 200 + i)
    for b, idx in enumerate(np.array_split(np.arange(len(el)), min(C.N_PER_SOURCE, len(el)))):
        for rank, j in enumerate(rng.permutation(idx)):
            r = el.iloc[j]
            cands.append(dict(obs_id=r.OBSID, source_id=cat, label=lab, time_bin=b, rank_in_bin=rank, mjd=round(float(r.mjd), 5),
                              cat_exposure=float(r.EXPOSURE), cat_npcu=int(r.NPCU), cat_std1rate=float(r.STD1RATE),
                              pointing_sep_deg=round(float(r.sep_deg), 4), epoch=int(r.epoch)))
pd.DataFrame(srows).to_csv(D/'sources.csv', index=False)
pd.DataFrame(cands).to_csv(D/'observation_candidates.csv', index=False)
print('\nincluded:', [(s['source_id'], s['label'], s['role'], s['n_eligible']) for s in srows])
print('candidates:', len(cands), '; first-choice observations:', sum(c['rank_in_bin'] == 0 for c in cands))
progress('v6_select', f"{len(srows)} external sources ({sum(s['label']=='BH' for s in srows)} BH; "
         f"{sum(s['role']=='stress_slow_pulsar' for s in srows)} stress-set pulsars)")
