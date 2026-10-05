"""Synthetic checks of the v8c event-mode estimator (preregistration_v8.md sec. 7, IC3). Run before any real HF feature.
Events: continuous-time Poisson per PCU (thinning for a sinusoidal modulation with fractional rms a), optional unmodulated
background and non-paralyzable dead time per PCU, then time-quantised to 2^-13 s ticks (floor), as in E_125us data."""
import os, sys
os.environ.setdefault('XRB_VERSION', 'v8c')
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import v8lib as L8

TICK = 2.0 ** -13
rng = np.random.default_rng(42)


def sim(T, r, f=None, a=0.0, rb=0.0, tau=0.0, npcu=5, t0=1000.0):
    ts, ps = [], []
    for k in range(npcu):
        rmax = r * (1 + np.sqrt(2) * a)
        n = rng.poisson(rmax * T); t = np.sort(rng.uniform(0, T, n))
        if f is not None and a > 0:
            keep = rng.uniform(0, 1, n) < (1 + np.sqrt(2) * a * np.sin(2 * np.pi * f * t)) / (1 + np.sqrt(2) * a)
            t = t[keep]
        if rb > 0: t = np.sort(np.r_[t, rng.uniform(0, T, rng.poisson(rb * T))])
        if tau > 0:                                         # non-paralyzable dead time
            out = np.empty_like(t); m = 0; last = -1.0
            for x in t:
                if x >= last + tau: out[m] = x; m += 1; last = x
            t = out[:m]
        ts.append(np.floor((t0 + t) / TICK) * TICK); ps.append(np.full(len(t), k))
    t = np.concatenate(ts); p = np.concatenate(ps); o = np.argsort(t, kind='mergesort')
    return t[o], p[o], np.array([[t0, t0 + T]])


def run(name, T, r, band, lo, hi, **kw):
    t, p, g = sim(T, r, **kw)
    seg = L8.hf_from_events(t, p, g, kw.get('rb', 0.0)); s = L8.hf_summary(seg)
    v = s[band]; ok = lo <= v <= hi
    return dict(test=name, band=band, value=round(v, 5), lo=lo, hi=hi, z=round(s[f'{band}_var'] / s[f'{band}_se'], 2) if band != 'NULL' else round(s['NULL_z'], 2),
                n_seg=s['n_seg'], passed=bool(ok))


rows = []
rows.append(run('sinusoid 20 Hz rms 0.10', 640, 2000, 'HF1', 0.09, 0.11, f=20.0, a=0.10))
rows.append(run('sinusoid 200 Hz rms 0.10', 640, 2000, 'HF2', 0.09, 0.11, f=200.0, a=0.10))
rows.append(run('sinusoid 700 Hz rms 0.10', 640, 2000, 'HF3', 0.09, 0.11, f=700.0, a=0.10))
rows.append(run('sinusoid 900 Hz rms 0.10 (binning correction)', 640, 2000, 'HF3', 0.09, 0.11, f=900.0, a=0.10))
rows.append(run('sinusoid 200 Hz rms 0.10, 50% background', 640, 1000, 'HF2', 0.09, 0.11, f=200.0, a=0.10, rb=1000.0))
# pure Poisson: unbiased (|z| < 3) in every band
t, p, g = sim(640, 2000)
s = L8.hf_summary(L8.hf_from_events(t, p, g, 0.0))
for b in ('HF1', 'HF2', 'HF3', 'NULL'):
    z = s[f'{b}_var'] / s[f'{b}_se']
    rows.append(dict(test='pure Poisson 2000 c/s/PCU', band=b, value=round(s[b], 5), lo=-3, hi=3, z=round(z, 2), n_seg=s['n_seg'], passed=bool(abs(z) < 3)))
# dead time 10 us per PCU (non-paralyzable): cross-PCU cospectrum stays white-noise free
t, p, g = sim(320, 2000, tau=1e-5)
s = L8.hf_summary(L8.hf_from_events(t, p, g, 0.0))
for b in ('HF1', 'HF2', 'HF3', 'NULL'):
    z = s[f'{b}_var'] / s[f'{b}_se']
    rows.append(dict(test='Poisson + 10 us dead time per PCU', band=b, value=round(s[b], 5), lo=-3, hi=3, z=round(z, 2), n_seg=s['n_seg'], passed=bool(abs(z) < 3)))
# segment logic: GTI [0,100] -> 0,16,32,48,64,80; burst [40,50] removes 32 and 48; GTI [200,233] -> 200,216 => 6
g = np.array([[0.0, 100.0], [200.0, 233.0]])
sg = L8.segments(g, [(40.0, 50.0)])
rows.append(dict(test='segments: 16-s inside GTI, burst [40,50] removed', band='-', value=len(sg), lo=6, hi=6, z=np.nan, n_seg=len(sg),
                 passed=bool(len(sg) == 6 and not any((x < 50) and (x + 16 > 40) for x in sg))))
res = pd.DataFrame(rows)
pd.set_option('display.width', 200)
print(res.to_string(index=False))
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'logs', 'v8c'), exist_ok=True)
res.to_csv(os.path.join(os.path.dirname(__file__), '..', 'logs', 'v8c', 'test_v8lib.csv'), index=False)
print('ALL PASS' if res.passed.all() else 'SOME FAILED')
sys.exit(0 if res.passed.all() else 1)
