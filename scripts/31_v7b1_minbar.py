"""v7b1 step 1 (preregistration_v7.md §3, 1a-1c): MINBAR DR1 bursts vs the spectrum GTIs of the v2 observations
(and, with --sample, any other observation table). Contaminated = any MINBAR burst (any instrument, any origin)
whose interval [time, time + dur] (dur missing -> 300 s) overlaps a GTI. Cross-check with the frozen v4 Standard-1
detector (automatic rule and visual verdicts). Outputs results/v7b1/minbar_*.csv and figures/v7b1/*.png.
Usage: python 31_v7b1_minbar.py [--sample v7b2]  (default v2)"""
import os, sys
os.environ['XRB_VERSION'] = 'v7b1'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
import config as C
import v7lib as L7
from plotstyle import plt, INK, INK2

SAMPLE = sys.argv[sys.argv.index('--sample') + 1] if '--sample' in sys.argv else 'v2'
R7, FG = ROOT/'results/v7b1', ROOT/'figures/v7b1'
for p in (R7, FG): p.mkdir(parents=True, exist_ok=True)
SUF = '' if SAMPLE == 'v2' else f'_{SAMPLE}'
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)

b = L7.load_minbar(); mo = L7.load_minbar_obs(); ms = L7.load_minbar_sources()
obs = pd.read_csv(ROOT/f'data/{SAMPLE}/observations.csv', dtype={'obs_id': str}, low_memory=False)
obs = obs[obs.in_dataset.astype(str).str.lower().eq('true')].reset_index(drop=True)
srcpos = pd.read_csv(ROOT/f'data/{SAMPLE}/sources.csv').set_index('source_id')
FOV_DEG = 1.0     # PCA collimator: 1 deg FWHM (triangular response); post-hoc FOV restriction, see decision_log
missing_pos = sorted(set(b.name) - set(ms.index))
print('MINBAR burst names without a source-table position:', missing_pos, flush=True)
print(f'MINBAR: {len(b)} bursts ({b.instr.str.startswith("XP").sum()} RXTE/PCA), {len(mo)} observations; '
      f'{SAMPLE}: {len(obs)} observations', flush=True)

rows, hits = [], []
for r in obs.itertuples():
    utc, gti, mjdref, s = L7.gti_utc(r.path_src)
    idx = L7.bursts_in_gti(b, utc)
    same = b[b.obsid == r.obs_id]
    mrow = mo[mo.obsid == r.obs_id]
    sp = srcpos.loc[r.source_id]; n_fov = 0
    for i in idx:
        bb = b.iloc[i]
        d_or = float(L7.sep_deg(ms.loc[bb['name']].ra, ms.loc[bb['name']].dec, sp.ra_deg, sp.dec_deg)) if bb['name'] in ms.index else np.nan
        in_fov = bool(bb.obsid == r.obs_id or (np.isfinite(d_or) and d_or <= FOV_DEG)); n_fov += in_fov
        hits.append(dict(obs_id=r.obs_id, source_id=r.source_id, label=r.label, minbar_name=bb['name'], instr=bb.instr,
                         minbar_obsid=bb.obsid, burst_time_mjd=bb.t0, dur_used_s=bb.dur_used, sflag=bb.sflag, entry=int(bb.entry),
                         origin_sep_deg=d_or, same_obsid=bb.obsid == r.obs_id, in_fov=in_fov))
    rows.append(dict(obs_id=r.obs_id, source_id=r.source_id, label=r.label, gti_start_mjd=float(utc.min()), gti_stop_mjd=float(utc.max()),
                     n_minbar_in_gti_fov=n_fov,
                     gti_total_s=float(np.sum(np.diff(gti, axis=1))), n_minbar_in_gti=len(idx),
                     minbar_names_in_gti=';'.join(sorted({b.iloc[i]['name'] for i in idx})),
                     n_minbar_same_obsid=len(same), n_minbar_same_obsid_in_gti=int(np.isin(same.index, b.index[idx]).sum()),
                     minbar_obs_rows=len(mrow), minbar_obs_nburst=int(np.nansum(mrow.nburst.astype(float))) if len(mrow) else 0,
                     minbar_obs_names=';'.join(sorted(set(mrow.name))),
                     contaminated_minbar=n_fov > 0, contaminated_literal=len(idx) > 0))
fl = pd.DataFrame(rows); hi = pd.DataFrame(hits)
fl.to_csv(R7/f'minbar_flags{SUF}.csv', index=False); hi.to_csv(R7/f'minbar_bursts_in_gti{SUF}.csv', index=False)
print(f'\ncontaminated (PRIMARY: MINBAR burst in GTI from the same ObsID or an origin within {FOV_DEG} deg): '
      f'{int(fl.contaminated_minbar.sum())} of {len(fl)} ({fl[fl.contaminated_minbar].label.value_counts().to_dict()})')
print(f'contaminated (literal preregistered rule, any burst anywhere in the sky): {int(fl.contaminated_literal.sum())} '
      f'({fl[fl.contaminated_literal].label.value_counts().to_dict()}); bursts in GTIs: {len(hi)}, in FOV: {int(hi.in_fov.sum()) if len(hi) else 0}', flush=True)
print(fl[fl.contaminated_minbar].groupby(['label', 'source_id']).size().to_string())
if len(hi):
    print('\nbursts in GTI by origin (sep from our source position):')
    print(hi.groupby(['source_id', 'minbar_name', 'in_fov']).agg(n=('entry', 'size'), sep=('origin_sep_deg', 'min')).round(3).to_string())

# ---------------- 1c: cross-check with the frozen v4 Standard-1 detector ----------------
if SAMPLE == 'v2':
    v4 = pd.read_csv(ROOT/'results/v4/burst_flags.csv', dtype={'obs_id': str})
    vis = pd.read_csv(ROOT/'results/v4/burst_visual.csv', dtype={'obs_id': str})
    fl = fl.merge(v4[['obs_id', 'contains_burst_auto', 'n_bursts_auto']], on='obs_id', how='left')
    fl['std1_auto'] = fl.contains_burst_auto.fillna(False).astype(bool)
    fl['std1_visual'] = fl.obs_id.isin(set(vis[vis.visual != 'not_burst'].obs_id))
    fl.to_csv(R7/'minbar_flags.csv', index=False)
    agr = []
    for k in ('std1_auto', 'std1_visual'):
        ct = pd.crosstab(fl.contaminated_minbar, fl[k])
        a = dict(std1_set=k, both=int((fl.contaminated_minbar & fl[k]).sum()), minbar_only=int((fl.contaminated_minbar & ~fl[k]).sum()),
                 std1_only=int((~fl.contaminated_minbar & fl[k]).sum()), neither=int((~fl.contaminated_minbar & ~fl[k]).sum()))
        a['agreement'] = (a['both'] + a['neither']) / len(fl); agr.append(a)
    agr = pd.DataFrame(agr); agr.to_csv(R7/'minbar_vs_std1_agreement.csv', index=False)
    print('\nMINBAR vs Standard-1 (v4, frozen):\n' + agr.to_string(index=False))
    dis = fl[fl.contaminated_minbar != fl.std1_visual]
    print('\ndisagreements MINBAR vs v4 visual:\n' + dis[['obs_id', 'source_id', 'label', 'n_minbar_in_gti', 'n_minbar_in_gti_fov', 'minbar_names_in_gti',
                                                         'n_minbar_same_obsid', 'std1_auto', 'std1_visual']].to_string(index=False))
    # figures: every disagreement + 10 random agreements with a burst
    obs_i = obs.set_index('obs_id')
    agree_pos = fl[fl.contaminated_minbar & fl.std1_visual].obs_id.values
    pick = list(dis.obs_id) + list(np.random.default_rng(C.SEED).choice(agree_pos, min(10, len(agree_pos)), replace=False))
    for oid in pick:
        r = obs_i.loc[oid]; utc, gti, mjdref, s = L7.gti_utc(r.path_src)
        try: t, rate = L7.lightcurve_1s(oid, gti, s['pcus'])
        except Exception as e: print('no light curve', oid, e); continue
        fig, a = plt.subplots(figsize=(9, 2.6))
        a.plot(t - t[0], rate, color=INK, lw=.5)
        bb = b.iloc[L7.bursts_in_gti(b, utc)]
        for _, x in bb.iterrows():
            m0 = L7.utc_to_met(x.t0, mjdref)[0] - t[0]
            a.axvspan(m0, m0 + x.dur_used, color='#c2410c', alpha=.25, lw=0)
        f = fl.set_index('obs_id').loc[oid]
        a.set_title(f"{r.source_id} {oid}: MINBAR bursts in GTI {int(f.n_minbar_in_gti)} (in FOV {int(f.n_minbar_in_gti_fov)}; {f.minbar_names_in_gti}); "
                    f"v4 auto {bool(f.std1_auto)}, v4 visual {bool(f.std1_visual)}", loc='left', fontsize=7)
        a.set_xlabel('s since first 1-s bin (gaps = outside GTI)'); a.set_ylabel('count/s')
        tag = 'disagree' if oid in set(dis.obs_id) else 'agree'
        fig.savefig(FG/f'{tag}_{r.source_id}_{oid}.png', dpi=90); plt.close(fig)
progress(f'v7b1_minbar{SUF}', f"{int(fl.contaminated_minbar.sum())}/{len(fl)} {SAMPLE} observations contain a MINBAR burst in the spectrum GTIs")
