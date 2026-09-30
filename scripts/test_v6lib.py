"""Unit tests for v6lib (preregistration_v6.md §3.4 and §7): estimator variance and recovery, nu_c, CCTLR, permutation
test calibration, conformal coverage, proper scores. Synthetic data only."""
import os, sys
os.environ['XRB_VERSION'] = 'v6'
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import v5lib as L5, v6lib as L6

rng = np.random.default_rng(42)
N, DT = L5.N, L5.DT
t = np.arange(N + 1) * DT
fails = 0


def check(name, ok, info=''):
    global fails
    print(('PASS ' if ok else 'FAIL ') + name, info); fails += (not ok)


def rows(mu, b, rms, f, n_rows, n_pcu):
    out = np.zeros((5, n_rows, N)); a = np.sqrt(2) * rms
    for r in range(n_rows):
        ph = rng.uniform(0, 2 * np.pi)
        integ = mu * (np.diff(t) + (a / (2 * np.pi * f) * np.diff(np.sin(2 * np.pi * f * t + ph)) if rms > 0 else 0))
        for p in range(n_pcu): out[p, r] = rng.poisson(integ + b * DT)
    return out


# 1. variance reduction vs the v5 A/B split (pure Poisson), 3-5 PCUs
for n in (3, 4, 5):
    r5 = rows(100.0, 20.0, 0.0, 1.0, 300, n)
    ap = np.array([L6.allpairs_row(r5[:, i], 20.0)['T3'] for i in range(300)])
    ab = np.array([L5.row_features(r5[:, i], 20.0)['f_T3'] for i in range(300)])
    red = 1 - ap.var() / ab.var()
    check(f'all-pairs variance reduction >= 25% with {n} PCUs', red >= 0.25, f'{red:.2f}')
    check(f'all-pairs unbiased under pure Poisson ({n} PCUs, |mean| < 3 SE)', abs(ap.mean()) < 3 * ap.std() / np.sqrt(len(ap)), f'{ap.mean():.2e}')
# 2. sinusoid recovery (all-pairs, 4 PCUs) and single-PCU hybrid
for f, band in ((0.05, 'T1'), (0.5, 'T2'), (3.0, 'T3')):
    for n in (4, 1):
        r5 = rows(100.0, 20.0, 0.2, f, 20, n)
        v = np.median([L6.allpairs_row(r5[:, i], 20.0)[band] for i in range(20)])
        check(f'rms 0.2 at {f} Hz recovered in {band} ({n} PCU{"s" if n > 1 else ""}, <10%)', abs(np.sqrt(v) - 0.2) / 0.2 < 0.1, f'{np.sqrt(v):.3f}')
# 3. nu_c within one log bin of a sinusoid's frequency
for f in (0.05, 0.5, 3.0):
    r5 = rows(200.0, 20.0, 0.2, f, 20, 4)
    fs = [L6.allpairs_row(r5[:, i], 20.0) for i in range(20)]
    lb = [np.median([x[f'lb{i}'] for x in fs]) for i in range(len(L6.LOGBINS))]
    tot = np.sqrt(sum(np.median([x[k] for x in fs]) for k in L6.BANDS))
    nc = L6.nu_centroid(lb, tot); jb = np.argmin(abs(np.log(L6.NU_B) - np.log(f)))
    check(f'nu_c for a {f} Hz sinusoid within one log bin', abs(np.log(nc) - np.log(f)) <= L6.DLN[jb] + 1e-9, f'{nc:.3f} Hz')
check('nu_c missing for low total rms', np.isnan(L6.nu_centroid([1e-4] * len(L6.LOGBINS), 0.01)))
# 4. CCTLR: timing informative only at high c2; missing timing -> H-LR only
n_src, n_obs = 40, 20
H, T, y, g = [], [], [], []
for s in range(n_src):
    lab = int(s < 12); c2 = rng.uniform(0.05, 0.45, n_obs); c1 = 0.3 + 0.6 * c2 + rng.normal(0, .05, n_obs)
    t1 = 0.02 + (0.25 if lab else 0.08) * np.clip(c2 - 0.2, 0, None) / 0.25 + rng.normal(0, .01, n_obs)
    H.append(np.c_[c1, c2]); T.append(np.c_[t1, t1 * .8 + rng.normal(0, .01, n_obs), rng.normal(.05, .02, n_obs)]); y += [lab] * n_obs; g += [s] * n_obs
H, T, y, g = np.vstack(H), np.vstack(T), np.array(y), np.array(g)
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.linear_model import LogisticRegression
folds = list(LeaveOneGroupOut().split(H, y, g))
sc = L6.cctlr_loso(H, T, y, g, folds)
src = pd.DataFrame(dict(s=sc, y=y, g=g)).groupby('g').mean()
from sklearn.metrics import roc_auc_score
check('CCTLR separates classes that differ only in timing at high c2 (source AUC > 0.9)', roc_auc_score(src.y, src.s) > 0.9, f'{roc_auc_score(src.y, src.s):.3f}')
m = L6.CCTLR().fit(H, T, y, g); Tm = T.copy(); Tm[:5] = np.nan
check('missing timing -> score equals the H-LR probability', np.allclose(m.score(H[:5], Tm[:5]), m.lr.predict_proba(m.sc.transform(H[:5]))[:, 1]))
# 5. permutation test: calibrated under H0 (p < 0.05 in <= 12% of 60 null datasets), powerful under H1
ps = []
for rep in range(60):
    Tn = np.r_[[rng.normal(0.02 + 0.1 * h[1], 0.03) for h in H]] + np.repeat(rng.normal(0, .02, n_src), n_obs)   # source effect, no class effect
    res = L6.source_residuals(H, Tn, g)
    ps.append(L6.perm_test(res, pd.Series(y, index=g).groupby(level=0).first(), n_perm=500, seed=rep)['p'])
check('permutation test under H0: fraction p < 0.05 <= 0.12', np.mean(np.array(ps) < 0.05) <= 0.12, f'{np.mean(np.array(ps) < 0.05):.3f}')
res = L6.source_residuals(H, T[:, 0], g)
check('permutation test under H1: p < 0.01', L6.perm_test(res, pd.Series(y, index=g).groupby(level=0).first(), n_perm=2000)['p'] < 0.01)
check('holm adjustment', np.allclose(L6.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06]), L6.holm([0.01, 0.04, 0.03]))
# 6. conformal: exchangeable scores -> coverage >= 1 - eps (per class, on average)
cov = []
for rep in range(200):
    yy = np.r_[np.ones(8, int), np.zeros(30, int)]; ss = np.clip(np.where(yy == 1, rng.normal(.7, .15, 38), rng.normal(.3, .15, 38)), 0, 1)
    sets = L6.conformal_loso(ss, yy, 0.2)
    cov.append(np.mean([('BH' in st and yi == 1) or ('NS' in st and yi == 0) for (_, _, st), yi in zip(sets, yy)]))
check('conformal LOSO coverage >= 0.8 - 0.02 at eps = 0.2', np.mean(cov) >= 0.78, f'{np.mean(cov):.3f}')
# 7. proper scores: a perfect model beats a random one
oo = pd.DataFrame(dict(source_id=np.repeat(np.arange(20), 3).astype(str), obs_id=np.arange(60).astype(str),
                       true_label=np.where(np.repeat(np.arange(20), 3) < 6, 'BH', 'NS')))
good = oo.assign(BH_score=np.where(oo.true_label == 'BH', .95, .05)); bad = oo.assign(BH_score=.5)
for d in (good, bad): d['predicted_label'] = np.where(d.BH_score >= .5, 'BH', 'NS')
ps_ = L6.proper_score_bootstrap({'bad': bad, 'good': good}, 'bad', n_boot=200)
check('proper scores: perfect model better than 0.5 everywhere (CI < 0)', (ps_[ps_.comparison.str.contains(' - ')].ci97_5 < 0).all())
print('\nALL PASS' if fails == 0 else f'\n{fails} FAILED')
sys.exit(1 if fails else 0)
