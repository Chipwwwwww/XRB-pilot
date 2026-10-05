"""v7c2 step 1 (preregistration_v7.md §6, 4c): freeze the C2 label list and match it to MAXI/GSC standard products,
then download the 1-day light curves and apply the de Beurs et al. 2022 cuts.
BH   : dynamically confirmed, Marcel et al. 2026 (arXiv:2606.19952) Table 1 (25 systems).
NPNS : MINBAR DR1 burst sources (type-I bursts; official source table, 115) without a pulse period
       (Liu+2007 LMXB catalogue Ppulse, Patruno & Watts 2021 Table 1).
PSR  : secondary only: sources with a pulse period in Liu+2006 (HMXB) or Liu+2007 (LMXB), or in Patruno & Watts Table 1.
Matching: positions (CDS Sesame / MINBAR / Liu) to the MAXI J-name position (RA hhmm, Dec +-dd.d) within 0.35 deg;
a MAXI source matched by sources of different classes or by several label sources is excluded (ambiguous).
Cuts (de Beurs 2022 sec. 2.1): every band >= sqrt(3) sigma (sum >= 3 sigma), drop points >= 10 sigma above the mean of the
summed light curve, keep sources with >= 100 points. Outputs data/v7c/c2_sources.csv, data/v7c/maxi_points.csv."""
import os, sys, re, html, urllib.request, urllib.parse
os.environ['XRB_VERSION'] = 'v7c'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, download, progress
import numpy as np, pandas as pd
from astropy.table import Table
import warnings
import config as C
import v7lib as L7

D7, R7 = ROOT/'data/v7c', ROOT/'results/v7c'
warnings.filterwarnings('ignore')
TOL = 0.35
MARCEL = ['M33 X-7', 'Cyg X-1', 'LMC X-1', 'SS 433', 'LMC X-3', 'SAX J1819.3-2525', '4U 1543-475', 'GRO J1655-40', 'GRO J0422+32',
          'GRS 1124-684', 'GX 339-4', 'GS 1354-64', 'Swift J1727.8-1613', 'XTE J1650-500', 'GS 2023+338', 'MAXI J1820+070',
          'XTE J1859+226', 'GRS 1915+105', 'V616 Mon', 'MAXI J1305-704', 'H 1705-250', 'XTE J1550-564', 'GS 2000+25', 'GRS 1009-45',
          'XTE J1118+480']
PW21 = ['SAX J1808.4-3658', 'XTE J1751-305', 'XTE J0929-314', 'XTE J1807-294', 'XTE J1814-338', 'IGR J00291+5934', 'HETE J1900.1-2455',
        'Swift J1756.9-2508', 'Aql X-1', 'SAX J1748.9-2021', 'IGR J17511-3057', 'Swift J1749.4-2807', 'IGR J17498-2921',
        'IGR J18245-2452', 'IGR J17480-2446', '2A 1822-371', '4U 1626-67', 'GRO J1744-28', 'Her X-1', 'GX 1+4', '4U 1954+31', 'IGR J16358-4726']
# name fixes (before any C2 model): A 0620-00 resolved as V616 Mon; P&W Table 1 spellings IGR J17480-2466 / IGR J16358-4724
# are not resolved by Sesame -> SIMBAD names IGR J17480-2446 (Terzan 5, 11 Hz pulsar) / IGR J16358-4726


def sesame(names, cache):
    pos = pd.read_csv(cache) if cache.exists() else pd.DataFrame(columns=['name', 'ra', 'dec', 'resolver_url'])
    for n in names:
        if n in set(pos.name): continue
        u = 'https://cds.unistra.fr/cgi-bin/nph-sesame/-oI/SNV?' + urllib.parse.quote(n)
        try: t = urllib.request.urlopen(u, timeout=60).read().decode(errors='ignore')
        except Exception: t = ''
        j = [l for l in t.splitlines() if l.startswith('%J ')]
        ra, dec = (map(float, j[0].split()[1:3]) if j else (np.nan, np.nan))
        pos = pd.concat([pos, pd.DataFrame([dict(name=n, ra=ra, dec=dec, resolver_url=u)])], ignore_index=True)
    pos.to_csv(cache, index=False); return pos.set_index('name')


# ---------------- MAXI source index (all category pages) ----------------
rows = []
for cat in ['agn', 'bh', 'ci', 'clst', 'els', 'gal', 'gc', 'ns', 'nsbh', 'pls', 'snr', 'str', 'wd']:
    p = download(f'http://maxi.riken.jp/top/lc_{cat}.html', f'data/raw/maxi/index/lc_{cat}.html')
    t = p.read_text(encoding='utf-8', errors='ignore')
    for name, j in re.findall(r'([^<>\n]+?)\s*<br>\s*<a href="\.\./star_data/([^/]+)/\2\.html">', t):
        m = re.match(r'J(\d\d)(\d\d)([+-])(\d\d)(\d)', j)
        if not m: continue
        ra = (int(m.group(1)) + int(m.group(2)) / 60) * 15; dec = (1 if m.group(3) == '+' else -1) * (int(m.group(4)) + int(m.group(5)) / 10)
        rows.append(dict(maxi_name=html.unescape(name).strip(), maxi_id=j, maxi_category=cat, ra_j=ra, dec_j=dec))
mx = pd.DataFrame(rows).drop_duplicates('maxi_id').reset_index(drop=True)
mx['blend'] = mx.maxi_name.str.contains(' with ')                # MAXI light curve of two sources -> excluded
mpos = sesame(sorted(set(mx[~mx.blend].maxi_name)), D7/'sesame_maxi_names.csv')
mx['ra'] = mx.maxi_name.map(mpos.ra); mx['dec'] = mx.maxi_name.map(mpos.dec)
mx['pos_origin'] = np.where(mx.ra.notna(), 'sesame(maxi_name)', 'J-name'); mx['tol'] = np.where(mx.ra.notna(), 0.1, 0.3)
mx['ra'] = mx.ra.fillna(mx.ra_j); mx['dec'] = mx.dec.fillna(mx.dec_j)
mx = mx[~mx.blend].reset_index(drop=True)
mx.to_csv(D7/'maxi_index.csv', index=False); print(len(mx), 'MAXI sources indexed', flush=True)

# ---------------- label sources ----------------
liu_h = download('https://cdsarc.cds.unistra.fr/ftp/J/A+A/455/1165/table1.dat', 'data/raw/catalogs_liu/J_A+A_455_1165/table1.dat')
liu_hr = download('https://cdsarc.cds.unistra.fr/ftp/J/A+A/455/1165/ReadMe', 'data/raw/catalogs_liu/J_A+A_455_1165/ReadMe')
liu_l = download('https://cdsarc.cds.unistra.fr/ftp/J/A+A/469/807/lmxb.dat', 'data/raw/catalogs_liu/J_A+A_469_807/lmxb.dat')
liu_lr = download('https://cdsarc.cds.unistra.fr/ftp/J/A+A/469/807/ReadMe', 'data/raw/catalogs_liu/J_A+A_469_807/ReadMe')


def liu(path, readme, tab):
    from astropy.io import ascii as _ascii
    t = _ascii.read(str(path), format='cds', readme=str(readme))
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    cols = t.colnames
    ra = (np.asarray(t['RAh'], float) + np.asarray(t['RAm'], float) / 60 + np.asarray(t['RAs'], float) / 3600) * 15
    sgn = np.where(np.asarray(t['DE-']).astype(str) == '-', -1, 1)
    dec = sgn * (np.asarray(t['DEd'], float) + np.asarray(t['DEm'], float) / 60 + np.asarray(t['DEs'] if 'DEs' in cols else np.zeros(len(t)), float) / 3600)
    pp = np.asarray(t['Ppulse'].filled(np.nan) if hasattr(t['Ppulse'], 'filled') else t['Ppulse'], float)
    name = [str(x).strip() for x in t[cols[0]]]
    return pd.DataFrame(dict(name=name, ra=ra, dec=dec, Ppulse=pp))


lh = liu(liu_h, liu_hr, 'table1.dat')
# HMXB pulse periods are accretion-powered spin periods; Liu+2007 LMXB 'Ppulse' also lists burst-oscillation periods
# (nuclear-powered, e.g. 4U 1608-52, 4U 1636-536) -> LMXB pulsars only from Patruno & Watts 2021 Table 1 (accretion-powered)
psr_liu = lh[np.isfinite(lh.Ppulse)].assign(src='Liu+2006 HMXB Ppulse')
pos = sesame(MARCEL + PW21, D7/'sesame_positions.csv')
ms = L7.load_minbar_sources()
lab = []
for n in MARCEL: lab.append(dict(name=n, cls='BH', ra=pos.loc[n].ra, dec=pos.loc[n].dec, evidence='Marcel+2026 Table 1 (dynamical)'))
for n in PW21: lab.append(dict(name=n, cls='PSR', ra=pos.loc[n].ra, dec=pos.loc[n].dec, evidence='Patruno & Watts 2021 Table 1'))
for r in psr_liu.itertuples(): lab.append(dict(name=r.name, cls='PSR', ra=r.ra, dec=r.dec, evidence=f'{r.src} = {r.Ppulse:g} s'))
psr_all = pd.DataFrame([x for x in lab if x['cls'] == 'PSR'])
for n, r in ms.iterrows():
    d = L7.sep_deg(psr_all.ra.values, psr_all.dec.values, r.ra, r.dec)
    if np.nanmin(d) <= 0.1: continue                                   # bursting pulsar -> not NPNS
    lab.append(dict(name=n, cls='NPNS', ra=r.ra, dec=r.dec, evidence='MINBAR DR1 burst source (type-I bursts), no pulse period'))
lab = pd.DataFrame(lab).dropna(subset=['ra'])
lab = lab.drop_duplicates(subset=['cls', 'name'])
# merge PSR duplicates (same object from several lists) by position
lab['maxi_id'] = None; lab['match_sep_deg'] = np.nan
for i, r in lab.iterrows():
    d = L7.sep_deg(mx.ra.values, mx.dec.values, r.ra, r.dec); k = int(np.nanargmin(d))
    if d[k] <= mx.tol[k]: lab.loc[i, 'maxi_id'] = mx.maxi_id[k]; lab.loc[i, 'match_sep_deg'] = d[k]
m = lab.dropna(subset=['maxi_id'])
per_id = m.groupby('maxi_id').agg(classes=('cls', lambda s: ','.join(sorted(set(s)))), names=('name', lambda s: ';'.join(sorted(set(s)))))
# several names for one object (aliases) are fine if they are within 0.1 deg of each other and share the class
def unique_object(g):
    if g.cls.nunique() > 1: return False
    return float(np.nanmax([L7.sep_deg(a.ra, a.dec, b.ra, b.dec) for _, a in g.iterrows() for _, b in g.iterrows()])) <= 0.1
ok = m.groupby('maxi_id').apply(unique_object)
sel = m[m.maxi_id.isin(ok[ok].index)].sort_values('match_sep_deg').drop_duplicates('maxi_id')
amb = m[m.maxi_id.isin(ok[~ok].index)]
sel = sel.merge(mx[['maxi_id', 'maxi_name', 'maxi_category', 'pos_origin']], on='maxi_id')
sel.to_csv(D7/'c2_sources_matched.csv', index=False); amb.to_csv(D7/'c2_sources_ambiguous.csv', index=False)
print('matched:', sel.cls.value_counts().to_dict(), '| ambiguous MAXI ids:', amb.maxi_id.nunique(), flush=True)
print(amb[['name', 'cls', 'maxi_id']].to_string(index=False))

# ---------------- download + cuts ----------------
pts, rows = [], []
for r in sel.itertuples():
    p = download(C.V7_MAXI_URL.format(j=r.maxi_id), f'data/raw/maxi/{r.maxi_id}_g_lc_1day_all.dat')
    d = pd.read_csv(p, sep=r'\s+', header=None, names=['mjd', 'f', 'e', 'L', 'eL', 'M', 'eM', 'H', 'eH'])
    n0 = len(d)
    ok3 = (d.L / d.eL >= np.sqrt(3)) & (d.M / d.eM >= np.sqrt(3)) & (d.H / d.eH >= np.sqrt(3))
    d = d[ok3 & (d.eL > 0) & (d.eM > 0) & (d.eH > 0)]
    tot = d.L + d.M + d.H
    d = d[tot < tot.mean() + C.V7_MAXI_OUTLIER_SIGMA * tot.std()] if len(d) > 1 else d
    rows.append(dict(name=r.name, cls=r.cls, maxi_id=r.maxi_id, maxi_name=r.maxi_name, n_points_raw=n0, n_points_cut=len(d),
                     included=len(d) >= C.V7_MAXI_MIN_POINTS, evidence=r.evidence, match_sep_deg=r.match_sep_deg))
    if len(d) >= C.V7_MAXI_MIN_POINTS: pts.append(d.assign(source=r.maxi_id, name=r.name, cls=r.cls))
src = pd.DataFrame(rows); src.to_csv(D7/'c2_sources.csv', index=False)
pd.concat(pts).to_csv(D7/'maxi_points.csv', index=False)
print(src[src.included].groupby('cls').name.apply(list).to_string())
print(src.groupby('cls').included.agg(['sum', 'size']).to_string())
progress('v7c2_select', f"C2 sources with >=100 MAXI points: {src[src.included].cls.value_counts().to_dict()}")
