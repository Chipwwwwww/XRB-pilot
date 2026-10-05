"""v8c (preregistration_v8.md sec. 5): event-mode high-frequency timing for the hard-like observations of S1 (v7a states) and
of the external set X (42_v8_states_timing.py).
1. Survey: SE*.evt.gz files in each pca/ directory, header read with an HTTP range request; qualifying rule v8lib.mode_qualifies;
   if several qualifying modes, the mode with the largest total size (all its files).
2. Download to data/raw/events/<obs>/ (v8lib.download_curl: URL, bytes, SHA256 in logs/downloads.jsonl).
3. HF features (v8lib.hf_features): 2^-12 s bins, 16-s segments, all-pairs cospectrum, bands LC/HF1/HF2/HF3/NULL; burst
   intervals as v7a for S1 (MINBAR FOV rule + v4 candidates) and MINBAR only for X.
4. Checks: null-band QC fraction (stop if > 20% of S1 observations with a qualifying file fail) and IC4 (LC vs v6 T3*,
   Spearman >= 0.90 on S1-HF, else stop).
Outputs: results/v8c/event_survey.csv, data/v8c/processed/hf_features.csv, results/v8c/ic4_lc_vs_t3.csv."""
import os, sys, re, time, zlib
os.environ['XRB_VERSION'] = 'v8c'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress, download
import numpy as np, pandas as pd, requests
from astropy.io import fits
from joblib import Parallel, delayed
from concurrent.futures import ThreadPoolExecutor
from scipy.stats import spearmanr
import config as C
import v7lib as L7, v8lib as L8

T0 = time.time()
R8, D8 = ROOT/'results/v8c', ROOT/'data/v8c/processed'
for p in (R8, D8): p.mkdir(parents=True, exist_ok=True)


def obs_table(v):
    o = pd.read_csv(ROOT/f'data/{v}/observations.csv', dtype={'obs_id': str}, low_memory=False)
    return o[o.in_dataset.astype(str).str.lower().eq('true')]


# ---------------- observations: S1 hard-like + X hard-like ----------------
s1 = obs_table('v2'); st = pd.read_csv(ROOT/'results/v7a/states.csv', dtype={'obs_id': str})
s1 = s1.merge(st[['obs_id', 'state']], on='obs_id'); s1 = s1[s1.state == 'hard-like'].assign(sample='S1', role='S1')
X = pd.read_csv(ROOT/'data/v8b/processed/external_states_timing.csv', dtype={'obs_id': str})
X = X[X.state == 'hard-like']
xs = pd.concat([obs_table(v) for v in ('v4b2', 'v6', 'v7b2', 'v8b')]).drop_duplicates('obs_id')
X = X[['obs_id', 'sample', 'role']].merge(xs, on='obs_id').assign(sample='X')
O = pd.concat([s1, X], ignore_index=True)[['obs_id', 'source_id', 'label', 'sample', 'role', 'url_base', 'path_src', 'path_bkg']]
print(O.groupby(['sample', 'label']).agg(n=('obs_id', 'size'), src=('source_id', 'nunique')).to_string(), flush=True)


# ---------------- 1. survey ----------------
def peek(url, nbytes=100000):
    for k in range(4):                                # transient network errors: retry (survey must be deterministic)
        try:
            r = requests.get(url, headers={'Range': f'bytes=0-{nbytes - 1}'}, timeout=60); r.raise_for_status(); break
        except requests.RequestException:
            if k == 3: raise
            time.sleep(5)
    d = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(r.content)
    hdrs, pos = [], 0
    while len(hdrs) < 2 and pos < len(d):
        start = pos
        while pos < len(d):
            blk = d[pos:pos + 2880]; pos += 2880
            if any(blk[i:i + 8] == b'END     ' for i in range(0, len(blk), 80)): break
        hdrs.append(fits.Header.fromstring(d[start:pos].decode('ascii', 'replace')))
    return hdrs[1]


def size_mb(s):
    m = re.match(r'([\d.]+)([KMG]?)', s); return float(m.group(1)) * {'': 1e-6, 'K': 1e-3, 'M': 1.0, 'G': 1e3}[m.group(2)]


def survey(r):
    base = r.url_base.replace('stdprod/', 'pca/')
    idx = download(base, f'data/raw/std1/{r.obs_id}/pca_index.html').read_text(errors='ignore')
    out = []
    for name, size in re.findall(r'href="(SE\d*_[^"]+\.evt\.gz)">[^<]*</a>\s+\S+\s+\S+\s+([\d.]+[KMG]?)', idx):
        rec = dict(obs_id=r.obs_id, file=name, url=base + name, size_MB=size_mb(size))
        try:
            h = peek(base + name)
            rec.update(mode=str(h.get('DATAMODE', '')).strip(), tddes2=str(h.get('TDDES2', '')), timedel=float(h.get('TIMEDEL', np.nan)),
                       qualifies=L8.mode_qualifies(h))
        except Exception as e:
            rec.update(mode=f'ERROR {type(e).__name__}', qualifies=False)
        out.append(rec)
    return out or [dict(obs_id=r.obs_id, file=None, qualifies=False)]


with ThreadPoolExecutor(8) as ex:
    sv = pd.DataFrame([x for xx in ex.map(survey, O.itertuples()) for x in xx])
sel = []
for o, d in sv[sv.qualifies == True].groupby('obs_id'):
    best = d.groupby('mode').size_MB.sum().idxmax()
    sel.append(d[d['mode'] == best].assign(chosen=True))
sv = sv.merge(pd.concat(sel)[['obs_id', 'file', 'chosen']], on=['obs_id', 'file'], how='left').fillna({'chosen': False})
sv = sv.merge(O[['obs_id', 'source_id', 'label', 'sample', 'role']], on='obs_id')
sv.to_csv(R8/'event_survey.csv', index=False)
ch = sv[sv.chosen == True]
print(f'\nsurvey: {sv.obs_id.nunique()} obs, {ch.obs_id.nunique()} with a qualifying event file, {ch.size_MB.sum():.0f} MB to download '
      f'({time.time() - T0:.0f} s)\n' + ch.groupby('mode').agg(n=('file', 'size'), MB=('size_MB', 'sum')).to_string(), flush=True)

# ---------------- 2. download ----------------
with ThreadPoolExecutor(10) as ex:            # curl streams (urllib was ~0.1 MB/s here; see decision_log)
    list(ex.map(lambda r: L8.download_curl(r.url, f'data/raw/events/{r.obs_id}/{r.file}'), ch.itertuples()))
print(f'download done ({time.time() - T0:.0f} s)', flush=True)

# ---------------- 3. HF features ----------------
hits = pd.read_csv(ROOT/'results/v7b1/minbar_bursts_in_gti.csv', dtype={'obs_id': str}); hits = hits[hits.in_fov]
cand = pd.read_csv(ROOT/'results/v4/burst_candidates.csv', dtype={'obs_id': str})
vis = pd.read_csv(ROOT/'results/v4/burst_visual.csv', dtype={'obs_id': str}); visb = set(vis[vis.visual != 'not_burst'].obs_id)


def intervals_s1(r):                                  # identical to 34_v7a_states.intervals
    out = []
    h = hits[hits.obs_id == r.obs_id]
    if len(h):
        _, _, mjdref, _ = L7.gti_utc(r.path_src)
        m0 = L7.utc_to_met(h.burst_time_mjd.values, mjdref)
        out += [(a - C.V7_BURST_PRE_S, a + d) for a, d in zip(m0, h.dur_used_s.values)]
    c = cand[(cand.obs_id == r.obs_id) & ((cand.auto_burst == True) | cand.obs_id.isin(visb))]
    out += [(a - C.V7_BURST_PRE_S, b) for a, b in zip(c.burst_start, c.burst_end)]
    return out


bursts, msrc = L7.load_minbar(), L7.load_minbar_sources()
pos = pd.concat([pd.read_csv(ROOT/f'data/{v}/sources.csv')[['source_id', 'ra_deg', 'dec_deg']] for v in ('v4b2', 'v6', 'v7b2', 'v8b')]).drop_duplicates('source_id').set_index('source_id')
iv = []
for r in O.itertuples():
    if r.sample == 'S1': iv.append(intervals_s1(r))
    else: iv.append(L8.minbar_intervals(r.path_src, r.obs_id, float(pos.loc[r.source_id].ra_deg), float(pos.loc[r.source_id].dec_deg), bursts, msrc))
recs = Parallel(n_jobs=8, batch_size=1)(delayed(L8.hf_features)(r.obs_id, r.path_src, r.path_bkg, b) for r, b in zip(O.itertuples(), iv))
hf = O[['obs_id', 'source_id', 'label', 'sample', 'role']].merge(pd.DataFrame(recs), on='obs_id')
hf['n_burst_intervals'] = [len(b) for b in iv]
hf.to_csv(D8/'hf_features.csv', index=False)
print(f'\nHF features ({time.time() - T0:.0f} s):\n' + hf.groupby(['sample', 'status']).size().to_string(), flush=True)

# ---------------- 4. checks ----------------
s1f = hf[(hf['sample'] == 'S1') & hf.obs_id.isin(ch.obs_id)]
nfail = int(s1f.status.astype(str).str.startswith('excluded').sum())
frac = nfail / max(len(s1f), 1)
print(f'null-band QC: {nfail}/{len(s1f)} S1 observations with a qualifying file excluded ({frac:.3f}; stop if > {C.V8_HF_MAX_NULL_FAIL_FRAC})')
print('null z (S1, valid segments): median %.2f, |z|>3: %d' % (np.nanmedian(s1f.NULL_z), int((s1f.NULL_z.abs() > 3).sum())))
T6 = pd.read_csv(ROOT/'data/v6/processed/timing_v6.csv', dtype={'obs_id': str}).set_index('obs_id')
ok = hf[(hf['sample'] == 'S1') & (hf.status == 'ok')].join(T6[['T3s']], on='obs_id').dropna(subset=['LC', 'T3s'])
rho = spearmanr(ok.LC, ok.T3s)[0] if len(ok) > 2 else np.nan
ic = pd.DataFrame([dict(check='IC4 LC (1-4 Hz, events) vs v6 T3* (1-4 Hz, Standard-1), S1-HF', n=len(ok), spearman=rho,
                        threshold=C.V8_HF_MIN_SPEARMAN_LC, passed=bool(rho >= C.V8_HF_MIN_SPEARMAN_LC)),
                   dict(check='null-band QC failure fraction (S1 obs with qualifying file)', n=len(s1f), spearman=frac,
                        threshold=C.V8_HF_MAX_NULL_FAIL_FRAC, passed=bool(frac <= C.V8_HF_MAX_NULL_FAIL_FRAC))])
ic.to_csv(R8/'ic4_lc_vs_t3.csv', index=False)
print(ic.round(4).to_string(index=False))
good = hf[hf.status == 'ok']
print('\nS1-HF:', good[good['sample'] == 'S1'].groupby('label').agg(n=('obs_id', 'size'), src=('source_id', 'nunique')).to_dict(),
      '\nX-HF:', good[good['sample'] == 'X'].groupby(['label']).agg(n=('obs_id', 'size'), src=('source_id', 'nunique')).to_dict())
progress('v8c_events', f"S1-HF {int((good['sample'] == 'S1').sum())} obs; IC4 rho {rho:.3f}; null QC fail {frac:.3f}")
if not ic.passed.all():
    print('IMPLEMENTATION CHECK FAILED -> v8c stops (preregistration_v8 sec. 5)'); sys.exit(3)
