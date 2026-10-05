"""v10 helpers (preregistration_v10.md): NICER tail download (rest of the cleaned event file after the v9 prefix, up to 1 GB),
prefix + tail reading, split-half features from per-segment statistics, cross-instrument source identity, pooled stratified
bootstrap over the union of sources (v7a-type per component) and pooled label permutation (sources keep one label across
instruments)."""
import json, hashlib, datetime, subprocess, time
import numpy as np, pandas as pd
import config as C
from common import ROOT, _LOCK
import v7lib as L7, v8lib as L8, v9lib as L9

EXT = L9.EXT


# ------------------------------------------------------------------ NICER tail download / reading
def prefix_paths(obsid):
    base = EXT/f'nicer/{obsid}/ni{obsid}_0mpu7_cl.evt.gz.prefix'
    return base, base.with_name(base.name + '.json'), EXT/f'nicer_tail/{obsid}/ni{obsid}_0mpu7_cl.evt.gz.tail'


def download_tail(obsid, chunk=64 << 20):
    """Bytes [len(prefix), min(file, V10_FULL_CAP_BYTES)) of the event file, appended in 64-MB range requests (curl).
    Writes <tail> + <tail>.json (URL, offsets, bytes, SHA256 of the tail) and logs to logs/downloads.jsonl."""
    pre, pmeta, tail = prefix_paths(obsid)
    meta = tail.with_name(tail.name + '.json')
    if meta.exists(): return json.loads(meta.read_text())
    pm = json.loads(pmeta.read_text()); start = int(pm['bytes']); total = pm.get('file_bytes')
    end_excl = min(int(total), C.V10_FULL_CAP_BYTES) if total else C.V10_FULL_CAP_BYTES
    tail.parent.mkdir(parents=True, exist_ok=True); h = hashlib.sha256(); n = 0
    piece = tail.with_name(tail.name + '.piece'); tmp = tail.with_name(tail.name + '.part')
    with open(tmp, 'wb') as f:
        pos = start
        while pos < end_excl:
            e = min(pos + chunk, end_excl) - 1
            for k in range(4):
                r = L9._curl(['-f', '-r', f'{pos}-{e}', '-o', str(piece), pm['url']])
                if r.returncode == 0: break
                if k == 3: raise RuntimeError(f'curl failed ({r.returncode}): {r.stderr.decode(errors="replace")[:150]}')
                time.sleep(5)
            d = piece.read_bytes()
            if not d: break
            f.write(d); h.update(d); n += len(d); pos += len(d)
    if piece.exists(): piece.unlink()
    tmp.replace(tail)
    info = dict(url=pm['url'], path='XRB_EXTERNAL_RAW/' + str(tail.relative_to(EXT)).replace('\\', '/'), offset=start, bytes=n,
                sha256=h.hexdigest(), file_bytes=total, complete=bool(total and start + n >= int(total)),
                utc=datetime.datetime.now(datetime.UTC).isoformat(), tool='curl range requests (tail after v9 prefix)')
    meta.write_text(json.dumps(info))
    with _LOCK, (ROOT/'logs/downloads.jsonl').open('a', encoding='utf-8') as fl: fl.write(json.dumps(info) + '\n')
    return info


def read_full(obsid):
    """Parse prefix + tail as one gzip stream (same parser as v9)."""
    import zlib
    pre, _, tail = prefix_paths(obsid)
    p = L9.PrefixParser()
    for path in (pre, tail):
        if not path.exists(): continue
        with open(path, 'rb') as f:
            while True:
                ch = f.read(1 << 20)
                if not ch: break
                try: p.feed(ch)
                except zlib.error: break
    return p.arrays(), p.h, p.complete


def bkg_ratio(arr):
    pi = arr['PI']; lo, hi = C.V10_BKG_PI; a, b = C.V9_PI_TIMING
    n_b = int(((pi >= lo) & (pi < hi)).sum()); n_s = int(((pi >= a) & (pi < b)).sum())
    return n_b / n_s if n_s else np.nan


def half_features(S, idx):
    """T1-T3, STATE and nu_c (signed sqrt, ratio of means) from a subset of per-segment statistics."""
    S = S.iloc[idx]; D = S.den.sum(); out = {}
    for k in list(C.V9_T_BANDS_J) + ['STATE']:
        R = S[f'num_{k}'].sum() / D; out[k] = float(np.sign(R) * np.sqrt(abs(R)))
    lb = np.array([S[f'num_nu{i}'].sum() / D for i in range(L9.NUC_K)]); w = np.maximum(lb, 0)
    tot = float(np.sqrt(max(lb.sum(), 0)))
    out['nu_c'] = float(np.exp((w * np.log(L9.NUC_NU)).sum() / w.sum())) if (tot >= C.V6_NUC_MIN_RMS and w.sum() > 0) else np.nan
    return out


# ------------------------------------------------------------------ source identity
def canonical_map(rxte_pos, nicer_pos, tol=None):
    """rxte_pos: DataFrame(source_id, ra, dec, label); nicer_pos: DataFrame(name, ra, dec, label).
    Returns {rxte source_id: canonical name} (NICER name if within tol deg, else the RXTE id) and a match table."""
    tol = tol or C.V10_MATCH_DEG; rows = []
    for r in rxte_pos.itertuples():
        d = L7.sep_deg(nicer_pos.ra.values, nicer_pos.dec.values, r.ra, r.dec); k = int(np.argmin(d))
        m = d[k] <= tol
        rows.append(dict(rxte_source=r.source_id, rxte_label=r.label, nicer_name=nicer_pos.name.iloc[k] if m else None,
                         nicer_label=nicer_pos.label.iloc[k] if m else None, sep_deg=float(d[k]), canonical=nicer_pos.name.iloc[k] if m else r.source_id))
    t = pd.DataFrame(rows)
    return dict(zip(t.rxte_source, t.canonical)), t


# ------------------------------------------------------------------ pooled statistics
def pooled_boot(components, labels, n_boot=None, seed=None):
    """components: list of dict(name, A=oof frame, B=oof frame, groups=Series obs_id->stratum, stratum=str); source_id in the
    frames must be canonical names. labels: {source: 'BH'/'NS'} over the union. Difference A - B in observation-level AUC
    within the stratum, per component and pooled (equal-weight mean; NaN if any component is undefined in a draw)."""
    draws = L7.boot_draws(labels, n_boot, seed)
    pts, bts = [], []
    for c in components:
        sa = L8.strat_boot(c['A'], c['groups'], draws)[c['stratum']]; sb = L8.strat_boot(c['B'], c['groups'], draws)[c['stratum']]
        pts.append(sa[0][0] - sb[0][0]); bts.append(sa[1][:, 0] - sb[1][:, 0])
    P = np.array(pts); B = np.vstack(bts).T
    return P, B, float(P.mean()), B.mean(1)          # NaN propagates: draws with an undefined component are dropped


def pooled_perm(resids, labels, n_perm=None, seed=None):
    """resids: {instrument: Series(source -> mean residual)}; labels: {source: 'BH'/'NS'} (union). Statistic: mean over
    instruments of (mean BH residual - mean NS residual). Null: labels permuted within instrument-membership strata
    (fixed number of BH per stratum; a source keeps one label in all instruments)."""
    n_perm = n_perm or C.V10_N_PERM; rng = np.random.default_rng(C.SEED if seed is None else seed)
    names = np.sort(np.array(list(labels))); y = np.array([labels[s] == 'BH' for s in names]); nb = int(y.sum())
    pos = {s: i for i, s in enumerate(names)}
    R = {k: (np.array([pos[s] for s in v.dropna().index]), v.dropna().values) for k, v in resids.items()}

    def stat(yy):
        ds = []
        for ix, r in R.values():
            b = yy[ix]
            ds.append(r[b].mean() - r[~b].mean() if b.any() and (~b).any() else np.nan)
        return np.array(ds)
    D_inst = stat(y); D = float(np.nanmean(D_inst))
    # restricted permutation: labels are permuted within strata of instrument membership (RXTE only / NICER only / both),
    # keeping the number of BH per stratum fixed (decision_log v10: union-wide permutation lost power, synthetic test)
    sets = {k: set(ix.tolist()) for k, (ix, _) in R.items()}
    member = [tuple(k for k in R if i in sets[k]) for i in range(len(names))]
    strata = [np.array([i for i, m in enumerate(member) if m == u]) for u in sorted(set(member), key=str)]
    Dp = np.empty(n_perm)
    for i in range(n_perm):
        yy = np.zeros(len(names), bool)
        for st in strata:
            yy[st[rng.permutation(len(st))[:int(y[st].sum())]]] = True
        Dp[i] = np.nanmean(stat(yy))
    p = (1 + (np.abs(Dp) >= abs(D) - 1e-15).sum()) / (1 + n_perm)
    return dict(D=D, p=float(p), D_inst=dict(zip(R, D_inst)), null_sd=float(Dp.std()))
