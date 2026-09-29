"""Step 3b: download StdProd Std2 spectra for ranked candidates, apply pre-registered quality rules,
build common-energy-grid features. One accepted observation per time bin (max MAX_TRIES candidates per bin).
Outputs: data/observations.csv (every candidate tried, with status/reason), data/processed/features.npz,
         data/processed/feature_definitions.csv, results/attrition_download.csv"""
from common import *
from config import *
from spectra import *
import urllib.error, re, numpy as np, pandas as pd, traceback
from concurrent.futures import ThreadPoolExecutor
import config as _cfg
DEADTIME = getattr(_cfg, 'DEADTIME', 'xe_lower_bound')
VLE_DT_ALT = getattr(_cfg, 'VLE_DT_ALT', None)

MAX_TRIES = 6
AO_BY_PREFIX = {'5': 5, '6': 6, '7': 7, '8': 8, '90': 9, '91': 10, '92': 11, '93': 12, '94': 13, '95': 14, '96': 15}
_ao_cache = {}

def guess_ao(prop):
    return AO_BY_PREFIX.get(prop[:2], AO_BY_PREFIX.get(prop[0]))

def fetch(obs):
    prop = obs.split('-')[0]
    aos = [_ao_cache[prop]] if prop in _ao_cache else [guess_ao(prop)] + [a for a in range(4, 17) if a != guess_ao(prop)]
    o = obs.replace('-', '')
    last = None
    for ao in aos:
        base = f'{ARCHIVE}AO{ao}/P{prop}/{obs}/stdprod/'
        try:
            paths = {k: download(base + f, f'data/raw/spectra/{obs}/{f}') for k, f in
                     [('src', f'xp{o}_s2.pha.gz'), ('bkg', f'xp{o}_b2.pha.gz'), ('rsp', f'xp{o}.rsp.gz')]}
            _ao_cache[prop] = ao
            return base, paths
        except urllib.error.HTTPError as e:
            last = e
            if e.code != 404: raise
            if prop in _ao_cache: break
            # stop scanning AOs once the proposal directory itself is known to exist
    raise FileNotFoundError(f'StdProd Std2 files not found ({last})')

def sep_deg(ra1, dec1, ra2, dec2):
    r = np.radians
    c = np.sin(r(dec1))*np.sin(r(dec2)) + np.cos(r(dec1))*np.cos(r(dec2))*np.cos(r(ra1-ra2))
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))))

def std1_files(obs, base):
    obs_base = base.replace('stdprod/', '')
    idx = download(obs_base + 'pca/', f'data/raw/std1/{obs}/pca_index.html').read_text(errors='ignore')
    names = sorted(set(re.findall(r'href="(FS46_[^"]+\.gz)"', idx)))
    if not names: raise FileNotFoundError('no Standard-1 (FS46_*) file in pca/')
    return [download(obs_base + 'pca/' + n, f'data/raw/std1/{obs}/{n}') for n in names]

def deadtime(obs, base, s):
    xe_only = s['counts'].sum() / s['exposure'] / s['npcu'] * 1e-5      # good-xenon Std2 term only (v1 method)
    if DEADTIME != 'std1':
        return xe_only, dict(dtf_xe=xe_only, deadtime_method='std2_good_xenon_lower_bound')
    r = std1_rates(std1_files(obs, base), s['gti'])
    dtf, non = std1_dtf(r, s['pcus'])
    alt, _ = std1_dtf(r, s['pcus'], vle_dt=VLE_DT_ALT)
    return dtf, dict(dtf_xe=xe_only, dtf_std1=dtf, dtf_std1_vle150us=alt, std1_npcu_on=non,
                     std1_covered_s=r['covered'], std1_vle_rate_per_pcu=r['vle']/non,
                     deadtime_method='std1_gof_recipe')

# ---- common energy grid from the reference observation ----
ref = read_rsp(ROOT/f'data/raw/spectra/{REFERENCE_OBS}/xp{REFERENCE_OBS.replace("-", "")}.rsp.gz')
bounds = np.unique(np.r_[ref['ch_lo'], ref['ch_hi']])
lo_edge = bounds[np.argmin(abs(bounds - E_MIN))]; hi_edge = bounds[np.argmin(abs(bounds - E_MAX))]
EDGES = bounds[(bounds >= lo_edge) & (bounds <= hi_edge)]
WID = np.diff(EDGES); ECEN = np.sqrt(EDGES[:-1]*EDGES[1:])
print(f'Energy grid: {len(WID)} bins, {EDGES[0]:.3f}-{EDGES[-1]:.3f} keV (reference {REFERENCE_OBS})', flush=True)

sources = pd.read_csv(D/'sources.csv').set_index('source_id')
cand = pd.read_csv(D/'observation_candidates.csv', dtype={'obs_id': str})

def process_bin(sid, b, grp):
    rows, feats = [], []
    accepted = False
    for _, c in grp.sort_values('rank_in_bin').head(MAX_TRIES).iterrows():
        rec = dict(obs_id=c.obs_id, source_id=sid, label=c.label, time_bin=b, rank_in_bin=c.rank_in_bin,
                   mjd=c.mjd, cat_exposure=c.cat_exposure, cat_npcu=c.cat_npcu, cat_std1rate=c.cat_std1rate)
        try:
            base, P = fetch(c.obs_id)
            rec.update(url_base=base, path_src=str(P['src'].relative_to(ROOT)), path_bkg=str(P['bkg'].relative_to(ROOT)),
                       path_rsp=str(P['rsp'].relative_to(ROOT)))
            s, bk, rsp = read_pha(P['src']), read_pha(P['bkg']), read_rsp(P['rsp'])
            npcu = s['npcu']
            dtf, dinfo = deadtime(c.obs_id, base, s)
            dcor = 1.0 / (1.0 - dtf)
            net, err, rs, es, rb, eb = net_spectrum(s, bk, dcor)
            W = overlap_matrix(rsp['ch_lo'], rsp['ch_hi'], EDGES)
            per = lambda v: (W @ v) / npcu / WID                          # count/s/keV/PCU
            rate, rerr = per(net), np.sqrt((W**2) @ err**2) / npcu / WID
            srate, brate = per(rs), per(rb)
            F = np.sum(rate*WID); sF = np.sqrt(np.sum((rerr*WID)**2))
            S = np.sum(srate*WID); B = np.sum(brate*WID)
            soft = ECEN < 10
            pl2 = per(powerlaw_folded(rsp))
            gshift = max(abs(np.interp(E_MIN, rsp['ch_lo'], np.arange(len(rsp['ch_lo']))) - np.interp(E_MIN, ref['ch_lo'], np.arange(len(ref['ch_lo'])))),
                         abs(np.interp(E_MAX, rsp['ch_lo'], np.arange(len(rsp['ch_lo']))) - np.interp(E_MAX, ref['ch_lo'], np.arange(len(ref['ch_lo'])))))
            src_row = sources.loc[sid]
            rec.update(date_obs=s['date_obs'], obs_mjd_start=s['mjdref'] + s['tstart']/86400, exposure_s=s['exposure'],
                       bkg_exposure_s=bk['exposure'], pcus=s['pcus'], npcu=npcu, n_gti=s['ngti'], object_hdr=s['object'],
                       hdr_sep_deg=sep_deg(s['ra'], s['dec'], src_row.ra_deg, src_row.dec_deg),
                       src_unit=str(s['unit']), src_class=f"{s['hduclas2']}/{s['hduclas3']}", bkg_class=f"{bk['hduclas2']}/{bk['hduclas3']}",
                       poisserr=s['poisserr'], sys_err=s['sys_err'], backscal_ratio=s['backscal']/bk['backscal'],
                       rsp_detnam=rsp['detnam'], gain_shift_channels=gshift, dtf=dtf, dcor=dcor, **dinfo,
                       net_rate_5_25=F, net_rate_err=sF, net_snr=F/sF if sF > 0 else np.nan,
                       src_rate_5_25=S, bkg_rate_5_25=B, bkg_fraction=B/S if S > 0 else np.nan,
                       hardness_10_25_over_5_10=np.sum((rate*WID)[~soft])/np.sum((rate*WID)[soft]),
                       n_nonpositive_bins=int(np.sum(rate <= 0)))
            reasons = []
            if not np.all(np.isfinite(rate)) or not np.all(np.isfinite(rerr)): reasons.append('nonfinite')
            if s['exposure'] < MIN_SPEC_EXPOSURE_S: reasons.append('short_exposure')
            if not (F/sF >= MIN_NET_SNR): reasons.append('low_snr')
            if dtf > MAX_DTF: reasons.append('high_deadtime')
            if rec['hdr_sep_deg'] > COORD_TOL_DEG: reasons.append('coord_mismatch')
            if len(s['counts']) != 129 or len(rsp['ch_lo']) != 129: reasons.append('nonstandard_channels')
            if rsp['ch_lo'][0] > EDGES[0] or rsp['ch_hi'][-1] < EDGES[-1]: reasons.append('ebounds_coverage')
            if reasons:
                rec.update(status='excluded', reason=';'.join(reasons))
            else:
                rec.update(status='accepted', reason='')
                accepted = True
                feats.append(dict(obs_id=c.obs_id, rate=rate, err=rerr, srate=srate, brate=brate, pl2=pl2, F=F))
        except Exception as e:
            rec.update(status='excluded', reason=f'fetch_or_read_error: {type(e).__name__}: {e}'[:200])
            with (ROOT/'logs/04_errors.log').open('a') as f: f.write(c.obs_id + '\n' + traceback.format_exc() + '\n')
        rows.append(rec)
        if accepted: break
    print(sid, 'bin', b, 'accepted' if accepted else 'EMPTY', rec['obs_id'], rec.get('reason', ''), flush=True)
    return rows, feats

groups = list(cand.groupby(['source_id', 'time_bin'], sort=False))
with ThreadPoolExecutor(max_workers=4) as ex:     # network-bound; results keep input order
    results = list(ex.map(lambda x: process_bin(x[0][0], x[0][1], x[1]), groups))
rows = [r for rr, _ in results for r in rr]
feats = [f for _, ff in results for f in ff]

obs = pd.DataFrame(rows)
obs['in_dataset'] = obs.status.eq('accepted')
obs.to_csv(D/'observations.csv', index=False)
acc = obs[obs.in_dataset].reset_index(drop=True)
fd = {f['obs_id']: f for f in feats}
stack = lambda k: np.array([fd[o][k] for o in acc.obs_id])
rate, err = stack('rate'), stack('err')
F = acc.net_rate_5_25.values
np.savez_compressed(D/'processed/features.npz', rate=rate, err=err, srate=stack('srate'), brate=stack('brate'),
                    pl2=stack('pl2'), edges=EDGES, obs_id=acc.obs_id.values.astype(str), source_id=acc.source_id.values.astype(str),
                    y=(acc.label.values == 'BH').astype(int), F=F)
fdef = pd.DataFrame(dict(feature=[f'bin{k:02d}' for k in range(len(WID))], e_lo_keV=EDGES[:-1], e_hi_keV=EDGES[1:]))
fdef['A_definition'] = f'asinh(net_rate/{ASINH_SCALE}); net_rate in count/s/keV/PCU (deadtime-corrected net, not flux)'
fdef['B_definition'] = 'net_rate / F_5_25 ; F_5_25 = net count/s/PCU summed over grid; units 1/keV'
fdef.to_csv(D/'processed/feature_definitions.csv', index=False)
att = obs.groupby('source_id').agg(candidates_tried=('obs_id', 'size'), accepted=('in_dataset', 'sum'))
att['bins_empty'] = cand.groupby('source_id').time_bin.nunique().reindex(att.index) - att.accepted
att.to_csv(R/'attrition_download.csv')
print(att.to_string()); print(obs[~obs.in_dataset].reason.str.split(':').str[0].value_counts().to_string())
progress(f'3b_fetch_process_{VERSION}', f'{len(acc)} accepted observations; {len(obs)-len(acc)} excluded candidates logged')
