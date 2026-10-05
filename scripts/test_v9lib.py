"""v9 implementation checks before any NICER data (preregistration_v9.md sec. 7): IC1 streamed-prefix parser vs astropy on a
synthetic NICER-format event file (complete and truncated); IC2 synthetic NICER-like events (7 MPUs, 1/256 s): T1-T3 and the
0.1-10 Hz state rms recovered within +-10%, pure Poisson unbiased (|z| < 3), nu_c of a zero-centred Lorentzian (0.5 / 5 Hz)."""
import os, sys, gzip, io
os.environ.setdefault('XRB_VERSION', 'v9')
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
from astropy.io import fits
import config as C
import v9lib as L9

rng = np.random.default_rng(42)
OUT = os.path.join(os.path.dirname(__file__), '..', 'logs', 'v9'); os.makedirs(OUT, exist_ok=True)
rows = []

# ---------------- IC1 parser ----------------
n = 50000
cols = [fits.Column('TIME', 'D', array=np.sort(rng.uniform(1e8, 1e8 + 500, n))), fits.Column('RAWX', 'B', array=rng.integers(0, 8, n)),
        fits.Column('RAWY', 'B', array=rng.integers(0, 8, n)), fits.Column('PHA', 'I', array=rng.integers(0, 1500, n)),
        fits.Column('PHA_FAST', 'I', array=rng.integers(0, 1500, n)), fits.Column('DET_ID', 'B', array=rng.integers(0, 67, n)),
        fits.Column('DEADTIME', 'B', array=rng.integers(0, 255, n)), fits.Column('EVENT_FLAGS', '8X', array=np.zeros((n, 8), bool)),
        fits.Column('TICK', 'K', array=rng.integers(0, 2**40, n)), fits.Column('MPU_A_TEMP', 'I', array=rng.integers(0, 500, n)),
        fits.Column('MPU_UNDER_COUNT', 'J', array=rng.integers(0, 1000, n)), fits.Column('PI_FAST', 'I', array=rng.integers(0, 1500, n)),
        fits.Column('PI', 'I', array=rng.integers(0, 1500, n)), fits.Column('PI_RATIO', 'E', array=rng.uniform(0, 2, n).astype(np.float32))]
hdu = fits.BinTableHDU.from_columns(cols, name='EVENTS'); bio = io.BytesIO(); fits.HDUList([fits.PrimaryHDU(), hdu]).writeto(bio)
gz = gzip.compress(bio.getvalue())
tmp = os.path.join(OUT, '_synthetic_cl.evt.gz'); open(tmp, 'wb').write(gz)
arr, h, complete = L9.read_prefix(tmp)
ok = complete and np.array_equal(arr['TIME'], hdu.data['TIME']) and np.array_equal(arr['PI'], hdu.data['PI']) and np.array_equal(arr['DET_ID'], hdu.data['DET_ID'])
rows.append(dict(test='IC1 parser = astropy (complete synthetic file, 14 NICER columns)', value=int(len(arr['TIME'])), passed=bool(ok)))
open(tmp, 'wb').write(gz[:len(gz) // 2])
arr2, _, complete2 = L9.read_prefix(tmp)
k = len(arr2['TIME'])
ok2 = (not complete2) and 0 < k < n and np.array_equal(arr2['TIME'], hdu.data['TIME'][:k]) and np.array_equal(arr2['PI'], hdu.data['PI'][:k])
rows.append(dict(test='IC1 truncated prefix = first rows', value=k, passed=bool(ok2)))
os.remove(tmp)


# ---------------- IC2 synthetic events ----------------
def simulate(T, r_mpu, lam_fn, t0=2e8):
    """Bin-level Poisson events for 7 MPUs, dt = 1/256 s; lam_fn(t) = fractional modulation (common to all MPUs)."""
    dt = C.V9_DT; nb = int(T / dt); tc = t0 + (np.arange(nb) + 0.5) * dt
    mod = 1.0 + lam_fn(tc - t0); mod = np.clip(mod, 0, None)
    ts, ds = [], []
    for m in range(7):
        c = rng.poisson(r_mpu * dt * mod)
        tt = np.repeat(t0 + np.arange(nb) * dt, c) + rng.uniform(0, dt, c.sum())
        ts.append(tt); ds.append(m * 10 + rng.integers(0, 8, c.sum()))
    t = np.concatenate(ts); d = np.concatenate(ds); o = np.argsort(t)
    return dict(TIME=t[o], DET_ID=d[o], PI=rng.integers(200, 1000, len(t)))


def lorentz_lc(T, nu0, rms):
    dt = C.V9_DT; nb = int(T / dt); f = np.fft.rfftfreq(nb, dt)
    P = np.zeros_like(f); P[1:] = 1.0 / (1.0 + (f[1:] / nu0) ** 2)
    a = (rng.normal(size=len(f)) + 1j * rng.normal(size=len(f))) * np.sqrt(P / 2); a[0] = 0
    x = np.fft.irfft(a, nb); x *= rms / x.std()
    return lambda tt: np.interp(tt, (np.arange(nb) + 0.5) * dt, x)


s2 = np.sqrt(2) * 0.10
f3 = lambda tt: s2 * (np.sin(2 * np.pi * 0.05 * tt) + np.sin(2 * np.pi * 0.5 * tt + 1.0) + np.sin(2 * np.pi * 2.0 * tt + 2.0))
r = L9.obs_features(simulate(1024, 200.0, f3))
for b, target in (('T1', 0.10), ('T2', 0.10), ('T3', 0.10), ('STATE', np.sqrt(0.02))):
    rows.append(dict(test=f'IC2 sinusoids (0.05, 0.5, 2 Hz; rms 0.10 each): {b}', value=round(r[b], 4), passed=bool(abs(r[b] / target - 1) <= 0.10)))
r = L9.obs_features(simulate(1024, 200.0, lambda tt: 0 * tt))
for b in ('T1', 'T2', 'T3', 'STATE', 'WHITE'):
    z = r[f'{b}_var'] / r[f'{b}_se']
    rows.append(dict(test=f'IC2 pure Poisson: {b} |z| < 3', value=round(z, 2), passed=bool(abs(z) < 3)))
for nu0, lo, hi in ((0.5, 0.25, 1.0), (5.0, 2.5, 10.0)):
    r = L9.obs_features(simulate(1024, 300.0, lorentz_lc(1024, nu0, 0.30)))
    rows.append(dict(test=f'IC2 nu_c of a zero-centred Lorentzian nu0 = {nu0} Hz in [{lo}, {hi}]', value=round(r['nu_c'], 3), passed=bool(lo <= r['nu_c'] <= hi)))
res = pd.DataFrame(rows); pd.set_option('display.width', 200)
print(res.to_string(index=False)); res.to_csv(os.path.join(OUT, 'test_v9lib.csv'), index=False)
print('ALL PASS' if res.passed.all() else 'SOME FAILED'); sys.exit(0 if res.passed.all() else 1)
