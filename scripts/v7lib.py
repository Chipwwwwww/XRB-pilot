"""v7 helpers (preregistration_v7.md): MINBAR burst table, StdProd GTIs in UTC MJD, Standard-1 light curves,
state index (0.1-4 Hz rms from the all-pairs cospectrum), stratified source bootstrap."""
import os, glob
from pathlib import Path
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
import warnings
import config as C
from common import ROOT
from spectra import read_pha

EXT = Path(os.environ.get('XRB_EXTERNAL_RAW', Path.home()/'xrb-pilot-data/raw'))


def fix(p):
    return (ROOT / str(p).replace('\\', '/')).resolve()


# ------------------------------------------------------------------ MINBAR
def load_minbar():
    """MINBAR DR1 burst table (all instruments). Adds t0, t1 = burst interval in MJD(UTC)."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        b = Table.read(ROOT/'data/raw/minbar/minbar.txt', format='ascii.mrt')
    d = pd.DataFrame({k: np.asarray(b[k].filled(np.nan) if hasattr(b[k], 'filled') else b[k]) for k in
                      ['name', 'instr', 'obsid', 'time', 'entry', 'dur', 'sflag', 'mult']})
    for k in ('name', 'instr', 'obsid', 'sflag'): d[k] = d[k].astype(str).str.strip()
    d['dur_used'] = np.where(np.isfinite(d.dur.astype(float)) & (d.dur.astype(float) > 0), d.dur.astype(float), C.V7_BURST_DEFAULT_DUR_S)
    d['t0'] = d.time.astype(float); d['t1'] = d.t0 + d.dur_used / 86400.0
    return d


def load_minbar_sources():
    """MINBAR source table (positions of the 115 bursters), keyed by MINBAR NAME."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        t = Table.read(ROOT/'data/raw/minbar/minbar_sources_v2.7.fits')
    return pd.DataFrame(dict(name=[str(x).strip() for x in t['NAME']], ra=np.asarray(t['RA_OBJ'], float),
                             dec=np.asarray(t['DEC_OBJ'], float))).drop_duplicates('name').set_index('name')


def sep_deg(ra1, dec1, ra2, dec2):
    r = np.radians
    return np.degrees(np.arccos(np.clip(np.sin(r(dec1))*np.sin(r(dec2)) + np.cos(r(dec1))*np.cos(r(dec2))*np.cos(r(ra1-ra2)), -1, 1)))


def minbar_flag(path_src, obs_id, src_ra, src_dec, bursts, msrc, fov_deg=1.0):
    """Primary v7b1 rule: a MINBAR burst overlapping the spectrum GTIs, from the same ObsID or from an origin within
    fov_deg of the source position. Returns (n_in_fov, n_any)."""
    utc, gti, mjdref, s = gti_utc(path_src)
    idx = bursts_in_gti(bursts, utc); n = 0
    for i in idx:
        bb = bursts.iloc[i]
        d = float(sep_deg(msrc.loc[bb['name']].ra, msrc.loc[bb['name']].dec, src_ra, src_dec)) if bb['name'] in msrc.index else np.nan
        n += bool(bb.obsid == obs_id or (np.isfinite(d) and d <= fov_deg))
    return n, len(idx)


def load_minbar_obs():
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        o = Table.read(ROOT/'data/raw/minbar/minbar-obs.txt', format='ascii.mrt')
    d = pd.DataFrame({k: np.asarray(o[k].filled(np.nan) if hasattr(o[k], 'filled') else o[k]) for k in
                      ['name', 'instr', 'obsid', 'tstart', 'tstop', 'nburst', 'angle']})
    for k in ('name', 'instr', 'obsid'): d[k] = d[k].astype(str).str.strip()
    return d


def gti_utc(path_src):
    """Spectrum GTIs (STDGTI, MET s, TT) -> MJD UTC intervals; plus MET array and MJDREF for light curves."""
    s = read_pha(fix(path_src))
    with fits.open(fix(path_src)) as h:
        hd = h['SPECTRUM'].header
        timesys = str(hd.get('TIMESYS', 'TT')).strip()
    mjd_tt = s['mjdref'] + s['gti'] / 86400.0
    scale = 'tt' if timesys.upper() == 'TT' else timesys.lower()
    utc = Time(mjd_tt.ravel(), format='mjd', scale=scale).utc.mjd.reshape(mjd_tt.shape)
    return utc, s['gti'], s['mjdref'], s


def bursts_in_gti(bursts, gti_mjd_utc):
    """Indices of bursts whose interval [t0, t1] overlaps any GTI interval."""
    hit = np.zeros(len(bursts), bool)
    for a, b in gti_mjd_utc:
        hit |= (bursts.t0.values <= b) & (bursts.t1.values >= a)
    return np.where(hit)[0]


# ------------------------------------------------------------------ Standard-1 light curves
def std1_files(obs_id):
    fs = sorted(glob.glob(str(ROOT/f'data/raw/std1/{obs_id}/FS46_*.gz')))
    return fs or sorted(glob.glob(str(EXT/f'std1/{obs_id}/FS46_*.gz')))


def lightcurve_1s(obs_id, gti, pcus):
    """1-s light curve summed over the spectrum PCUs, complete 1-s bins inside the GTIs (as 17_v4_burst_detect.py).
    Returns (t_met_centre, rate)."""
    t_all, c_all = [], []
    for f in std1_files(obs_id):
        with fits.open(f, memmap=False) as h:
            d = h[1].data; tz = float(h[1].header.get('TIMEZERO', 0.0))
            nb = d['XeCntPcu0'].shape[1]; dt = 128.0 / nb
            t0 = np.asarray(d['Time'], float) + tz
            tb = (t0[:, None] + dt * np.arange(nb)[None, :]).ravel()
            cnt = sum(np.asarray(d[f'XeCntPcu{int(p)}'], float) for p in pcus).ravel()
            t_all.append(tb); c_all.append(cnt)
    if not t_all: raise FileNotFoundError('no Standard-1 file')
    tb, cnt = np.concatenate(t_all), np.concatenate(c_all)
    o = np.argsort(tb); tb, cnt = tb[o], cnt[o]
    ing = np.zeros(len(tb), bool)
    for a, b in gti: ing |= (tb >= a) & (tb + dt <= b)
    tb, cnt = tb[ing], cnt[ing]
    nper = int(round(1.0 / dt)); T0 = np.floor(tb[0]) if len(tb) else 0
    k = np.floor((tb - T0) / 1.0).astype(int)
    df = pd.DataFrame(dict(k=k, c=cnt)).groupby('k').agg(c=('c', 'sum'), n=('c', 'size'))
    df = df[df.n == nper]
    return T0 + df.index.values + 0.5, df.c.values / 1.0


def state_rms(obs_id, path_src, path_bkg, burst_met):
    """0.1-4 Hz fractional rms (signed sqrt of the median over 128-s rows of the all-pairs cospectral variance,
    Fourier indices V7_RMS_J), rows with >= 2 PCUs on only, rows overlapping a burst interval removed."""
    import v5lib as L5, v6lib as L6
    rec = dict(obs_id=obs_id)
    try:
        s, bk = read_pha(fix(path_src)), read_pha(fix(path_bkg))
        cnt = bk['counts'].sum()
        rate = cnt if str(bk['unit']).lower().replace(' ', '').endswith('/s') else cnt / bk['exposure']
        b_pcu = rate / bk['npcu']
        rows, t0 = std1_rows_with_time(obs_id, s['gti'])
        a, b = C.V7_RMS_J; N = L5.N
        vals, n_burst = [], 0
        for i in range(rows.shape[1]):
            if any((t0[i] < y) and (t0[i] + N * L5.DT > x) for x, y in burst_met): n_burst += 1; continue
            row5 = rows[:, i]; on = np.where(L5.pcus_on(row5))[0]
            if len(on) < 2: continue
            x = row5[on]; sx = x.mean(1) - b_pcu * L5.DT
            if (sx <= 0).any(): continue
            X = np.fft.rfft(x, axis=1); S = X.sum(0)
            cross = (np.abs(S) ** 2 - (np.abs(X) ** 2).sum(0)) / 2.0 / L5.SINC2
            den = (sx.sum() ** 2 - (sx ** 2).sum()) / 2.0
            vals.append(2.0 / N**2 * cross[a:b + 1].sum() / den)
        rec.update(n_rows_in_gti=rows.shape[1], n_rows_burst_removed=n_burst, n_rows_used=len(vals))
        if len(vals) < C.V7_STATE_MIN_ROWS:
            rec.update(rms=np.nan, state='unknown'); return rec
        f = float(np.median(vals)); r = float(np.sign(f) * np.sqrt(abs(f)))
        rec.update(rms=r, state='hard-like' if r > C.V7_RMS_HARD else ('soft-like' if r < C.V7_RMS_SOFT else 'intermediate'))
    except Exception as e:
        rec.update(rms=np.nan, state='unknown', error=f'{type(e).__name__}: {e}'[:150])
    return rec


def std1_rows_with_time(obs_id, gti):
    """Like v5lib.std1_rows but also returns the start time (MET) of every kept row."""
    import v5lib as L5
    rows, ts = [], []
    for f in std1_files(obs_id):
        with fits.open(f, memmap=False) as h:
            d = h[1].data; tz = float(h[1].header.get('TIMEZERO', 0.0))
            if d['XeCntPcu0'].shape[1] != L5.N: continue
            t0 = np.asarray(d['Time'], float) + tz
            ok = np.zeros(len(t0), bool)
            for a, b in gti: ok |= (t0 >= a - 1e-3) & (t0 + L5.N * L5.DT <= b + 1e-3)
            if ok.any():
                rows.append(np.stack([np.asarray(d[f'XeCntPcu{p}'], float)[ok] for p in range(5)])); ts.append(t0[ok])
    if not rows: return np.zeros((5, 0, L5.N)), np.zeros(0)
    return np.concatenate(rows, axis=1), np.concatenate(ts)


def boot_draws(src_labels, n_boot=None, seed=None):
    """Class-stratified source draws identical to v4lib.paired_bootstrap / 09_bootstrap_sources.py."""
    n_boot = n_boot or C.N_BOOT; rng = np.random.default_rng(C.SEED if seed is None else seed)
    bh = np.sort([s for s, l in src_labels.items() if l == 'BH']); ns = np.sort([s for s, l in src_labels.items() if l == 'NS'])
    return [np.r_[rng.choice(bh, len(bh)), rng.choice(ns, len(ns))] for _ in range(n_boot)]


def auc_ba(y, s, w=None):
    """Observation-level AUC (Mann-Whitney with weights) and balanced accuracy at 0.5; NaN if a class is absent."""
    y = np.asarray(y).astype(bool); s = np.asarray(s, float); w = np.ones(len(y)) if w is None else np.asarray(w, float)
    if y.sum() == 0 or (~y).sum() == 0: return np.nan, np.nan
    o = np.argsort(s, kind='mergesort'); s_, y_, w_ = s[o], y[o], w[o]
    # weighted rank-sum with ties
    uniq, inv = np.unique(s_, return_inverse=True)
    wn_cum = np.cumsum(np.bincount(inv, weights=w_ * ~y_))          # NS weight up to each unique score
    wn_eq = np.bincount(inv, weights=w_ * ~y_)
    below = wn_cum - wn_eq
    auc = float(((below[inv] + 0.5 * wn_eq[inv]) * w_ * y_).sum() / ((w_ * y_).sum() * (w_ * ~y_).sum()))
    p = s >= 0.5
    ba = 0.5 * ((w * (p & y)).sum() / (w * y).sum() + (w * (~p & ~y)).sum() / (w * ~y).sum())
    return auc, float(ba)


def utc_to_met(mjd_utc, mjdref):
    return (Time(np.atleast_1d(mjd_utc), format='mjd', scale='utc').tt.mjd - mjdref) * 86400.0


# ------------------------------------------------------------------ v7c2 models (importable for joblib workers)
class C2Model:
    """LR / RF (v2 settings), KNN (standardised, prior-corrected to equal classes), SVM (standardised, balanced, sigmoid of
    the decision function)."""
    def __init__(self, alg, cfg=None): self.alg, self.cfg = alg, dict(cfg or {})

    def fit(self, X, y):
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.svm import SVC
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import make_pipeline
        a = self.alg; self.pi = float(np.mean(y))
        if a == 'LR': self.m = make_pipeline(StandardScaler(), LogisticRegression(**C.LR_PARAMS)).fit(X, y)
        elif a == 'RF': self.m = RandomForestClassifier(**dict(C.RF_PARAMS, n_jobs=1)).fit(X, y)
        elif a == 'KNN': self.m = make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=self.cfg['k'])).fit(X, y)
        else: self.m = make_pipeline(StandardScaler(), SVC(C=self.cfg['C'], gamma=self.cfg['gamma'], class_weight='balanced')).fit(X, y)
        return self

    def score(self, X):
        from scipy.special import expit
        if self.alg == 'SVM': return expit(self.m.decision_function(X))
        p = self.m.predict_proba(X)[:, 1]
        if self.alg == 'KNN':
            q1, q0 = p / self.pi, (1 - p) / (1 - self.pi); return q1 / (q1 + q0)
        return p


def c2_capped(df, cap, seed):
    rng = np.random.default_rng(seed)
    return pd.concat([d if len(d) <= cap else d.iloc[np.sort(rng.choice(len(d), cap, replace=False))] for _, d in df.groupby('source', sort=True)])


def c2_src_auc(scores, df):
    s = pd.DataFrame(dict(s=scores, y=df.y.values, g=df.source.values)).groupby('g').agg(s=('s', 'mean'), y=('y', 'first'))
    y, v = s.y.values.astype(bool), s.s.values
    if y.sum() == 0 or (~y).sum() == 0: return np.nan
    return float((v[y][:, None] > v[~y][None, :]).mean() + 0.5 * (v[y][:, None] == v[~y][None, :]).mean())


def c2_outer(test_src, data, alg, cols, grid, cap, seed):
    """One outer LOSO fold; KNN/SVM hyperparameters chosen by inner LOSO source AUC on the (capped) training sources."""
    tr = c2_capped(data[data.source != test_src], cap, seed); te = data[data.source == test_src]
    cfg, inner = None, []
    if alg in grid:
        best = (-1.0, None)
        if alg == 'SVM':      # inner grouped 5-fold over training sources (compute deviation, see decision_log); KNN: inner LOSO
            from sklearn.model_selection import GroupKFold
            splits = [(tr.source.values[i_te][0], i_tr, i_te) for i_tr, i_te in GroupKFold(n_splits=5).split(tr, tr.y, tr.source)]
        else:
            splits = [(s, np.where((tr.source != s).values)[0], np.where((tr.source == s).values)[0]) for s in tr.source.unique()]
        for c in grid[alg]:
            sc = np.full(len(tr), np.nan)
            for _, itr, ite in splits:
                if len(np.unique(tr.y.values[itr])) < 2: continue
                sc[ite] = C2Model(alg, c).fit(tr[cols].values[itr], tr.y.values[itr]).score(tr[cols].values[ite])
            a = c2_src_auc(sc, tr); inner.append(dict(test_source=test_src, alg=alg, cfg=str(c), inner_source_AUC=a))
            if a > best[0] + 1e-12: best = (a, c)
        cfg = best[1]
    s = C2Model(alg, cfg).fit(tr[cols].values, tr.y.values).score(te[cols].values)
    return test_src, alg, str(cfg), s, inner


def c2_outer_cached(cache_file, test_src, data, alg, cols, grid, cap, seed):
    """c2_outer with an on-disk cache (one file per task / algorithm / feature set / held-out source) so that an
    interrupted run resumes; identical results (deterministic inputs and seeds)."""
    import joblib, os
    if os.path.exists(cache_file): return joblib.load(cache_file)
    out = c2_outer(test_src, data, alg, cols, grid, cap, seed)
    tmp = cache_file + '.part'; joblib.dump(out, tmp); os.replace(tmp, cache_file)
    return out
