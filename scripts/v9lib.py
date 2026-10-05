"""v9 helpers (preregistration_v9.md): NICER cleaned event files read as a streamed, time-ordered prefix; MPU all-pairs
cospectrum timing features (ratio of means over 128-s segments), colours, nu_c; v4 burst rules on the 1-s light curve."""
import zlib, hashlib, json, datetime
import numpy as np, pandas as pd
import requests
from astropy.io import fits
import config as C
from common import ROOT, _LOCK
import os
from pathlib import Path
EXT = Path(os.environ.get('XRB_EXTERNAL_RAW', Path.home()/'xrb-pilot-data/raw'))

N = int(round(C.V9_SEG_S / C.V9_DT)) if hasattr(C, 'V9_SEG_S') else 32768
JJ = np.arange(N // 2 + 1)
SINC2 = np.sinc(JJ / N) ** 2
FORMAT_BYTES = {'L': 1, 'B': 1, 'I': 2, 'J': 4, 'K': 8, 'E': 4, 'D': 8, 'A': 1}


# ------------------------------------------------------------------ FITS header / row parsing from a byte stream
def _read_headers(buf):
    """Parse the primary and first extension headers from the start of a decompressed FITS byte buffer.
    Returns (ext_header, data_start) or (None, None) if the buffer is still too short."""
    pos, hdrs = 0, []
    while len(hdrs) < 2:
        start = pos
        while True:
            if pos + 2880 > len(buf): return None, None
            blk = bytes(buf[pos:pos + 2880]); pos += 2880
            if any(blk[i:i + 8] == b'END     ' for i in range(0, 2880, 80)): break
        hdrs.append(fits.Header.fromstring(bytes(buf[start:pos]).decode('ascii', 'replace')))
    return hdrs[1], pos


def row_dtype(h, want=('TIME', 'PI', 'DET_ID')):
    """numpy dtype (big endian, with offsets) selecting the wanted columns of a FITS binary table row."""
    names, formats, offsets, off = [], [], [], 0
    for k in range(1, h['TFIELDS'] + 1):
        name, tf = h[f'TTYPE{k}'].strip(), h[f'TFORM{k}'].strip()
        rep = int(''.join(ch for ch in tf if ch.isdigit()) or 1); code = ''.join(ch for ch in tf if ch.isalpha())
        size = (rep + 7) // 8 if code == 'X' else rep * FORMAT_BYTES[code]
        if name in want:
            assert rep == 1, name
            names.append(name); formats.append({'D': '>f8', 'I': '>i2', 'B': 'u1', 'J': '>i4', 'E': '>f4', 'K': '>i8'}[code]); offsets.append(off)
        off += size
    assert off == h['NAXIS1'], (off, h['NAXIS1'])
    return np.dtype(dict(names=names, formats=formats, offsets=offsets, itemsize=off))


class PrefixParser:
    """Incremental gzip -> FITS EVENTS rows (TIME, PI, DET_ID)."""
    def __init__(self):
        self.z = zlib.decompressobj(16 + zlib.MAX_WBITS); self.buf = bytearray(); self.h = None; self.dt = None
        self.cols = {'TIME': [], 'PI': [], 'DET_ID': []}; self.nrows = 0

    def feed(self, chunk):
        self.buf += self.z.decompress(chunk)
        if self.h is None:
            h, start = _read_headers(self.buf)
            if h is None: return
            self.h, self.dt = h, row_dtype(h); del self.buf[:start]
        rs = self.dt.itemsize; n = len(self.buf) // rs
        n = min(n, self.h['NAXIS2'] - self.nrows)
        if n > 0:
            a = np.frombuffer(bytes(self.buf[:n * rs]), dtype=self.dt)
            for k in self.cols: self.cols[k].append(np.array(a[k]))
            del self.buf[:n * rs]; self.nrows += n

    def arrays(self):
        out = {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in self.cols.items()}
        out['TIME'] = out['TIME'].astype(float); out['PI'] = out['PI'].astype(np.int32); out['DET_ID'] = out['DET_ID'].astype(np.int32)
        return out

    @property
    def complete(self):
        return self.h is not None and self.nrows >= self.h['NAXIS2']


def good_intervals(t, gap=None):
    gap = gap or C.V9_GAP_S
    if len(t) < 2: return np.zeros((0, 2))
    br = np.where(np.diff(t) > gap)[0]
    starts = np.r_[t[0], t[br + 1]]; ends = np.r_[t[br], t[-1]]
    return np.c_[starts, ends]


def n_segments(t):
    g = good_intervals(t); L = C.V9_SEG_S
    return int(np.floor((g[:, 1] - g[:, 0]) / L).sum()) if len(g) else 0


def _curl(args):
    import subprocess
    return subprocess.run(['curl', '-sS', '-L', '--connect-timeout', '30', '--speed-limit', '20000', '--speed-time', '60'] + args,
                          capture_output=True)


def stream_prefix(url, relative, chunk=16 << 20):
    """relative: path under XRB_EXTERNAL_RAW (default ~/xrb-pilot-data/raw; outside the OneDrive repo, as v4b1)."""
    """Download the start of a gzipped NICER event file until >= V9_TARGET_SEG gap-free segments, EOF or V9_CAP_BYTES, in
    16-MB HTTP range requests with curl (requests/urllib streams were ~0.1 MB/s here). Saves the compressed prefix to
    ROOT/relative (+ .json metadata) and logs URL, bytes, SHA256 in logs/downloads.jsonl. 404 -> FileNotFoundError."""
    import time as _t
    path = EXT/relative; path.parent.mkdir(parents=True, exist_ok=True)
    meta = path.with_name(path.name + '.json')
    if path.exists() and meta.exists(): return json.loads(meta.read_text())
    hd = _curl(['-I', url]).stdout.decode('ascii', 'replace')
    code = [l for l in hd.splitlines() if l.startswith('HTTP/')]
    if not code or ' 404' in code[-1] or ' 403' in code[-1]: raise FileNotFoundError(f'not found {url}')   # S3: 403 for a missing key
    size = [int(l.split(':')[1]) for l in hd.splitlines() if l.lower().startswith('content-length:')]
    total = size[-1] if size else None
    p = PrefixParser(); h = hashlib.sha256(); nbytes = 0; reason = 'cap'
    tmp = path.with_name(path.name + '.part'); piece = path.with_name(path.name + '.piece')
    with open(tmp, 'wb') as f:
        while nbytes < C.V9_CAP_BYTES and (total is None or nbytes < total):
            end = min(nbytes + chunk, C.V9_CAP_BYTES) - 1
            for k in range(4):
                r = _curl(['-f', '-r', f'{nbytes}-{end}', '-o', str(piece), url])
                if r.returncode == 0: break
                if k == 3: raise RuntimeError(f'curl failed ({r.returncode}): {r.stderr.decode(errors="replace")[:150]}')
                _t.sleep(5)
            data = piece.read_bytes()
            if not data: reason = 'eof'; break
            f.write(data); h.update(data); nbytes += len(data); p.feed(data)
            if p.complete or (total is not None and nbytes >= total): reason = 'eof'; break
            if p.nrows and n_segments(np.concatenate(p.cols['TIME'])) >= C.V9_TARGET_SEG: reason = 'target segments'; break
    if piece.exists(): piece.unlink()
    tmp.replace(path)
    info = dict(url=url, path='XRB_EXTERNAL_RAW/' + relative, bytes=nbytes, sha256=h.hexdigest(), file_bytes=total, stop=reason, rows=p.nrows,
                naxis2=int(p.h['NAXIS2']) if p.h is not None else None, utc=datetime.datetime.now(datetime.UTC).isoformat(),
                tool='curl range requests (prefix)')
    meta.write_text(json.dumps(info))
    with _LOCK, (ROOT/'logs/downloads.jsonl').open('a', encoding='utf-8') as fl: fl.write(json.dumps(info) + '\n')
    return info


def read_prefix(path):
    """Re-parse a saved compressed prefix (deterministic)."""
    p = PrefixParser()
    with open(path, 'rb') as f:
        while True:
            ch = f.read(1 << 20)
            if not ch: break
            try: p.feed(ch)
            except zlib.error: break                    # truncated stream end
    return p.arrays(), p.h, p.complete


# ------------------------------------------------------------------ bursts (v4 rules, copied from 17_v4_burst_detect.events)
def burst_events(t, r):
    P = C.V4_BURST
    mu, sd = r.mean(), r.std()
    cand = np.where(r > mu + P['nsigma'] * sd)[0]
    ev = []
    for i in cand:
        if ev and t[i] - t[ev[-1][-1]] < P['merge_gap_s']: ev[-1].append(i)
        else: ev.append([i])
    out = []
    for e in ev:
        i0 = e[0]; ip = e[int(np.argmax(r[e]))]; tp, peak = t[ip], r[ip]
        pre = (t >= t[i0] - P['pre_window_s']) & (t < t[i0])
        pers = np.median(r[pre]) if pre.sum() >= P['pre_window_s'] else np.median(r)
        A = peak - pers
        lvl25, lvl50, lvl10 = pers + .25 * A, pers + .5 * A, pers + .1 * A
        before = np.where((t < tp) & (r < lvl25))[0]; after50 = np.where((t > tp) & (r < lvl50))[0]
        after10 = np.where((t > tp) & (r < lvl10))[0]
        rise = tp - t[before[-1]] if len(before) else np.nan
        decay = t[after50[0]] - tp if len(after50) else np.nan
        n25, j = 1, ip
        while j - 1 >= 0 and t[j] - t[j - 1] < 1.5 and r[j - 1] > lvl25: n25 += 1; j -= 1
        j = ip
        while j + 1 < len(t) and t[j + 1] - t[j] < 1.5 and r[j + 1] > lvl25: n25 += 1; j += 1
        start = t[before[-1]] if len(before) else t[0]; end = t[after10[0]] if len(after10) else t[-1]
        ok = (pers > 0 and peak >= P['min_peak_ratio'] * pers) and (np.isfinite(rise) and rise <= P['max_rise_s']) and \
             (np.isfinite(decay) and P['decay_half_min_s'] <= decay <= P['decay_half_max_s']) and n25 >= P['min_bins_above_25pct']
        out.append(dict(t_peak=tp, peak_ratio=peak / pers if pers > 0 else np.nan, rise_s=rise, decay_half_s=decay,
                        burst_start=start, burst_end=end, auto_burst=bool(ok)))
    return out


def lc_1s(t, gi):
    """1-s light curve from event times t inside good intervals gi (complete 1-s bins only)."""
    tb, rb = [], []
    for a, b in gi:
        n = int(np.floor(b - a))
        if n < 1: continue
        e = np.arange(n + 1) + a
        c, _ = np.histogram(t[(t >= a) & (t < a + n)], bins=e)
        tb.append(e[:-1] + 0.5); rb.append(c.astype(float))
    if not tb: return np.zeros(0), np.zeros(0)
    return np.concatenate(tb), np.concatenate(rb)


# ------------------------------------------------------------------ features
NUC_K = 13
NUC_J = [(2 ** k, 2 ** (k + 1) - 1) for k in range(NUC_K)]          # j / 128 s: 1/128-2/128 ... 32-64 Hz
NUC_NU = np.array([2 ** (k + 0.5) / C.V9_SEG_S for k in range(NUC_K)]) if hasattr(C, 'V9_SEG_S') else None


def segment_stats(x):
    """x: (n_mpu_on, N) counts. Returns dict of numerators per band/bin and the denominator (ratio-of-means pieces)."""
    s = x.mean(1)
    X = np.fft.rfft(x, axis=1); S = X.sum(0)
    cross = (np.abs(S) ** 2 - (np.abs(X) ** 2).sum(0)) / 2.0 / SINC2
    den = (s.sum() ** 2 - (s ** 2).sum()) / 2.0
    out = dict(den=den)
    bands = dict(C.V9_T_BANDS_J); bands['STATE'] = C.V9_STATE_J; bands['WHITE'] = C.V9_WHITE_J
    for k, (a, b) in bands.items(): out[f'num_{k}'] = 2.0 / N ** 2 * cross[a:b + 1].sum()
    for i, (a, b) in enumerate(NUC_J): out[f'num_nu{i}'] = 2.0 / N ** 2 * cross[a:b + 1].sum()
    return out


def obs_features(arr, gap=None, return_segments=False):
    """Per-observation NICER features from parsed events (dict TIME, PI, DET_ID). Returns a record (status 'ok' or reason).
    return_segments=True (added for v10, default unchanged) also returns the per-segment statistics DataFrame."""
    t, pi, det = arr['TIME'], arr['PI'], arr['DET_ID']
    rec = dict(n_events=len(t))
    if len(t) < 100: rec['status'] = 'missing (no events)'; return rec
    if np.any(np.diff(t) < 0):
        o = np.argsort(t, kind='mergesort'); t, pi, det = t[o], pi[o], det[o]; rec['sorted_here'] = True
    gi = good_intervals(t, gap)
    lo, hi = C.V9_PI_TIMING; m = (pi >= lo) & (pi < hi)
    tt, mpu = t[m], det[m] // 10
    # bursts on the 1-s 2-10 keV light curve
    tb, rb = lc_1s(tt, gi)
    ev = burst_events(tb, rb) if len(tb) > 30 else []
    bursts = [(e['burst_start'] - C.V9_BURST_PRE_S, e['burst_end'] + C.V9_BURST_POST_S) for e in ev if e['auto_burst']]
    rec['n_bursts'] = len(bursts)
    L = C.V9_SEG_S; sub = N // C.V9_BLOCKS
    segs, n_burst_seg = [], 0
    cA = cB = cC = 0; nseg = 0
    for a, b in gi:
        s0 = a
        while s0 + L <= b:
            if any((s0 < y) and (s0 + L > x) for x, y in bursts): n_burst_seg += 1; s0 += L; continue
            i0, i1 = np.searchsorted(tt, [s0, s0 + L])
            k = np.floor((tt[i0:i1] - s0) / C.V9_DT).astype(np.int64); mm = mpu[i0:i1].astype(np.int64)
            okk = (k >= 0) & (k < N) & (mm >= 0) & (mm <= 6)
            x = np.bincount(mm[okk] * N + k[okk], minlength=7 * N).reshape(7, N).astype(float)
            on = np.where((x.reshape(7, C.V9_BLOCKS, sub).sum(2) > 0).all(1))[0]
            if len(on) >= C.V9_MIN_MPUS:
                st = segment_stats(x[on]); st['rate'] = x[on].sum() / L; st['n_on'] = len(on); segs.append(st)
                j0, j1 = np.searchsorted(t, [s0, s0 + L]); pp = pi[j0:j1]
                cA += int(((pp >= C.V9_PI_BANDS['A'][0]) & (pp < C.V9_PI_BANDS['A'][1])).sum())
                cB += int(((pp >= C.V9_PI_BANDS['B'][0]) & (pp < C.V9_PI_BANDS['B'][1])).sum())
                cC += int(((pp >= C.V9_PI_BANDS['C'][0]) & (pp < C.V9_PI_BANDS['C'][1])).sum())
                nseg += 1
            s0 += L
    rec.update(n_seg=nseg, n_seg_burst_removed=n_burst_seg, good_time_s=float((gi[:, 1] - gi[:, 0]).sum()) if len(gi) else 0.0)
    if nseg < C.V9_MIN_SEG:
        rec['status'] = f'missing (< {C.V9_MIN_SEG} valid segments)'
        return (rec, pd.DataFrame(segs)) if return_segments else rec
    S = pd.DataFrame(segs); D = S.den.sum()
    rate = float(S.rate.mean()); rec.update(rate_2_10=rate, mean_n_mpu=float(S.n_on.mean()), cA=cA, cB=cB, cC=cC,
                                           c1=cB / cA if cA else np.nan, c2=cC / cB if cB else np.nan)
    for k in list(C.V9_T_BANDS_J) + ['STATE', 'WHITE']:
        R = float(S[f'num_{k}'].sum() / D); n = len(S)
        se = float(np.sqrt(((S[f'num_{k}'] - R * S.den) ** 2).sum() * n / max(n - 1, 1)) / D)
        rec[f'{k}_var'] = R; rec[f'{k}_se'] = se; rec[k] = float(np.sign(R) * np.sqrt(abs(R)))
    lb = np.array([S[f'num_nu{i}'].sum() / D for i in range(NUC_K)])
    tot = float(np.sqrt(max(lb.sum(), 0)))
    w = np.maximum(lb, 0)
    rec['rms_nuc_band'] = tot
    rec['nu_c'] = float(np.exp((w * np.log(NUC_NU)).sum() / w.sum())) if (tot >= C.V6_NUC_MIN_RMS and w.sum() > 0) else np.nan
    for i in range(NUC_K): rec[f'lb{i}'] = float(lb[i])
    r = rec['STATE']
    rec['state'] = 'hard-like' if r > C.V7_RMS_HARD else ('soft-like' if r < C.V7_RMS_SOFT else 'intermediate')
    rec['status'] = 'ok' if rate >= C.V9_MIN_RATE else f'excluded (2-10 keV rate {rate:.1f} < {C.V9_MIN_RATE})'
    return (rec, S) if return_segments else rec
