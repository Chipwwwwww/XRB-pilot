"""v4b2 step 1 (preregistration_v4.md §4, 3b): verify the source rule over ALL gain epochs by POSITION.
Targets: every Galloway+2008 Table-3 / appendix-A burster (48) and every BlackCAT dynamical BH (Corral-Santana+2016
Table 4/5, 18). Positions from CDS Sesame (SIMBAD); every RXTE MissionLongData catalogue is downloaded and matched if
its median pointing is within COORD_TOL_DEG (0.1 deg). Eligibility (exposure, STD1RATE, pointing) as v2, window = all
gain epochs (MJD < 55931). New sources = not in the v2 sample and >= 10 eligible pointings; 15 time-stratified
candidates each (same algorithm as 03_select_observations.py). Outputs data/v4b2/*."""
import os, sys, json, re, urllib.request, urllib.parse
os.environ['XRB_VERSION'] = 'v4b2'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, ARCHIVE, download, progress, D, R
import config as C
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.table import Table
from concurrent.futures import ThreadPoolExecutor

GALLOWAY = ["4U 0513-40", "EXO 0748-676", "1M 0836-425", "4U 0919-54", "4U 1254-69", "4U 1323-62", "4U 1608-52", "4U 1636-536",
            "MXB 1659-298", "4U 1702-429", "4U 1705-44", "XTE J1709-267", "XTE J1710-281", "XTE J1723-376", "4U 1724-307",
            "4U 1728-34", "MXB 1730-335", "KS 1731-260", "SLX 1735-269", "4U 1735-44", "XTE J1739-285", "KS 1741-293",
            "GRS 1741.9-2853", "2E 1742.9-2929", "SAX J1747.0-2853", "IGR J17473-2721", "SLX 1744-300", "GX 3+1",
            "1A 1744-361", "SAX J1748.9-2021", "EXO 1745-248", "4U 1746-37", "SAX J1750.8-2900", "GRS 1747-312",
            "XTE J1759-220", "SAX J1808.4-3658", "XTE J1814-338", "GX 17+2", "4U 1820-30", "GS 1826-24", "XB 1832-330",
            "Ser X-1", "HETE J1900.1-2455", "Aql X-1", "4U 1916-053", "XTE J2123-058", "4U 2129+12", "Cyg X-2"]
BLACKCAT_DYN = ["Swift J1357.2-0933", "XTE J1650-500", "XTE J1118+480", "XTE J1859+226", "V4641 Sgr", "XTE J1550-564",
                "GRO J1655-40", "GRS 1009-45", "GRS 1915+105", "GRO J0422+32", "GRS 1124-684", "V404 Cyg", "GS 2000+251",
                "BW Cir", "H 1705-250", "A 0620-00", "GX 339-4", "4U 1543-47"]
V2 = pd.read_csv(ROOT/'data/v2/sources.csv')

# 1. every MissionLongData catalogue and its median pointing
_lf = ROOT/'data/raw/catalogs/_missionlongdata_listing.json'
if not _lf.exists():
    _html = urllib.request.urlopen(ARCHIVE + 'MissionLongData/', timeout=120).read().decode(errors='ignore')
    _lf.parent.mkdir(parents=True, exist_ok=True)
    json.dump(sorted(set(re.findall(r'href="([^"]+)\.fits\.gz"', _html))), open(_lf, 'w'))
names = json.load(open(_lf))
json.dump(names, open(D/'missionlongdata_listing.json', 'w'))          # committed copy of the listing used
def cat_info(n):
    p = download(ARCHIVE + 'MissionLongData/' + n + '.fits.gz', 'data/raw/catalogs/' + n + '.fits.gz')
    try:
        with fits.open(p) as h: d = h[1].data
        return n, float(np.nanmedian(np.asarray(d['RA'], float))), float(np.nanmedian(np.asarray(d['DEC'], float))), len(d)
    except Exception as e:
        return n, np.nan, np.nan, 0
with ThreadPoolExecutor(4) as ex: cats = pd.DataFrame(list(ex.map(cat_info, names)), columns=['catalog_name', 'ra', 'dec', 'n_rows'])
cats.to_csv(D/'missionlongdata_positions.csv', index=False)

# 2. positions (CDS Sesame / SIMBAD), cached
PF = D/'source_positions.csv'
pos = pd.read_csv(PF) if PF.exists() else pd.DataFrame(columns=['name', 'ra', 'dec', 'simbad_main_id', 'resolver_url'])
for n in GALLOWAY + BLACKCAT_DYN:
    if n in set(pos.name): continue
    u = 'https://cds.unistra.fr/cgi-bin/nph-sesame/-oI/SNV?' + urllib.parse.quote(n)
    t = urllib.request.urlopen(u, timeout=60).read().decode(errors='ignore')
    j = [l for l in t.splitlines() if l.startswith('%J ')]; i0 = [l for l in t.splitlines() if l.startswith('%I.0')]
    ra, dec = (map(float, j[0].split()[1:3]) if j else (np.nan, np.nan))
    pos = pd.concat([pos, pd.DataFrame([dict(name=n, ra=ra, dec=dec, simbad_main_id=i0[0][5:].strip() if i0 else '', resolver_url=u)])])
pos.to_csv(PF, index=False)

def sep(ra1, dec1, ra2, dec2):
    r = np.radians
    return np.degrees(np.arccos(np.clip(np.sin(r(dec1))*np.sin(r(dec2)) + np.cos(r(dec1))*np.cos(r(dec2))*np.cos(r(ra1-ra2)), -1, 1)))

# 3. match, 4. eligibility over all epochs
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
for n in GALLOWAY + BLACKCAT_DYN:
    lab = 'NS' if n in GALLOWAY else 'BH'
    p = pos[pos.name == n].iloc[0]
    d = sep(cats.ra.values, cats.dec.values, p.ra, p.dec)
    m = cats[(d <= C.COORD_TOL_DEG) & (cats.n_rows > 0)].assign(sep=d[(d <= C.COORD_TOL_DEG) & (cats.n_rows > 0)]).sort_values('n_rows', ascending=False)
    rec = dict(name=n, label=lab, simbad_ra=p.ra, simbad_dec=p.dec, simbad_main_id=p.simbad_main_id,
               matched_catalogs=';'.join(f'{a} ({s:.3f} deg, {k} rows)' for a, s, k in zip(m.catalog_name, m.sep, m.n_rows)))
    if len(m):
        cat = m.catalog_name.iloc[0]; el, ra0, dec0 = eligibility(cat)
        # compare by POSITION: any catalogue matching this source that is already a v2 source counts (e.g. 4U/XB 1254-690)
        v2hit = [a for a in m.catalog_name if a in set(V2.source_id)]
        in_v2 = len(v2hit) > 0
        rec.update(catalog_name=cat, eligible_epoch5=int((el.epoch == 5).sum()), eligible_all=len(el),
                   eligible_by_epoch=json.dumps(el.epoch.value_counts().sort_index().to_dict()),
                   v2_catalog=';'.join(v2hit), in_v2_list=in_v2,
                   in_v2_sample=bool(in_v2 and V2.set_index('source_id').loc[v2hit, 'included'].any()))
        if not rec['in_v2_sample'] and len(el) >= C.MIN_ELIGIBLE:
            rec['v4b2_new_source'] = True; new.append((cat, n, lab, el, ra0, dec0))
    rows.append(rec)
ver = pd.DataFrame(rows); ver.to_csv(D/'source_verification.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 90)
print(ver[['name', 'label', 'catalog_name', 'eligible_epoch5', 'eligible_all', 'in_v2_list', 'in_v2_sample', 'v4b2_new_source']].to_string())

# 5. candidates for new sources (03 algorithm: MJD-sorted eligible list, 15 equal-count bins, seeded permutation per bin)
srows, cands = [], []
for i, (cat, n, lab, el, ra0, dec0) in enumerate(sorted(new, key=lambda t: (t[2], t[0]))):
    ev = ('Dynamical BH in BlackCAT (Corral-Santana+2016 Table 4/5)' if lab == 'BH'
          else 'Type-I X-ray bursts (Galloway+2008 Table 3 / appendix A)')
    srows.append(dict(source_id=cat, name=n, aliases='', ra_deg=round(ra0, 4), dec_deg=round(dec0, 4), label=lab, evidence=ev,
                      reference_url='https://arxiv.org/abs/1510.08869' if lab == 'BH' else 'https://arxiv.org/abs/astro-ph/0608259',
                      status='confirmed', coord_origin='median pointing of RXTE MissionLongData catalogue',
                      n_eligible=len(el), included=True))
    rng = np.random.default_rng(C.SEED + 100 + i)
    for b, idx in enumerate(np.array_split(np.arange(len(el)), C.N_PER_SOURCE)):
        for rank, j in enumerate(rng.permutation(idx)):
            r = el.iloc[j]
            cands.append(dict(obs_id=r.OBSID, source_id=cat, label=lab, time_bin=b, rank_in_bin=rank, mjd=round(float(r.mjd), 5),
                              cat_exposure=float(r.EXPOSURE), cat_npcu=int(r.NPCU), cat_std1rate=float(r.STD1RATE),
                              pointing_sep_deg=round(float(r.sep_deg), 4), epoch=int(r.epoch)))
pd.DataFrame(srows).to_csv(D/'sources.csv', index=False)
pd.DataFrame(cands).to_csv(D/'observation_candidates.csv', index=False)
print('\nnew sources:', [(s['source_id'], s['label'], s['n_eligible']) for s in srows])
print('candidates:', len(cands), '; first-choice observations to download:', sum(c['rank_in_bin'] == 0 for c in cands))
progress('v4b2_select', f"{len(srows)} new sources ({sum(s['label']=='BH' for s in srows)} BH) with >=10 eligible pointings over all epochs")
