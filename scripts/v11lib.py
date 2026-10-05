"""v11 helpers (preregistration_v11.md): stream a NICER cleaned event file (HEASARC AWS mirror, 64-MB range requests, up to
V10_FULL_CAP_BYTES) straight into the frozen v9/v10 feature pipeline without storing the raw bytes (URL, bytes, SHA256 logged);
per-log-bin standard errors; zero-centred Lorentzian fits to the 13 log-bin fractional variances."""
import json, hashlib, datetime, time
import numpy as np, pandas as pd
from scipy.optimize import least_squares
import config as C
from common import ROOT, _LOCK
import v9lib as L9, v10lib as L10


def head(url):
    hd = L9._curl(['-I', url]).stdout.decode('ascii', 'replace')
    code = [l for l in hd.splitlines() if l.startswith('HTTP/')]
    if not code or ' 404' in code[-1] or ' 403' in code[-1]: raise FileNotFoundError(f'not found {url}')
    size = [int(l.split(':')[1]) for l in hd.splitlines() if l.lower().startswith('content-length:')]
    return size[-1] if size else None


def stream_events(url):
    """Parse the whole file (or its first V10_FULL_CAP_BYTES) from range requests held in memory only."""
    total = head(url); cap = min(total, C.V10_FULL_CAP_BYTES) if total else C.V10_FULL_CAP_BYTES
    from concurrent.futures import ThreadPoolExecutor
    p = L9.PrefixParser(); h = hashlib.sha256(); pos = 0
    ranges = [(a, min(a + C.V11_STREAM_CHUNK, cap) - 1) for a in range(0, cap, C.V11_STREAM_CHUNK)]

    def get(rg):
        for k in range(4):
            r = L9._curl(['-f', '-r', f'{rg[0]}-{rg[1]}', url])
            if r.returncode == 0 and len(r.stdout) == rg[1] - rg[0] + 1: return r.stdout
            if k == 3: raise RuntimeError(f'curl failed ({r.returncode}) for range {rg}: {r.stderr.decode(errors="replace")[:150]}')
            time.sleep(5)
    W = C.V11_RANGE_CONCURRENCY
    with ThreadPoolExecutor(W) as ex:
        for i in range(0, len(ranges), W):                      # windows of W concurrent requests, consumed in order
            for d in ex.map(get, ranges[i:i + W]):
                h.update(d); p.feed(d); pos += len(d)
            if p.complete: break
    info = dict(url=url, bytes=pos, sha256=h.hexdigest(), file_bytes=total, complete=bool(p.complete), rows=p.nrows,
                utc=datetime.datetime.now(datetime.UTC).isoformat(), tool='curl range requests, streamed (raw bytes not stored; v11)')
    with _LOCK, (ROOT/'logs/downloads.jsonl').open('a', encoding='utf-8') as fl: fl.write(json.dumps(info) + '\n')
    return p.arrays(), info


def lb_se(S):
    """Ratio-of-means fractional variance and delta-method SE for each of the 13 log bins."""
    D = S.den.sum(); n = len(S); out = {}
    for i in range(L9.NUC_K):
        num = S[f'num_nu{i}']; R = num.sum() / D
        out[f'lb{i}_se'] = float(np.sqrt(((num - R * S.den) ** 2).sum() * n / max(n - 1, 1)) / D) if n > 1 else np.nan
    return out


def obs_features_stream(url):
    arr, info = stream_events(url)
    rec, S = L9.obs_features(arr, return_segments=True)
    rec = dict(rec, bkg_ratio_12_15=L10.bkg_ratio(arr), bytes=info['bytes'], file_bytes=info['file_bytes'], read_complete=info['complete'],
               sha256=info['sha256'], url=url)
    if rec.get('status') == 'ok': rec.update(lb_se(S))
    return rec


# ------------------------------------------------------------------ Lorentzian fits (13 log bins, 1/128 - 64 Hz)
LB_LO = np.array([(a - 0.5) / C.V9_SEG_S for a, b in L9.NUC_J]); LB_HI = np.array([(b + 0.5) / C.V9_SEG_S for a, b in L9.NUC_J])


def lor_int(r2, d):
    """Integrated fractional variance of a zero-centred Lorentzian (total variance r2, half width d) in each bin."""
    return r2 * (2.0 / np.pi) * (np.arctan(LB_HI / d) - np.arctan(LB_LO / d))


def fit_lorentz(lb, se):
    """Weighted least squares with 1 and 2 zero-centred Lorentzians; returns dict with nu_L (lowest width), BIC choice."""
    lb, se = np.asarray(lb, float), np.asarray(se, float)
    ok = np.isfinite(lb) & np.isfinite(se) & (se > 0)
    if ok.sum() < 6: return dict(nu_L=np.nan, n_lor=0, fit='too few bins')
    y, s = lb[ok], se[ok]; lo, hi = np.log(C.V11_LORENTZ_NU[0]), np.log(C.V11_LORENTZ_NU[1])
    m1 = lambda p: lor_int(np.exp(p[0]), np.exp(p[1]))[ok]
    m2 = lambda p: (lor_int(np.exp(p[0]), np.exp(p[1])) + lor_int(np.exp(p[2]), np.exp(p[3])))[ok]
    tot = max(np.nansum(np.clip(y, 0, None)), 1e-6)
    best1 = None
    for d0 in np.log([0.03, 0.3, 3.0, 30.0]):
        r = least_squares(lambda p: (m1(p) - y) / s, [np.log(tot), d0], bounds=([np.log(1e-8), lo], [np.log(10.0), hi]))
        if best1 is None or r.cost < best1.cost: best1 = r
    best2 = None
    for d1, d2 in ((0.03, 1.0), (0.1, 3.0), (0.3, 10.0), (1.0, 30.0)):
        r = least_squares(lambda p: (m2(p) - y) / s, [np.log(tot / 2), np.log(d1), np.log(tot / 2), np.log(d2)],
                          bounds=([np.log(1e-8), lo, np.log(1e-8), lo], [np.log(10.0), hi, np.log(10.0), hi]))
        if best2 is None or r.cost < best2.cost: best2 = r
    n = int(ok.sum()); chi1, chi2 = 2 * best1.cost, 2 * best2.cost
    bic1, bic2 = chi1 + 2 * np.log(n), chi2 + 4 * np.log(n)
    if bic1 - bic2 > C.V11_LORENTZ_DBIC:
        d = np.exp([best2.x[1], best2.x[3]]); r2 = np.exp([best2.x[0], best2.x[2]]); i = int(np.argmin(d))
        return dict(nu_L=float(d[i]), rms_L=float(np.sqrt(r2[i])), nu_L2=float(d[1 - i]), n_lor=2, chi2=chi2, bic1=bic1, bic2=bic2, n_bins=n)
    return dict(nu_L=float(np.exp(best1.x[1])), rms_L=float(np.sqrt(np.exp(best1.x[0]))), nu_L2=np.nan, n_lor=1, chi2=chi1, bic1=bic1, bic2=bic2, n_bins=n)
