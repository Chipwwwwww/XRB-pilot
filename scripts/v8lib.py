"""v8 helpers (preregistration_v8.md): stratified observation-level metrics with the v7a source bootstrap,
MINBAR burst intervals for external observations, and the event-mode high-frequency (4-1024 Hz) all-pairs cospectrum."""
import re, glob
import numpy as np, pandas as pd
from astropy.io import fits
import config as C
from common import ROOT
from spectra import read_pha
import v7lib as L7


# ------------------------------------------------------------------ stratified metrics (v7a procedure)
def strat_boot(o, groups, draws):
    """o: OOF frame (obs_id, source_id, true_label, BH_score). groups: obs_id -> stratum label (obs not in the map are
    ignored). draws: list of source-name arrays (v7lib.boot_draws over the WHOLE sample). Returns
    {stratum: (point (auc, ba), boot array (n_draws, 2))}; NaN when a class is absent in a draw."""
    o = o.assign(g=o.obs_id.map(groups)).dropna(subset=['g'])
    out = {}
    for gname, d in o.groupby('g'):
        per = {s: (dd.true_label.eq('BH').values, dd.BH_score.values.astype(float)) for s, dd in d.groupby('source_id')}
        pt = L7.auc_ba(d.true_label.eq('BH'), d.BH_score)
        B = np.full((len(draws), 2), np.nan)
        for i, dr in enumerate(draws):
            parts = [per[s] for s in dr if s in per]
            if not parts: continue
            y = np.concatenate([p[0] for p in parts]); s = np.concatenate([p[1] for p in parts])
            B[i] = L7.auc_ba(y, s)
        out[gname] = (np.array(pt, float), B)
    return out


def summarize(point, boot):
    v = boot[np.isfinite(boot)]
    return dict(point=float(point), ci2_5=float(np.percentile(v, 2.5)) if len(v) else np.nan,
                ci97_5=float(np.percentile(v, 97.5)) if len(v) else np.nan, n_valid_draws=int(len(v)))


def verdict(r):
    return 'difference (CI excludes 0)' if (r['ci2_5'] > 0 or r['ci97_5'] < 0) else 'not detected'


# ------------------------------------------------------------------ MINBAR burst intervals (external observations)
def minbar_intervals(path_src, obs_id, src_ra, src_dec, bursts, msrc, fov_deg=1.0):
    """MET intervals [start - V7_BURST_PRE_S, start + dur] of MINBAR bursts overlapping the spectrum GTIs that pass the
    v7b1 field-of-view rule (same ObsID, or burst origin within fov_deg of the source)."""
    utc, gti, mjdref, s = L7.gti_utc(path_src)
    out = []
    for i in L7.bursts_in_gti(bursts, utc):
        bb = bursts.iloc[i]
        d = float(L7.sep_deg(msrc.loc[bb['name']].ra, msrc.loc[bb['name']].dec, src_ra, src_dec)) if bb['name'] in msrc.index else np.nan
        if bb.obsid == obs_id or (np.isfinite(d) and d <= fov_deg):
            m0 = float(L7.utc_to_met(bb.t0, mjdref)[0])
            out.append((m0 - C.V7_BURST_PRE_S, m0 + float(bb.dur_used)))
    return out


# ------------------------------------------------------------------ event-mode high-frequency timing (v8c)
def mode_qualifies(hdr):
    """Event-file rule of preregistration_v8.md sec. 5 (header of the XTE_SE extension)."""
    mode = str(hdr.get('DATAMODE', '')).strip(); tddes = str(hdr.get('TDDES2', ''))
    has_pcu = any(str(hdr.get(f'TTYPE{k}', '')).strip().upper() == 'PCUID' for k in range(1, 10))
    return bool(re.match(C.V8_HF_MODE_REGEX, mode)) and (C.V8_HF_CHAINS in tddes) and \
        float(hdr.get('TIMEDEL', 1.0)) <= C.V8_HF_MAX_TIMEDEL + 1e-12 and has_pcu


def read_events(files):
    """Concatenate (TIME, PCUID) of the event files; GTI = intersection of all GTI extensions within a file, union over files."""
    t, p, gtis = [], [], []
    for f in files:
        with fits.open(f, memmap=False) as h:
            d = h[1].data
            t.append(np.asarray(d['TIME'], float)); p.append(np.asarray(d['PCUID'], np.int16))
            g = None
            for e in h[2:]:
                if e.name.upper().startswith(('GTI', 'STDGTI')):
                    gg = np.c_[np.asarray(e.data.field(0), float), np.asarray(e.data.field(1), float)]
                    g = gg if g is None else intersect(g, gg)
            if g is None: g = np.array([[float(h[1].header['TSTART']), float(h[1].header['TSTOP'])]])
            gtis.append(g)
    t, p = np.concatenate(t), np.concatenate(p)
    o = np.argsort(t, kind='mergesort')
    return t[o], p[o], union(np.concatenate(gtis))


def intersect(a, b):
    out = []
    for x0, x1 in a:
        for y0, y1 in b:
            lo, hi = max(x0, y0), min(x1, y1)
            if hi > lo: out.append((lo, hi))
    return np.array(out).reshape(-1, 2)


def union(g):
    g = g[np.argsort(g[:, 0])]; out = []
    for a, b in g:
        if out and a <= out[-1][1]: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return np.array(out).reshape(-1, 2)


DT = C.V8_HF_DT if hasattr(C, 'V8_HF_DT') else 2.0 ** -12
NSEG = int(round(C.V8_HF_SEG_S / DT)) if hasattr(C, 'V8_HF_SEG_S') else 65536
JJ = np.arange(NSEG // 2 + 1)
SINC2_HF = np.sinc(JJ / NSEG) ** 2
BANDS_HF = C.V8_HF_BANDS_J if hasattr(C, 'V8_HF_BANDS_J') else {}


def segments(gti, burst_met):
    """Start times of 16-s segments (aligned to the DT grid) lying completely inside one GTI interval and not overlapping
    any burst interval."""
    L = NSEG * DT; out = []
    for a, b in gti:
        s = np.ceil(a / DT) * DT
        while s + L <= b + 1e-9:
            if not any((s < y) and (s + L > x) for x, y in burst_met): out.append(s)
            s += L
    return np.array(out)


def hf_from_events(t, p, gti, b_pcu, burst_met=()):
    """Per-segment fractional band variances (all-pairs cospectrum, binning-corrected) from events (t MET, p PCU id).
    b_pcu: background counts/s per PCU (subtracted from each PCU's mean). Returns DataFrame (one row per valid segment)."""
    rows = []
    sub = int(round(1.0 / DT))
    for s0 in segments(gti, burst_met):
        i0, i1 = np.searchsorted(t, [s0, s0 + NSEG * DT])
        if i1 - i0 == 0: continue
        k = np.floor((t[i0:i1] - s0) / DT).astype(np.int64); pp = p[i0:i1].astype(np.int64)
        ok = (k >= 0) & (k < NSEG) & (pp >= 0) & (pp <= 4)
        x = np.bincount(pp[ok] * NSEG + k[ok], minlength=5 * NSEG).reshape(5, NSEG).astype(float)
        on = np.where((x.reshape(5, -1, sub).sum(2) > 0).all(1))[0]
        if len(on) < 2: continue
        x = x[on]; sx = x.mean(1) - b_pcu * DT
        if (sx <= 0).any(): continue
        X = np.fft.rfft(x, axis=1); S = X.sum(0)
        cross = (np.abs(S) ** 2 - (np.abs(X) ** 2).sum(0)) / 2.0 / SINC2_HF
        den = (sx.sum() ** 2 - (sx ** 2).sum()) / 2.0
        r = dict(t0=s0, n_on=len(on), src_rate_per_pcu=float(sx.mean() / DT), tot_rate_per_pcu=float(x.mean() / DT))
        for kb, (a, b) in BANDS_HF.items(): r[kb] = 2.0 / NSEG ** 2 * cross[a:b + 1].sum() / den
        rows.append(r)
    return pd.DataFrame(rows)


def hf_summary(seg):
    """Per-observation summary: mean over segments, signed-sqrt features, null-band z, QC status."""
    rec = dict(n_seg=len(seg))
    if len(seg) == 0:
        rec['status'] = 'missing (0 valid segments)'; return rec
    for kb in BANDS_HF:
        m, sd = float(seg[kb].mean()), float(seg[kb].std(ddof=1)) if len(seg) > 1 else np.nan
        rec[f'{kb}_var'] = m; rec[f'{kb}_se'] = sd / np.sqrt(len(seg)) if len(seg) > 1 else np.nan
        rec[kb] = float(np.sign(m) * np.sqrt(abs(m)))
    rec['NULL_z'] = rec['NULL_var'] / rec['NULL_se'] if rec.get('NULL_se') else np.nan
    for kb in ('HF1', 'HF2', 'HF3'): rec[f'{kb}_z'] = rec[f'{kb}_var'] / rec[f'{kb}_se'] if rec.get(f'{kb}_se') else np.nan
    rec.update(mean_n_on=float(seg.n_on.mean()), src_rate_per_pcu=float(seg.src_rate_per_pcu.mean()),
               tot_rate_per_pcu=float(seg.tot_rate_per_pcu.mean()), exposure_s=len(seg) * NSEG * DT)
    if len(seg) < C.V8_HF_MIN_SEG: rec['status'] = f'missing (< {C.V8_HF_MIN_SEG} valid segments)'
    elif not np.isfinite(rec['NULL_z']) or abs(rec['NULL_z']) > C.V8_HF_MAX_NULL_Z: rec['status'] = 'excluded (null band |z| > %g)' % C.V8_HF_MAX_NULL_Z
    else: rec['status'] = 'ok'
    return rec


def event_files(obs_id):
    return sorted(glob.glob(str(ROOT/f'data/raw/events/{obs_id}/*.evt.gz')))


def hf_features(obs_id, path_src, path_bkg, burst_met=()):
    """Per-observation HF features from the downloaded qualifying event files (preregistration_v8.md sec. 5)."""
    rec = dict(obs_id=obs_id)
    try:
        fs = event_files(obs_id)
        if not fs:
            rec['status'] = 'missing (no qualifying event file)'; return rec
        s, bk = read_pha(L7.fix(path_src)), read_pha(L7.fix(path_bkg))
        cnt = bk['counts'].sum()
        rate = cnt if str(bk['unit']).lower().replace(' ', '').endswith('/s') else cnt / bk['exposure']
        b_pcu = rate / bk['npcu']
        t, p, g_ev = read_events(fs)
        gti = intersect(union(np.asarray(s['gti'], float)), g_ev)
        seg = hf_from_events(t, p, gti, b_pcu, burst_met)
        rec.update(bkg_rate_per_pcu=b_pcu, n_event_files=len(fs), n_events=len(t))
        rec.update(hf_summary(seg))
    except Exception as e:
        rec['status'] = f'error: {type(e).__name__}: {e}'[:200]
    return rec


# ------------------------------------------------------------------ source-level bootstrap arrays (same draws as v4lib)
def src_boot(oofs, ref, n_boot=2000, seed=42):
    """Like v4lib.paired_bootstrap but returns the raw arrays: {name: (point (3,), boot (n_boot, 3))}, metrics in
    v4lib.METRICS order (source BA, source AUC, observation BA). Draws: sorted BH / NS names of ref, default_rng(seed)."""
    import v4lib as L
    tabs = {k: L.src_table(v) for k, v in oofs.items()}
    t0 = tabs[ref]
    bh = np.sort(t0.index[t0.true_label == 'BH'].values); ns = np.sort(t0.index[t0.true_label == 'NS'].values)
    rng = np.random.default_rng(seed)
    draws = [np.r_[rng.choice(bh, len(bh)), rng.choice(ns, len(ns))] for _ in range(n_boot)]
    order = np.r_[bh, ns]; out = {}
    for k, t in tabs.items():
        assert set(t.index) == set(order), f'{k}: source set differs from reference'
        t = t.loc[order]; pos = {s: i for i, s in enumerate(t.index)}
        idx = np.array([[pos[x] for x in d] for d in draws]); bhm = (t.true_label == 'BH').values[idx]
        i0 = np.arange(len(order))[None, :]
        out[k] = (L._boot_metrics(t, i0, (t.true_label == 'BH').values[i0])[0], L._boot_metrics(t, idx, bhm))
    return out


# ------------------------------------------------------------------ downloads with curl (same logging as common.download)
def download_curl(url, relative, retries=3):
    """Like common.download (skip if present; log URL, bytes, SHA256 to logs/downloads.jsonl) but streams with curl,
    which is several times faster than urllib for the large event files on this machine."""
    import subprocess, hashlib, json, datetime, time
    from common import _LOCK
    path = ROOT/relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): return path
    tmp = path.with_name(path.name + '.part')
    for attempt in range(retries):
        r = subprocess.run(['curl', '-sS', '-f', '-L', '--retry', '3', '--connect-timeout', '30', '-o', str(tmp), url], capture_output=True, text=True)
        if r.returncode == 0: break
        if attempt == retries - 1: raise RuntimeError(f'curl failed ({r.returncode}): {r.stderr.strip()[:200]}')
        time.sleep(3)
    tmp.replace(path)
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    with _LOCK, (ROOT/'logs/downloads.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(url=url, path=relative, bytes=path.stat().st_size, sha256=h.hexdigest(),
                                utc=datetime.datetime.now(datetime.UTC).isoformat(), tool='curl')) + '\n')
    return path
