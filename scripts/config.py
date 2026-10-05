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

# =====================================================================================
# v4 (written 2026-09-30 AFTER all v1-v3 results, BEFORE any v4 training or download;
# see reports/preregistration_v4.md). Active only for XRB_VERSION in {v4, v4b1, v4b2, v4b3}.
# v1-v3 settings above are untouched.
# =====================================================================================
if _os.environ.get('XRB_VERSION', 'v1').startswith(('v4', 'v5', 'v6', 'v7', 'v8', 'v9')):     # v5-v9 re-use the v4 settings (v4lib)
    N_BOOT = 2000; DEADTIME = 'std1'; VLE_DT_ALT = 1.5e-4
    V4_REPRESENTATIONS = ['H_colours', 'HI_colours_intensity', 'B_shape', 'A_intensity']   # via v3lib.v2_representations
    V4_BASELINE = ('H_colours', 'LogReg')      # v2 OOF in results/v2/oof_predictions_loso.csv, threshold 0.5
    V4_MLP_SEEDS_OUTER = [0, 1, 2, 3, 4]; V4_MLP_SEEDS_INNER = [0, 1, 2]
    # 1b fixed-hyperparameter models (class imbalance handling per preregistration table)
    V4_FIXED = {
        'ExtraTrees': dict(n_estimators=500, max_features='sqrt', min_samples_leaf=2, class_weight='balanced', random_state=SEED),
        'HistGB': dict(learning_rate=0.1, max_iter=200, max_leaf_nodes=15, min_samples_leaf=20, l2_regularization=0.0,
                       early_stopping=False, class_weight='balanced', random_state=SEED),
        'SVM_RBF': dict(C=1.0, gamma='scale', kernel='rbf', class_weight='balanced'),     # score = sigmoid(decision_function)
        'kNN': dict(n_neighbors=15, weights='uniform'),                                   # prior-corrected to equal classes
        'QDA': dict(reg_param=0.1, priors=[0.5, 0.5]),
        'MLP': dict(hidden_layer_sizes=(32,), alpha=1e-3, early_stopping=True, validation_fraction=0.2, max_iter=500),
    }
    V4_SOURCE_WEIGHTED_MODELS = ['LogReg', 'RandomForest', 'HistGB']                     # 1c
    # 1d/1e nested grids (inner LOSO on the 30 training sources)
    V4_GRID = {
        'LogReg': [dict(C=c) for c in (0.01, 0.1, 1.0, 10.0)],
        'RandomForest': [dict(min_samples_leaf=m) for m in (1, 2, 5, 10)],               # inner 200 trees, outer 500
        'ExtraTrees': [dict(min_samples_leaf=m) for m in (1, 2, 5, 10)],                 # inner 200 trees, outer 500
        'HistGB': [dict(learning_rate=lr, max_leaf_nodes=n) for lr in (0.05, 0.1) for n in (7, 15)],
        'SVM_RBF': [dict(C=c, gamma_factor=g) for c in (0.1, 1.0, 10.0) for g in (0.3, 1.0, 3.0)],   # gamma = factor * 'scale'
        'kNN': [dict(n_neighbors=k) for k in (5, 15, 31)],
        'QDA': [dict(reg_param=r) for r in (0.01, 0.1, 0.5)],
        'MLP': [dict(hidden_layer_sizes=h, alpha=a) for h in ((16,), (32, 16)) for a in (1e-4, 1e-2)],
    }
    V4_INNER_TREES, V4_OUTER_TREES = 200, 500
    # burst detection (Galloway+2008 sec. 2: 1-s bins > mean + 4 sigma, then shape rules)
    V4_BURST = dict(bin_s=1.0, nsigma=4.0, merge_gap_s=30.0, pre_window_s=60.0, min_peak_ratio=1.5,
                    max_rise_s=10.0, decay_half_min_s=3.0, decay_half_max_s=300.0, min_bins_above_25pct=3)
    # v4b3 HEXTE (cluster B only; no HEXTE features on/after cluster B stopped rocking)
    V4_HEXTE_CLUSTER = 1
    V4_HEXTE_LAST_MJD = 55179.6736          # 2009-12-14 16:10 UT, HEASARC RXTE news archive 2010
    V4_HEXTE_BANDS = dict(X_25_40=(25.0, 40.0), X_40_60=(40.0, 60.0))
    V4_HEXTE_MIN_DEN_SNR = 3.0              # colour set to missing (train-fold median + indicator) below this
    V4_OVERLAP_BOX = dict(c1_min=0.70, c2_min=0.20)   # post-hoc box on the v2 H plane (declared as such)
    # v4b2 gain epochs (HEASARC Energy-Channel Conversion Table; stop times, converted with astropy)
    V4_EPOCH_STOP_MJD = {1: 50163.7729, 2: 50188.9618, 3: 51259.7340, 4: 51677.0000}
    V4_R_GAMMA, V4_R_NH = 2.0, 0.0
    V4_BRIDGE_MIN_SPEARMAN = 0.90
    _v = _os.environ.get('XRB_VERSION')
    if _v in ('v4b1', 'v4b2'):
        # same source list as v2 (realised table data/v2/sources.csv); v4b2 re-checks Galloway+2008 NS before download
        import csv as _csv
        _src = __import__('pathlib').Path(__file__).resolve().parents[1] / 'data/v2/sources.csv'
        SOURCES = [(r['source_id'], r['source_id'], r['name'], r['aliases'], r['label'], r['evidence'],
                    r['reference_url'], r['status']) for r in _csv.DictReader(open(_src, encoding='utf-8'))]
        MIN_ELIGIBLE = 10
        MJD_MAX = 55931.0
        if _v == 'v4b1':
            N_PER_SOURCE = 'all'          # every eligible epoch-5 pointing (new selection script, not 03)
        else:
            MJD_MIN = 0.0                 # all gain epochs

# =====================================================================================
# v5 (written 2026-10-01 AFTER all v1-v4 results, BEFORE any v5 feature or model; see reports/preregistration_v5.md).
# Active only for XRB_VERSION starting with v5 (the v4 block above is also active). v1-v4 behaviour is unchanged.
# =====================================================================================
if _os.environ.get('XRB_VERSION', 'v1').startswith(('v5', 'v6', 'v7', 'v8', 'v9')):     # v6-v9 re-use the v5 timing settings (v5lib)
    V5_N_BINS, V5_DT = 1024, 0.125                  # Standard-1 row: 1024 x 0.125 s = 128 s
    V5_BANDS_J = {'T1': (2, 12), 'T2': (13, 128), 'T3': (129, 511)}   # Fourier index ranges (inclusive), nu = j / 128 s
    V5_MIN_PCUS = 2                                  # PCUs on for the whole row; A = on[0::2], B = on[1::2]
    V5_BLOCKS = 8                                    # PCU "on" = all 8 blocks of 128 bins have > 0 counts
    V5_MIN_ROWS = 3                                  # valid rows per observation, else timing features missing
    V5_CHECK_RATE = (20.0, 500.0)                    # source counts/s/PCU range for the auto-power cross-check
    V5_CHECK_MIN_SPEARMAN = 0.90

# =====================================================================================
# v6 (written 2026-10-01 AFTER all v1-v5 results, BEFORE any v6 download/feature/model; see reports/preregistration_v6.md).
# Active only for XRB_VERSION starting with v6 (the v4 and v5 blocks above are also active). v1-v5 behaviour unchanged.
# =====================================================================================
if _os.environ.get('XRB_VERSION', 'v1').startswith(('v6', 'v7', 'v8', 'v9')):     # v7-v9 re-use the v6 estimator settings (v6lib)
    MIN_ELIGIBLE = 10; MJD_MAX = 55931.0; MJD_MIN = 0.0          # selection as v4b2: all gain epochs, >= 10 eligible
    V6_AUTO_MAX_RATE = 500.0            # counts/s/PCU: single-PCU rows use the auto-power estimator only below this
    V6_NLOGBINS = 9                     # log-spaced bins 1/128 .. 4 Hz for the nuPnu centroid
    V6_NUC_MIN_RMS = 0.05               # nu_c missing if T*_total < this
    V6_T_DOF = 4                        # CCTLR Student-t degrees of freedom
    V6_SIGMA_FLOOR = 0.01
    V6_KNN = 25                         # colour-conditional permutation test: kNN residualisation
    V6_N_PERM = 20000
    V6_CONFORMAL_EPS = (0.1, 0.2)
    V6_BUDGET_K = (1, 2, 3, 5, 8, 13, 21); V6_BUDGET_DRAWS = 500
    V6_PROB_CLIP = (0.01, 0.99)

# =====================================================================================
# v7 (written 2026-10-05 AFTER all v1-v6 results, BEFORE any v7 download/model; see reports/preregistration_v7.md).
# Active only for XRB_VERSION starting with v7 (the v4/v5/v6 blocks above are also active; this block comes last and
# restores the v2 gain-epoch-5 selection window). v1-v6 behaviour unchanged. Awaiting user approval before any run.
# =====================================================================================
if _os.environ.get('XRB_VERSION', 'v1').startswith(('v7', 'v8', 'v9')):     # v8/v9 re-use the v7 state / MINBAR / MAXI settings
    MJD_MIN = 51677.0; MJD_MAX = 55931.0; MIN_ELIGIBLE = 10; N_PER_SOURCE = 15    # v2 rules (B2)
    DEADTIME = 'std1'; VLE_DT_ALT = 1.5e-4
    # ---- B1: MINBAR DR1 (Galloway et al. 2020, ApJS 249, 32; Monash Bridges, CC BY 4.0) ----
    V7_MINBAR_FILES = {'minbar.txt': ('https://ndownloader.figshare.com/files/23201936', 'a398e7b927426ddf517caabdb7d2da40'),
                       'minbar-obs.txt': ('https://ndownloader.figshare.com/files/24131849', '311b2a0eb7a0611ed0addb2352d9a75c')}
    V7_BURST_DEFAULT_DUR_S = 300.0      # MINBAR dur missing -> burst interval [Time, Time + 300 s]
    V7_BURST_PRE_S = 20.0               # rows excluded for the state index: from 20 s before burst start
    # ---- A: state index (RM06 Table 2 thresholds; 0.1-4 Hz instead of 0.1-10 Hz) ----
    V7_RMS_J = (13, 511)                # Fourier indices of a 128-s Standard-1 row: 0.102-3.99 Hz
    V7_RMS_HARD, V7_RMS_SOFT = 0.10, 0.075
    V7_STATE_MIN_ROWS = 3               # rows with >= 2 PCUs on (all-pairs cospectrum only)
    V7_SANITY_FRAC = 2.0 / 3.0          # XTE J1118+480 hard-like and Z sources (Cyg X-2, GX 17+2) soft-like fractions
    V7_Z_SOURCES = ('CYGX2', 'GX17+2')
    V7_MIN_BH_SOURCES_PER_STRATUM = 3
    # ---- B2: persistent dynamical BHs (Marcel et al. 2026, arXiv:2606.19952, Table 1) ----
    V7_PERSISTENT_BH = {'CYGX1': 'Cyg X-1', 'LMCX1': 'LMC X-1', 'LMCX3': 'LMC X-3'}
    V7_POINTING_REF = 'simbad'          # pending user decision (preregistration_v7.md sec. 7 item 1)
    # ---- C: MAXI / de Beurs et al. 2022 ----
    V7_DEBEURS_REPO = 'https://github.com/zdebeurs/3ML_methods_for_XRB_classification'
    V7_DEBEURS_KNN_K = 24; V7_DEBEURS_SVM = dict(C=0.655, gamma=0.585)
    V7_REPRO_TOL_SOURCES, V7_REPRO_TOL_BH = 2, 1
    V7_MAXI_URL = 'http://maxi.riken.jp/star_data/{j}/{j}_g_lc_1day_all.dat'
    V7_MAXI_SIGMA, V7_MAXI_OUTLIER_SIGMA, V7_MAXI_MIN_POINTS = 3.0, 10.0, 100
    V7_MAXI_TRAIN_CAP = 200
    V7_C2_KNN_GRID = (5, 15, 24, 35); V7_C2_SVM_GRID = dict(C=(0.1, 1.0, 10.0), gamma=(0.1, 0.585, 3.0))

# =====================================================================================
# v8 (written 2026-10-05 AFTER all v1-v7 results, BEFORE any v8 download/feature/model; see reports/preregistration_v8.md).
# Active only for XRB_VERSION starting with v8 (the v4-v7 blocks above are also active). v1-v7 behaviour unchanged.
# =====================================================================================
if _os.environ.get('XRB_VERSION', 'v1').startswith('v8'):
    # ---- v8b: new dynamically confirmed BHs (Marcel+2026 Table 1, not used in any earlier RXTE sample) ----
    MJD_MIN = 0.0; MJD_MAX = 55931.0            # all gain epochs (as v4b2 / v6)
    MIN_ELIGIBLE = 3; N_PER_SOURCE = 15         # >= 3 eligible pointings (explicit relaxation of the v2 rule)
    V8_NEW_BH = {'GS1354-64': 'GS 1354-64', 'SS433': 'SS 433'}       # from the TAP query in preregistration_v8.md sec. 2
    V8_TAP_URL = 'https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync'
    V8_MIN_SOURCES_PER_CLASS = 3                # v8b primary testable if >= 3 BH and >= 3 NS sources in the stratum
    # ---- v8c: event-mode high-frequency timing ----
    V8_HF_MODE_REGEX = r'^E_\d+us_\d+M_0_\d+s$'
    V8_HF_CHAINS = 'X1L^X1R^X2L^X2R^X3L^X3R'
    V8_HF_MAX_TIMEDEL = 2.0 ** -12
    V8_HF_DT = 2.0 ** -12                       # bin width (s): Nyquist 2048 Hz
    V8_HF_SEG_S = 16.0                          # segment length (s): N = 65536 bins
    V8_HF_BANDS_J = {'LC': (16, 63), 'HF1': (64, 1023), 'HF2': (1024, 8191), 'HF3': (8192, 16383), 'NULL': (24576, 32767)}
    V8_HF_MIN_SEG = 10
    V8_HF_MAX_NULL_Z = 5.0
    V8_HF_MAX_NULL_FAIL_FRAC = 0.20
    V8_HF_MIN_SPEARMAN_LC = 0.90
    V8_AMXP = ('SAXJ1808.4-3658', 'XTEJ1814-338', 'HETEJ1900.1-245')
    # ---- v8d: MAXI N_H control ----
    V8_NH_GAMMA = 2.0
    V8_NH_GRID = (19.0, 23.5, 200)              # log10 N_H grid (cm^-2) for the tbabs transmission table (plus N_H = 0)
    V8_NH_BANDS = {'L': (2.0, 4.0), 'M': (4.0, 10.0), 'H': (10.0, 20.0)}

# =====================================================================================
# v9 (written 2026-10-05 AFTER all v1-v8 results, BEFORE any v9 download/feature/model; see reports/preregistration_v9.md).
# Active only for XRB_VERSION starting with v9 (the v4-v7 blocks above are also active). v1-v8 behaviour unchanged.
# =====================================================================================
if _os.environ.get('XRB_VERSION', 'v1').startswith('v9'):
    # ---- NICER/XTI selection ----
    V9_TAP_URL = 'https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync'
    V9_ARCHIVE = 'https://nasa-heasarc.s3.amazonaws.com/nicer/data/obs/'   # HEASARC's AWS open-data mirror (decision_log: ~10x faster, bytes identical)
    V9_ARCHIVE_HEASARC = 'https://heasarc.gsfc.nasa.gov/FTP/nicer/data/obs/'
    V9_TOL_DEG = 0.05                   # target position within 0.05 deg (FOV ~30 arcmin^2, radius ~0.05 deg)
    V9_MIN_EXPOSURE_S = 1000.0          # nicermastr exposure
    V9_MIN_ELIGIBLE = 5
    V9_N_PER_SOURCE = 8                 # time-stratified (03 algorithm, default_rng(SEED + position))
    V9_MAX_TRIES = 3                    # candidates tried per time bin
    # ---- streaming download of the cleaned event file (events are time ordered) ----
    V9_CAP_BYTES = 300_000_000          # at most the first 300 MB of the compressed ni*_0mpu7_cl.evt.gz
    V9_TARGET_SEG = 6                   # stop once >= 6 gap-free 128-s segments are available (or EOF / cap)
    V9_GAP_S = 1.0                      # gap between consecutive events (any energy) > 1 s = break in good time
    # ---- features ----
    V9_SEG_S = 128.0; V9_DT = 1.0 / 256.0          # N = 32768, Nyquist 128 Hz
    V9_PI_TIMING = (200, 1000)          # PI channels (10 eV): 2-10 keV for timing and the rate cut
    V9_PI_BANDS = {'A': (200, 400), 'B': (400, 600), 'C': (600, 1000)}   # 2-4, 4-6, 6-10 keV; c1 = B/A, c2 = C/B
    V9_T_BANDS_J = {'T1': (2, 12), 'T2': (13, 128), 'T3': (129, 511)}   # j / 128 s: as v5
    V9_STATE_J = (13, 1280)             # 0.10-10 Hz: RM06 band
    V9_WHITE_J = (12288, 16383)         # 96-128 Hz: white-level monitor (reported only)
    V9_NUC_EDGES_HZ = (1.0 / 128.0, 64.0, 13)      # 13 factor-2 log bins, 1/128-64 Hz, for nu_c
    V9_MIN_MPUS = 2; V9_BLOCKS = 8      # MPU on = all 8 blocks (16 s) of the segment have > 0 counts (2-10 keV)
    V9_MIN_RATE = 20.0                  # 2-10 keV counts/s (all MPUs) in the valid segments
    V9_MIN_SEG = 3
    V9_BURST_PRE_S, V9_BURST_POST_S = 20.0, 200.0  # v4 burst rules on the 1-s 2-10 keV light curve; segments overlapping removed
    V9_Z_SANITY = ('Cyg X-2', 'GX 17+2')
    V9_MIN_SOURCES_PER_CLASS = 3
