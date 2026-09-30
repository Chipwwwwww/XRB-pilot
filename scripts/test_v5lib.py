"""Unit tests for v5lib (preregistration_v5.md §4a): synthetic two-group Poisson light curves with a common sinusoid."""
import os, sys
os.environ['XRB_VERSION'] = 'v5'
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import v5lib as L5

rng = np.random.default_rng(42)
N, DT = L5.N, L5.DT
t = np.arange(N + 1) * DT
fails = 0


def check(name, ok, info=''):
    global fails
    print(('PASS ' if ok else 'FAIL ') + name, info); fails += (not ok)


def rows(mu_src, b, rms, f, n_rows, n_pcu=3):
    """(5, n_rows, N) Poisson counts; PCUs 0..n_pcu-1 on; source = mu*(1 + a cos) integrated over each bin."""
    out = np.zeros((5, n_rows, N))
    a = np.sqrt(2) * rms
    for r in range(n_rows):
        ph = rng.uniform(0, 2 * np.pi)
        integ = mu_src * (np.diff(t) + (a / (2 * np.pi * f) * np.diff(np.sin(2 * np.pi * f * t + ph)) if rms > 0 else 0))
        for p in range(n_pcu): out[p, r] = rng.poisson(integ + b * DT)
    return out


def median_T(r5, b):
    fs = [L5.row_features(r5[:, i], b) for i in range(r5.shape[1])]
    return {k: float(L5.signed_sqrt(np.median([x[f'f_{k}'] for x in fs]))) for k in L5.BANDS}, \
           {k: float(L5.signed_sqrt(np.median([x[f'fauto_{k}'] for x in fs]))) for k in L5.BANDS}


for f, band in ((0.05, 'T1'), (0.5, 'T2'), (3.0, 'T3')):
    T, Ta = median_T(rows(100.0, 20.0, 0.2, f, 20), 20.0)
    check(f'sinusoid rms 0.2 at {f} Hz recovered in {band} (cospectrum, <10%)', abs(T[band] - 0.2) / 0.2 < 0.10, T)
    check(f'sinusoid rms 0.2 at {f} Hz recovered in {band} (auto power, <10%)', abs(Ta[band] - 0.2) / 0.2 < 0.10, Ta)
T, Ta = median_T(rows(200.0, 20.0, 0.0, 1.0, 50), 20.0)
check('pure Poisson: median |T| < 0.02 in every band (cospectrum)', all(abs(v) < 0.02 for v in T.values()), T)
# PCU on/off rule and groups
r5 = rows(100.0, 20.0, 0.0, 1.0, 1, n_pcu=1)[:, 0]
check('one PCU on -> row invalid', L5.row_features(r5, 20.0) is None)
r5 = rows(100.0, 20.0, 0.0, 1.0, 1, n_pcu=3)[:, 0]; r5[2, 768:] = 0      # off for the last two 128-bin blocks
check('PCU switched off inside the row -> not counted as on', list(np.where(L5.pcus_on(r5))[0]) == [0, 1])
# background correction: 50% background, true source rms 0.2 at 0.5 Hz
T, _ = median_T(rows(40.0, 40.0, 0.2, 0.5, 40), 40.0)
check('background-corrected rms with 50% background (<10%)', abs(T['T2'] - 0.2) / 0.2 < 0.10, T)
# fill_missing
Xtr = np.array([[1.0, 2.0], [np.nan, np.nan], [3.0, 4.0]]); Xte = np.array([[np.nan, np.nan]])
a, b = L5.fill_missing(Xtr, Xte)
check('fill_missing: train median + indicator', np.allclose(b, [[2.0, 3.0, 1.0]]) and np.allclose(a[1], [2.0, 3.0, 1.0]), (a, b))
print('\nALL PASS' if fails == 0 else f'\n{fails} FAILED')
sys.exit(1 if fails else 0)
