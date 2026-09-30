"""v5 timing features from Standard-1 (preregistration_v5.md §3).
Cospectrum of two independent PCU groups (white-noise mean 0; Bachetti+2015), divided by the binning factor
sinc^2(pi j/N) (van der Klis 1989 Eq. 2.19), background-corrected, median over 128-s rows inside the spectrum GTIs."""
import os, glob
from pathlib import Path
import numpy as np
from astropy.io import fits
import config as C
from common import ROOT
from spectra import read_pha

EXT = Path(os.environ.get('XRB_EXTERNAL_RAW', Path.home()/'xrb-pilot-data/raw'))
N, DT = C.V5_N_BINS, C.V5_DT
J = np.arange(N // 2 + 1)
SINC2 = np.sinc(J / N) ** 2                     # np.sinc(x) = sin(pi x)/(pi x)
BANDS = C.V5_BANDS_J


def fix(p):
    return (ROOT / str(p).replace('\\', '/')).resolve()


def std1_files(obs_id):
    fs = sorted(glob.glob(str(ROOT/f'data/raw/std1/{obs_id}/FS46_*.gz')))
    return fs or sorted(glob.glob(str(EXT/f'std1/{obs_id}/FS46_*.gz')))


def std1_rows(obs_id, gti):
    """(5, n_rows, N) counts for the Standard-1 rows lying completely inside the GTIs."""
    rows = []
    for f in std1_files(obs_id):
        with fits.open(f, memmap=False) as h:
            d = h[1].data; tz = float(h[1].header.get('TIMEZERO', 0.0))
            if d['XeCntPcu0'].shape[1] != N: continue
            t0 = np.asarray(d['Time'], float) + tz
            ok = np.zeros(len(t0), bool)
            for a, b in gti: ok |= (t0 >= a - 1e-3) & (t0 + N * DT <= b + 1e-3)
            if ok.any(): rows.append(np.stack([np.asarray(d[f'XeCntPcu{p}'], float)[ok] for p in range(5)]))
    if not rows: return np.zeros((5, 0, N))
    return np.concatenate(rows, axis=1)


def pcus_on(row5):
    """row5: (5, N). PCU on = every one of the V5_BLOCKS blocks has > 0 counts."""
    return (row5.reshape(5, C.V5_BLOCKS, -1).sum(2) > 0).all(1)


def band_var_cross(x, y):
    """Band variances (counts^2 per bin^2) from the cospectrum, binning-corrected; dict band -> value."""
    X, Y = np.fft.rfft(x), np.fft.rfft(y)
    c = (X * np.conj(Y)).real / SINC2
    return {k: 2.0 / N**2 * c[a:b + 1].sum() for k, (a, b) in BANDS.items()}


def band_var_auto(z):
    """Band variances from the auto power spectrum minus the Poisson level (E|Z_j|^2 = N * mean counts), binning-corrected."""
    Z = np.fft.rfft(z)
    p = (np.abs(Z) ** 2 - N * z.mean()) / SINC2
    return {k: 2.0 / N**2 * p[a:b + 1].sum() for k, (a, b) in BANDS.items()}


def row_features(row5, b_pcu):
    """Fractional variances for one row (cospectrum of groups A/B), plus the auto-power T2 check; None if invalid."""
    on = np.where(pcus_on(row5))[0]
    if len(on) < C.V5_MIN_PCUS: return None
    A, B = on[0::2], on[1::2]
    x, y = row5[A].sum(0), row5[B].sum(0)
    sx, sy = x.mean() - len(A) * b_pcu * DT, y.mean() - len(B) * b_pcu * DT
    if sx <= 0 or sy <= 0: return None
    v = band_var_cross(x, y)
    z = x + y; sz = sx + sy; va = band_var_auto(z)
    out = {f'f_{k}': v[k] / (sx * sy) for k in BANDS}
    out.update({f'fauto_{k}': va[k] / sz**2 for k in BANDS})
    out.update(n_on=len(on), src_rate_per_pcu=sz / DT / len(on), tot_rate_per_pcu=z.mean() / DT / len(on))
    return out


def signed_sqrt(f):
    return np.sign(f) * np.sqrt(np.abs(f))


def obs_timing(obs_id, path_src, path_bkg):
    """Per-observation timing features (preregistration_v5.md §3)."""
    rec = dict(obs_id=obs_id)
    try:
        s, bk = read_pha(fix(path_src)), read_pha(fix(path_bkg))
        cnt = bk['counts'].sum()
        rate = cnt if str(bk['unit']).lower().replace(' ', '').endswith('/s') else cnt / bk['exposure']
        b_pcu = rate / bk['npcu']
        rows = std1_rows(obs_id, s['gti'])
        rec.update(bkg_rate_per_pcu=b_pcu, n_rows_in_gti=rows.shape[1], n_std1_files=len(std1_files(obs_id)))
        feats = [f for f in (row_features(rows[:, i], b_pcu) for i in range(rows.shape[1])) if f is not None]
        rec['n_rows_valid'] = len(feats)
        if len(feats) < C.V5_MIN_ROWS:
            rec['status'] = 'missing (< %d valid rows)' % C.V5_MIN_ROWS; return rec
        keys = feats[0].keys()
        med = {k: float(np.median([f[k] for f in feats])) for k in keys}
        rec.update(med)
        for k in BANDS: rec[k] = float(signed_sqrt(med[f'f_{k}'])); rec[f'{k}_auto'] = float(signed_sqrt(med[f'fauto_{k}']))
        rec['T_total'] = float(signed_sqrt(sum(med[f'f_{k}'] for k in BANDS)))
        rec['status'] = 'ok'
    except Exception as e:
        rec['status'] = f'error: {type(e).__name__}: {e}'[:200]
    return rec


def fill_missing(Xtr, Xte):
    """Train-fold median fill + one 0/1 'timing missing' indicator (same rule as v4b3)."""
    med = np.nanmedian(Xtr, axis=0); med = np.where(np.isfinite(med), med, 0.0)
    def f(X):
        X = X.copy(); miss = ~np.isfinite(X); X[miss] = np.take(med, np.where(miss)[1])
        return np.c_[X, miss.any(1).astype(float)]
    return f(Xtr), f(Xte)
