"""v4 burst leakage check, part 1 (preregistration_v4.md §3, 2a-2b): detect type-I bursts in the Standard-1 light
curves of the 456 v2 observations, inside the spectrum GTIs. Rule (Galloway+2008 sec. 2 + fixed shape rules):
1-s bins > mean + 4 sigma -> candidates (merged within 30 s) -> burst if peak >= 1.5 x persistent, rise <= 10 s,
decay to half amplitude within 3-300 s, >= 3 adjacent 1-s bins above 25% amplitude.
Light curve = sum of good-xenon counts (XeCntPcu*) over the PCUs used in the spectrum (ROWID keywords).
Outputs results/v4/burst_candidates.csv, results/v4/burst_flags.csv, figures/v4/burst_candidates/*.png"""
import os, sys, glob
os.environ['XRB_VERSION'] = 'v4'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
from spectra import read_pha
import config as C
import numpy as np, pandas as pd
from astropy.io import fits
from plotstyle import plt, INK, INK2

P = C.V4_BURST
R4, FG = ROOT/'results/v4', ROOT/'figures/v4/burst_candidates'
FG.mkdir(parents=True, exist_ok=True)
obs = pd.read_csv(ROOT/'data/v2/observations.csv', dtype={'obs_id': str})
obs = obs[obs.in_dataset.astype(str).str.lower().eq('true')].reset_index(drop=True)
fix = lambda p: ROOT / str(p).replace('\\', '/')


def lightcurve(obs_id, gti, pcus):
    """1-s light curve (count/s summed over spectrum PCUs), only complete 1-s bins inside the GTIs."""
    t_all, c_all = [], []
    for f in sorted(glob.glob(str(ROOT/f'data/raw/std1/{obs_id}/FS46_*.gz'))):
        with fits.open(f, memmap=False) as h:
            d = h[1].data; tz = float(h[1].header.get('TIMEZERO', 0.0))
            nb = d['XeCntPcu0'].shape[1]; dt = 128.0 / nb
            t0 = np.asarray(d['Time'], float) + tz
            tb = (t0[:, None] + dt * np.arange(nb)[None, :]).ravel()          # sub-bin start times
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


def events(t, r):
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
        # adjacent (time-contiguous) 1-s bins above 25% around the peak
        n25, j = 1, ip
        while j - 1 >= 0 and t[j] - t[j-1] < 1.5 and r[j-1] > lvl25: n25 += 1; j -= 1
        j = ip
        while j + 1 < len(t) and t[j+1] - t[j] < 1.5 and r[j+1] > lvl25: n25 += 1; j += 1
        start = t[before[-1]] if len(before) else t[0]; end = t[after10[0]] if len(after10) else t[-1]
        crit = dict(peak_ratio_ok=bool(pers > 0 and peak >= P['min_peak_ratio'] * pers),
                    rise_ok=bool(np.isfinite(rise) and rise <= P['max_rise_s']),
                    decay_ok=bool(np.isfinite(decay) and P['decay_half_min_s'] <= decay <= P['decay_half_max_s']),
                    width_ok=bool(n25 >= P['min_bins_above_25pct']))
        out.append(dict(t_peak=tp, peak_rate=peak, persistent_rate=pers, peak_ratio=peak / pers if pers > 0 else np.nan,
                        rise_s=rise, decay_half_s=decay, n_bins_above_25pct=n25, burst_start=start, burst_end=end,
                        n_candidate_bins=len(e), mean_rate=mu, sd_rate=sd, **crit, auto_burst=all(crit.values())))
    return out


cands, flags = [], []
for r in obs.itertuples():
    s = read_pha(fix(r.path_src))
    try:
        t, rate = lightcurve(r.obs_id, s['gti'], s['pcus'])
    except Exception as e:
        flags.append(dict(obs_id=r.obs_id, source_id=r.source_id, label=r.label, status=f'error: {e}'[:120])); continue
    ev = events(t, rate)
    for j, e in enumerate(ev): cands.append(dict(obs_id=r.obs_id, source_id=r.source_id, label=r.label, event=j, **e))
    nb = sum(e['auto_burst'] for e in ev)
    dur = sum(e['burst_end'] - e['burst_start'] for e in ev if e['auto_burst'])
    flags.append(dict(obs_id=r.obs_id, source_id=r.source_id, label=r.label, status='ok', n_1s_bins=len(t),
                      n_candidates=len(ev), n_bursts_auto=nb, contains_burst_auto=nb > 0,
                      burst_time_s=dur, exposure_s=s['exposure'], burst_fraction=dur / s['exposure']))
    if ev:
        fig, axes = plt.subplots(1, 1 + len(ev[:4]), figsize=(4 + 3 * len(ev[:4]), 2.6))
        axes = np.atleast_1d(axes)
        axes[0].plot(t - t[0], rate, color=INK, lw=.5)
        for e in ev: axes[0].axvline(e['t_peak'] - t[0], color='#c2410c' if e['auto_burst'] else '#9e9d98', lw=.8)
        axes[0].set_title(f'{r.source_id} {r.obs_id}', loc='left', fontsize=7); axes[0].set_xlabel('s')
        for a, e in zip(axes[1:], ev[:4]):
            m = (t > e['t_peak'] - 60) & (t < e['t_peak'] + 240)
            a.plot(t[m] - e['t_peak'], rate[m], color=INK, lw=.7); a.axhline(e['persistent_rate'], color=INK2, ls=':', lw=.7)
            a.set_title(f"{'AUTO BURST' if e['auto_burst'] else 'rejected'} x{e['peak_ratio']:.1f} rise {e['rise_s']:.0f}s "
                        f"decay {e['decay_half_s']:.0f}s", fontsize=6.5, loc='left', color='#c2410c' if e['auto_burst'] else INK2)
        fig.savefig(FG/f'{r.source_id}_{r.obs_id}.png', dpi=90); plt.close(fig)
    print(r.obs_id, r.source_id, len(t), 'bins', len(ev), 'candidates', nb, 'bursts', flush=True)

cdf, fdf = pd.DataFrame(cands), pd.DataFrame(flags)
cdf.to_csv(R4/'burst_candidates.csv', index=False); fdf.to_csv(R4/'burst_flags.csv', index=False)
print('\nstatus:', fdf.status.value_counts().to_dict())
print('candidates:', len(cdf), '; auto bursts:', int(cdf.auto_burst.sum()) if len(cdf) else 0,
      '; observations with >=1 auto burst:', int(fdf.contains_burst_auto.sum()))
print(fdf[fdf.contains_burst_auto == True].groupby(['label', 'source_id']).size().to_string())
progress('v4_burst_detect', f"{int(fdf.contains_burst_auto.sum())} of {len(fdf)} v2 observations contain an automatically detected burst")
