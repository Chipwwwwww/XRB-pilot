"""Pre-registered analysis choices (fixed BEFORE any model was trained).
Changing anything here after seeing results must be logged in reports/decision_log.md."""

SEED = 42

# ---- Source selection (step 3) ----
# Rule: BH = dynamically confirmed in BlackCAT (Corral-Santana+2016, arXiv:1510.08869);
#       NS = type-I X-ray bursts listed in Galloway+2008 (arXiv:astro-ph/0608259).
#       Both must have >= 30 eligible RXTE/PCA pointings in the gain-epoch window below.
# catalog_name = file name in RXTE MissionLongData
SOURCES = [
    # source_id, catalog_name, display name, aliases, label, evidence, url, status
    ('GROJ1655-40', 'GROJ1655-40', 'GRO J1655-40', 'V1033 Sco; Nova Sco 1994', 'BH',
     'Dynamical mass function; listed in BlackCAT (dynamically confirmed BH)', 'https://arxiv.org/abs/1510.08869', 'confirmed'),
    ('GRS1915+105', 'GRS1915+105', 'GRS 1915+105', 'V1487 Aql', 'BH',
     'Dynamical mass function (IR spectroscopy of K-giant donor); listed in BlackCAT', 'https://arxiv.org/abs/1510.08869', 'confirmed'),
    ('XTEJ1550-564', 'XTEJ1550-564', 'XTE J1550-564', 'V381 Nor', 'BH',
     'Dynamical mass function; listed in BlackCAT', 'https://arxiv.org/abs/1510.08869', 'confirmed'),
    ('4U1543-47', '4U1543-47', '4U 1543-47', '4U 1543-475; IL Lup', 'BH',
     'Dynamical mass function; listed in BlackCAT', 'https://arxiv.org/abs/1510.08869', 'confirmed'),
    ('4U1636-53', '4U1636-53', '4U 1636-53', '4U 1636-536; V801 Ara', 'NS',
     'Type-I X-ray bursts (Galloway+2008 catalogue, sec. A.8)', 'https://arxiv.org/abs/astro-ph/0608259', 'confirmed'),
    ('4U1608-52', '4U1608-52', '4U 1608-52', '4U 1608-522; QX Nor', 'NS',
     'Type-I X-ray bursts (Galloway+2008 catalogue, sec. A.7)', 'https://arxiv.org/abs/astro-ph/0608259', 'confirmed'),
    ('4U1728-34', '4U1728-34', '4U 1728-34', 'GX 354-0; Slow Burster', 'NS',
     'Type-I X-ray bursts (Galloway+2008 catalogue, sec. A.16)', 'https://arxiv.org/abs/astro-ph/0608259', 'confirmed'),
    ('AQLX1', 'AQLX1', 'Aql X-1', 'V1333 Aql; 4U 1908+005', 'NS',
     'Type-I X-ray bursts (Galloway+2008 catalogue, sec. A.44)', 'https://arxiv.org/abs/astro-ph/0608259', 'confirmed'),
]

# ---- Observation eligibility (catalog level, before download) ----
MJD_MIN = 51677.0   # 2000-05-13: PCA gain epoch 5 start; PCU0 dropped from StdProds
MJD_MAX = 54094.0   # 2006-12-25: PCU1 lost propane layer -> dropped from StdProds
MIN_EXPOSURE_S = 1000.0     # catalog EXPOSURE
MIN_STD1RATE = 5.0          # catalog STD1RATE (c/s/PCU), cf. Pattnaik+2021 5 c/s cut
COORD_TOL_DEG = 0.1         # pointing must match the source position

# ---- Observation sampling ----
N_PER_SOURCE = 15           # time-stratified: MJD-sorted eligible list split into 15 equal-count bins,
                            # one random obs per bin (seeded); if it fails a quality rule, next random in bin.

# ---- Energy representation ----
E_MIN, E_MAX = 5.0, 25.0    # keV
REFERENCE_OBS = '91702-01-66-05'  # defines common energy bin edges (its EBOUNDS channels inside 5-25 keV)

# ---- Post-download quality rules ----
MIN_SPEC_EXPOSURE_S = 1000.0
MIN_NET_SNR = 10.0          # net 5-25 keV rate / its statistical error
MAX_DTF = 0.10              # estimated good-xenon deadtime fraction per PCU

# ---- Representations ----
ASINH_SCALE = 0.1           # count/s/keV/PCU; A = asinh(rate/ASINH_SCALE) (log-like, keeps sign)

# ---- Models (fixed hyperparameters, no tuning) ----
LR_PARAMS = dict(C=1.0, penalty='l2', class_weight='balanced', max_iter=5000, solver='lbfgs')
RF_PARAMS = dict(n_estimators=500, max_features='sqrt', min_samples_leaf=2,
                 class_weight='balanced', n_jobs=2, random_state=SEED)
SOURCE_THRESHOLD = 0.5

# =====================================================================================
# v2 (expansion; written 2026-09-29 after v1 results, BEFORE any v2 data were downloaded)
# Activated with environment variable XRB_VERSION=v2. v1 settings above are unchanged.
# =====================================================================================
import os as _os
if _os.environ.get('XRB_VERSION', 'v1') == 'v2':
    _BH = 'https://arxiv.org/abs/1510.08869'
    _NS = 'https://arxiv.org/abs/astro-ph/0608259'
    _bh = lambda sid, cat, name, alias: (sid, cat, name, alias, 'BH',
            'Dynamical mass function listed in BlackCAT Table 4 (dynamically confirmed BH)', _BH, 'confirmed')
    _ns = lambda sid, cat, name, alias, sec: (sid, cat, name, alias, 'NS',
            f'Type-I X-ray bursts (Galloway+2008 catalogue, sec. {sec})', _NS, 'confirmed')
    # Rule: every source satisfying the v1 label rule AND having an RXTE MissionLongData catalogue file.
    # BH: all BlackCAT Table-4 systems with a catalogue file. NS: all Galloway+2008 appendix-A sources with one.
    SOURCES = [
        _bh('GROJ1655-40', 'GROJ1655-40', 'GRO J1655-40', 'V1033 Sco'),
        _bh('GRS1915+105', 'GRS1915+105', 'GRS 1915+105', 'V1487 Aql'),
        _bh('XTEJ1550-564', 'XTEJ1550-564', 'XTE J1550-564', 'V381 Nor'),
        _bh('4U1543-47', '4U1543-47', '4U 1543-47', 'IL Lup'),
        _bh('GX339-4', 'GX339-4', 'GX 339-4', '1H J1659-487; V821 Ara'),
        _bh('XTEJ1650-500', 'XTEJ1650-500', 'XTE J1650-500', ''),
        _bh('XTEJ1118+480', 'XTEJ1118+480', 'XTE J1118+480', 'KV UMa'),
        _bh('XTEJ1859+226', 'XTEJ1859+226', 'XTE J1859+226', 'V406 Vul'),
        _bh('V4641SGR', 'V4641SGR', 'V4641 Sgr', 'SAX J1819.3-2525 (B9III donor: IMXB)'),
        _ns('4U1636-53', '4U1636-53', '4U 1636-53', 'V801 Ara', 'A.8'),
        _ns('4U1608-52', '4U1608-52', '4U 1608-52', 'QX Nor', 'A.7'),
        _ns('4U1728-34', '4U1728-34', '4U 1728-34', 'GX 354-0', 'A.16'),
        _ns('AQLX1', 'AQLX1', 'Aql X-1', 'V1333 Aql', 'A.44'),
        _ns('EXO0748-676', 'EXO0748-676', 'EXO 0748-676', 'UY Vol', 'A.2'),
        _ns('4U1254-690', '4U1254-690', '4U 1254-69', 'XB 1254-690', 'A.5'),
        _ns('4U1323-619', '4U1323-619', '4U 1323-62', '', 'A.6'),
        _ns('MXB1658-298', 'MXB1658-298', 'MXB 1659-298', '', 'A.9'),
        _ns('4U1702-429', '4U1702-429', '4U 1702-429', 'Ara X-1', 'A.10'),
        _ns('4U1705-44', '4U1705-44', '4U 1705-44', '', 'A.11'),
        _ns('4U1724-307', '4U1724-307', '4U 1724-307', 'Terzan 2', 'A.15'),
        _ns('KS1731-260', 'KS1731-260', 'KS 1731-260', '', 'A.18'),
        _ns('SLX1735-269', 'SLX1735-269', 'SLX 1735-269', '', 'A.19'),
        _ns('4U1735-44', '4U1735-44', '4U 1735-44', 'V926 Sco', 'A.20'),
        _ns('GX3+1', 'GX3+1', 'GX 3+1', '', 'A.28'),
        _ns('4U1746-371', '4U1746-371', '4U 1746-37', 'NGC 6441', 'A.32'),
        _ns('SAXJ1808.4-3658', 'SAXJ1808.4-3658', 'SAX J1808.4-3658', 'V4580 Sgr', 'A.36'),
        _ns('XTEJ1814-338', 'XTEJ1814-338', 'XTE J1814-338', '', 'A.37'),
        _ns('GX17+2', 'GX17+2', 'GX 17+2', '', 'A.38'),
        _ns('4U1820-30', '4U1820-30', '4U 1820-30', '3A 1820-303; NGC 6624', 'A.39'),
        _ns('GS1826-238', 'GS1826-238', 'GS 1826-238', 'V4634 Sgr', 'A.40'),
        _ns('HETEJ1900.1-245', 'HETEJ1900.1-245', 'HETE J1900.1-2455', '', 'A.43'),
        _ns('4U1915-05', '4U1915-05', '4U 1916-053', '', 'A.45'),
        _ns('CYGX2', 'CYGX2', 'Cyg X-2', 'V1341 Cyg', 'A.48'),
    ]
    MJD_MAX = 55931.0            # whole gain epoch 5 (to end of mission); PCU0/PCU1 are dropped by StdProds
    MIN_ELIGIBLE = 10            # sources with fewer eligible pointings are dropped (recorded)
    # N_PER_SOURCE = 15 as v1 (if 10-14 eligible: take all of them)
    DEADTIME = 'std1'            # full GOF recipe from Standard-1 (FS46_*): Xe+Vp+Remaining x1e-5, VLE x6e-5, per PCU
    VLE_DT_ALT = 1.5e-4          # sensitivity check only (the GOF page quotes 150 us per VLE in another section)
    N_BOOT = 2000

# =====================================================================================
# v3c (BH candidates; written 2026-09-30 BEFORE any v3c download; see reports/preregistration_v3.md §3)
# Activated with XRB_VERSION=v3c. Same selection/quality/processing rules as v2.
# The candidate list below was drafted from memory of BlackCAT (Corral-Santana+2016) and is NOT yet verified:
# the user must check every entry against https://research.iac.es/proyecto/compactos/BlackCAT/ (BH candidate,
# i.e. no dynamical confirmation) and delete wrong ones BEFORE running 13_v3c_resolve_catalogs.py.
# catalog_name guesses follow the MissionLongData naming seen in v2; names that 404 are logged and skipped.
# =====================================================================================
if _os.environ.get('XRB_VERSION', 'v1') == 'v3c':
    _CAND = 'https://arxiv.org/abs/1510.08869'
    _c = lambda sid, cat, name, alias, note='': (sid, cat, name, alias, 'BH',
            'BlackCAT BH candidate (X-ray properties only, no dynamical mass) ' + note + '[VERIFY]', _CAND, 'candidate')
    V3C_CANDIDATES = [
        _c('H1743-322', 'H1743-322', 'H1743-322', 'IGR J17464-3213'),
        _c('4U1630-47', '4U1630-47', '4U 1630-47', '4U 1630-472'),
        _c('XTEJ1752-223', 'XTEJ1752-223', 'XTE J1752-223', ''),
        _c('XTEJ1817-330', 'XTEJ1817-330', 'XTE J1817-330', ''),
        _c('XTEJ1720-318', 'XTEJ1720-318', 'XTE J1720-318', ''),
        _c('XTEJ1748-288', 'XTEJ1748-288', 'XTE J1748-288', '', '(Galactic-centre field) '),
        _c('MAXIJ1659-152', 'MAXIJ1659-152', 'MAXI J1659-152', ''),
        _c('SWIFTJ1753.5-0127', 'SWIFTJ1753.5-01', 'Swift J1753.5-0127', ''),   # catalog_name fixed from HEASARC listing
        _c('XTEJ1908+094', 'XTEJ1908+094', 'XTE J1908+094', '',
           '(4U 1907+097 is ~0.4 deg away: keep the 0.1 deg pointing check; Garg+2026 pairing error) '),
        _c('IGRJ17091-3624', 'IGRJ17091-3624', 'IGR J17091-3624', ''),
        _c('SLX1746-331', 'SLX1746-331', 'SLX 1746-331', '', '(Galactic-centre field) '),
        _c('GRS1739-278', 'GRS1739-278', 'GRS 1739-278', '', '(Galactic-centre field) '),
        _c('XTEJ1652-453', 'XTEJ1652-453', 'XTE J1652-453', ''),
        _c('GRS1758-258', 'GRS1758-258', 'GRS 1758-258', '', '(persistent; Galactic-centre field) '),
        _c('1E1740.7-2942', '1E1740.7-2942', '1E 1740.7-2942', '', '(persistent; Galactic-centre field) '),
        _c('4U1957+11', '4U1957+11', '4U 1957+11', 'V1408 Aql', '(persistent) '),
    ]
    # only catalogues confirmed to exist by 13_v3c_resolve_catalogs.py are used by 03/04
    _res = __import__('pathlib').Path(__file__).resolve().parents[1] / 'data/v3c/candidate_catalogs.csv'
    if _res.exists():
        import csv as _csv
        _ok = {r['catalog_name'] for r in _csv.DictReader(open(_res, encoding='utf-8')) if r['found'] == 'True'}
        SOURCES = [s for s in V3C_CANDIDATES if s[1] in _ok]
    else:
        SOURCES = V3C_CANDIDATES
    MJD_MAX = 55931.0; MIN_ELIGIBLE = 10; DEADTIME = 'std1'; VLE_DT_ALT = 1.5e-4; N_BOOT = 2000
