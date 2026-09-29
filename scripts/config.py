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
