"""v7a (preregistration_v7.md §4): state-conditional evaluation of the v2 LOSO OOF predictions.
2a state index: 0.1-4 Hz fractional rms (all-pairs cospectrum, >= 2 PCU rows, burst rows removed), RM06 Table 2
   thresholds (rms > 0.10 hard-like, < 0.075 soft-like, otherwise intermediate). 2b sanity check (stop if it fails).
2c observation-level AUC / balanced accuracy per state (H-LR, H-RF, B-LR, B-RF), source bootstrap; PRIMARY:
   H-LR soft-like AUC - hard-like AUC. Also on the MINBAR-excluded OOF (v7b1). 2d counts. 2e colour-overlap box
   (descriptive). 2f exploratory: LOSO trained and tested on hard-like observations only."""
import os, sys
os.environ['XRB_VERSION'] = 'v7a'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import LeaveOneGroupOut
import config as C
import v4lib as L, v7lib as L7
from plotstyle import plt, CLASS_COLOR, INK2

R7, FG = ROOT/'results/v7a', ROOT/'figures/v7a'
for p in (R7, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
STATES = ['soft-like', 'intermediate', 'hard-like']

obs = pd.read_csv(ROOT/'data/v2/observations.csv', dtype={'obs_id': str}, low_memory=False)
obs = obs[obs.in_dataset.astype(str).str.lower().eq('true')].reset_index(drop=True)
# burst intervals (MET) per observation: MINBAR (primary rule) + v4 Standard-1 candidates of visually confirmed bursts
hits = pd.read_csv(ROOT/'results/v7b1/minbar_bursts_in_gti.csv', dtype={'obs_id': str})
hits = hits[hits.in_fov]
cand = pd.read_csv(ROOT/'results/v4/burst_candidates.csv', dtype={'obs_id': str})
vis = pd.read_csv(ROOT/'results/v4/burst_visual.csv', dtype={'obs_id': str}); visb = set(vis[vis.visual != 'not_burst'].obs_id)


def intervals(r):
    out = []
    h = hits[hits.obs_id == r.obs_id]
    if len(h):
        _, _, mjdref, _ = L7.gti_utc(r.path_src)
        m0 = L7.utc_to_met(h.burst_time_mjd.values, mjdref)
        out += [(a - C.V7_BURST_PRE_S, a + d) for a, d in zip(m0, h.dur_used_s.values)]
    c = cand[(cand.obs_id == r.obs_id) & ((cand.auto_burst == True) | cand.obs_id.isin(visb))]
    out += [(a - C.V7_BURST_PRE_S, b) for a, b in zip(c.burst_start, c.burst_end)]
    return out


recs = Parallel(n_jobs=16, batch_size=4)(delayed(L7.state_rms)(r.obs_id, r.path_src, r.path_bkg, intervals(r)) for r in obs.itertuples())
st = obs[['obs_id', 'source_id', 'label']].merge(pd.DataFrame(recs), on='obs_id')
z = np.load(ROOT/'data/v2/processed/features.npz')
H = pd.DataFrame(L.v2_representations(z['rate'], z['edges'], z['F'])['H_colours'], columns=['c1', 'c2']).assign(obs_id=z['obs_id'])
st = st.merge(H, on='obs_id'); st.to_csv(R7/'states.csv', index=False)
print(st.state.value_counts().to_string()); print('rows removed for bursts:', int(st.n_rows_burst_removed.sum()))

# ---------------- 2b sanity check ----------------
k = st[st.state != 'unknown']
f1118 = (k[k.source_id == 'XTEJ1118+480'].state == 'hard-like').mean()
fz = (k[k.source_id.isin(C.V7_Z_SOURCES)].state == 'soft-like').mean()
san = pd.DataFrame([dict(check='XTE J1118+480 hard-like fraction', value=f1118, n=int((k.source_id == 'XTEJ1118+480').sum()), threshold=C.V7_SANITY_FRAC),
                    dict(check='Z sources (Cyg X-2, GX 17+2) soft-like fraction', value=fz, n=int(k.source_id.isin(C.V7_Z_SOURCES).sum()), threshold=C.V7_SANITY_FRAC)])
san['passed'] = san.value >= san.threshold; san.to_csv(R7/'sanity_check.csv', index=False)
print('\nSANITY CHECK:\n' + san.round(3).to_string(index=False))
srcs = sorted(st.source_id.unique(), key=lambda s: (st[st.source_id == s].label.iloc[0], s))
fig, axes = plt.subplots(4, 8, figsize=(18, 9), sharex=True, sharey=True)
for a, s in zip(axes.ravel(), srcs):
    d = st[st.source_id == s]; lab = d.label.iloc[0]
    a.scatter(d.c2, d.rms, s=10, color=CLASS_COLOR[lab]); a.axhline(C.V7_RMS_HARD, color=INK2, lw=.6, ls='--'); a.axhline(C.V7_RMS_SOFT, color=INK2, lw=.6, ls=':')
    a.set_title(f'{s} ({lab})', fontsize=7, loc='left')
for a in axes.ravel()[len(srcs):]: a.axis('off')
fig.supxlabel('hard colour F(16–25)/F(10–16)'); fig.supylabel('0.1–4 Hz fractional rms (all-pairs cospectrum)')
fig.suptitle('v7a sanity check: rms vs hard colour per source (dashed 0.10 = hard-like, dotted 0.075 = soft-like; RM06 Table 2)', x=.01, ha='left')
fig.savefig(FG/'v7a_rms_vs_colour_by_source.png'); plt.close(fig)
if not san.passed.all():
    progress('v7a_states', 'SANITY CHECK FAILED -> stopped (preregistration_v7 2b)'); print('SANITY CHECK FAILED -> stop'); sys.exit(3)

# ---------------- 2d counts ----------------
cnt = st.groupby(['state', 'label']).agg(n_obs=('obs_id', 'size'), n_sources=('source_id', 'nunique')).unstack(fill_value=0)
cnt.to_csv(R7/'state_counts.csv'); print('\n' + cnt.to_string())
frac = st[st.label == 'BH'].groupby('source_id').state.value_counts(normalize=True).unstack(fill_value=0).round(3)
frac.to_csv(R7/'bh_state_fractions.csv'); print('\nBH sources, fraction of observations per state:\n' + frac.to_string())
nbh = {s: int(st[(st.state == s) & (st.label == 'BH')].source_id.nunique()) for s in STATES}

# ---------------- 2c stratified evaluation ----------------
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
ex = pd.read_csv(ROOT/'results/v7b1/exclusion_oof.csv', dtype={'obs_id': str})
MOD = [('H_colours', 'LogReg', 'H-LR'), ('H_colours', 'RandomForest', 'H-RF'), ('B_shape', 'LogReg', 'B-LR'), ('B_shape', 'RandomForest', 'B-RF')]
src_lab = st.drop_duplicates('source_id').set_index('source_id').label.to_dict()
draws = L7.boot_draws(src_lab)
stmap = st.set_index('obs_id').state; boxmap = st.set_index('obs_id').apply(lambda r: (r.c1 >= C.V4_OVERLAP_BOX['c1_min']) & (r.c2 >= C.V4_OVERLAP_BOX['c2_min']), axis=1)


def strat_eval(o, groups, tag, model):
    o = o.assign(g=o.obs_id.map(groups)); rows = []
    by_src = {s: d for s, d in o.groupby('source_id')}
    pts, boots = {}, {}
    for gname in sorted(o.g.dropna().unique(), key=str):
        d = o[o.g == gname]
        pts[gname] = L7.auc_ba(d.true_label.eq('BH'), d.BH_score)
        B = []
        for dr in draws:
            parts = [by_src[s][by_src[s].g == gname] for s in dr if s in by_src]
            dd = pd.concat(parts) if parts else d.iloc[:0]
            B.append(L7.auc_ba(dd.true_label.eq('BH'), dd.BH_score) if len(dd) else (np.nan, np.nan))
        boots[gname] = np.array(B)
        for j, m in enumerate(['obs_AUC', 'obs_balanced_accuracy']):
            v = boots[gname][:, j]
            rows.append(dict(analysis=tag, model=model, group=str(gname), metric=m, point=pts[gname][j], ci2_5=np.nanpercentile(v, 2.5),
                             ci97_5=np.nanpercentile(v, 97.5), n_valid_draws=int(np.isfinite(v).sum()),
                             n_obs=len(d), n_BH_obs=int(d.true_label.eq('BH').sum()), n_BH_sources=int(d[d.true_label == 'BH'].source_id.nunique()),
                             n_NS_sources=int(d[d.true_label == 'NS'].source_id.nunique())))
    return rows, boots, pts


allrows = []
for tag, oo in (('v2 OOF', v2), ('MINBAR-excluded OOF (v7b1)', ex[ex.set == 'minbar'])):
    for rep, alg, nm in MOD:
        o = oo[(oo.representation == rep) & (oo.model == alg)]
        rows, boots, pts = strat_eval(o, stmap, tag, nm); allrows += rows
        if 'soft-like' in boots and 'hard-like' in boots:
            dB = boots['soft-like'] - boots['hard-like']
            for j, m in enumerate(['obs_AUC', 'obs_balanced_accuracy']):
                testable = nbh['soft-like'] >= C.V7_MIN_BH_SOURCES_PER_STRATUM and nbh['hard-like'] >= C.V7_MIN_BH_SOURCES_PER_STRATUM
                allrows.append(dict(analysis=tag, model=nm, group='soft-like - hard-like', metric=m, point=pts['soft-like'][j] - pts['hard-like'][j],
                                    ci2_5=np.nanpercentile(dB[:, j], 2.5), ci97_5=np.nanpercentile(dB[:, j], 97.5), n_valid_draws=int(np.isfinite(dB[:, j]).sum()),
                                    role='PRIMARY' if (tag == 'v2 OOF' and nm == 'H-LR' and m == 'obs_AUC') else 'descriptive',
                                    testable=testable))
        rows, _, _ = strat_eval(o, boxmap.map({True: 'inside overlap box', False: 'outside overlap box'}), tag + ' | overlap box (2e)', nm)
        allrows += rows
res = pd.DataFrame(allrows); res.to_csv(R7/'state_stratified_metrics.csv', index=False)
t = res.copy(); t['txt'] = t.apply(lambda r: f"{r.point:.3f} [{r.ci2_5:.3f},{r.ci97_5:.3f}]", axis=1)
print('\n' + t.pivot_table(index=['analysis', 'model', 'group'], columns='metric', values='txt', aggfunc='first').to_string())
prim = res[res.role == 'PRIMARY'].iloc[0]
print(f"\nPRIMARY H-LR soft-like AUC - hard-like AUC: {prim.point:+.3f} [{prim.ci2_5:+.3f},{prim.ci97_5:+.3f}] (testable: {prim.testable}; "
      f"BH sources soft {nbh['soft-like']}, hard {nbh['hard-like']})")

# ---------------- 2f exploratory: hard-like only LOSO ----------------
hard = set(st[st.state == 'hard-like'].obs_id)
m = np.isin(z['obs_id'], list(hard))
yh, gh, oh = z['y'][m], z['source_id'][m], z['obs_id'][m]
reps = L.v2_representations(z['rate'][m], z['edges'], z['F'][m])
fh = list(LeaveOneGroupOut().split(np.zeros(m.sum()), yh, gh))
exo = {}
for rep, alg, nm in MOD:
    s = L.loso_scores(reps[rep], yh, gh, fh, alg)
    exo[f'{nm} [hard-like only, trained on hard-like]'] = L.to_oof(np.arange(m.sum()), s, 0.5, yh, gh, oh, rep, alg)
    ref = v2[(v2.representation == rep) & (v2.model == alg) & v2.obs_id.isin(hard)]
    exo[f'{nm} [v2 OOF on the same hard-like obs]'] = ref
pd.concat([v.assign(name=k) for k, v in exo.items()]).to_csv(R7/'hard_only_oof.csv', index=False)
eb = []
for rep, alg, nm in MOD:
    b = L.paired_bootstrap({f'{nm} [v2 OOF on the same hard-like obs]': exo[f'{nm} [v2 OOF on the same hard-like obs]'],
                            f'{nm} [hard-like only, trained on hard-like]': exo[f'{nm} [hard-like only, trained on hard-like]']},
                           f'{nm} [v2 OOF on the same hard-like obs]'); b['model'] = nm; eb.append(b)
eb = pd.concat(eb, ignore_index=True); eb.to_csv(R7/'hard_only_bootstrap.csv', index=False)
eb['txt'] = eb.apply(lambda r: f"{r.point:.3f} [{r.ci2_5:.3f},{r.ci97_5:.3f}]", axis=1)
print(f'\n[2f exploratory] hard-like only: {m.sum()} obs, {len(set(gh))} sources ({len(set(gh[yh == 1]))} BH)\n'
      + eb.pivot_table(index=['comparison'], columns='metric', values='txt', aggfunc='first').to_string())

# figure: per-state AUC with intervals (v2 OOF)
fig, a = plt.subplots(figsize=(7.5, 3.6))
r2 = res[(res.analysis == 'v2 OOF') & (res.metric == 'obs_AUC') & res.group.isin(STATES)]
for i, (rep, alg, nm) in enumerate(MOD):
    d = r2[r2.model == nm].set_index('group').loc[STATES]
    x = np.arange(3) + (i - 1.5) * 0.15
    a.errorbar(x, d.point, yerr=[d.point - d.ci2_5, d.ci97_5 - d.point], fmt='o', ms=4, capsize=2, label=nm)
a.set_xticks(range(3)); a.set_xticklabels([f'{s}\n({nbh[s]} BH src)' for s in STATES]); a.set_ylabel('observation-level AUC (v2 LOSO OOF)')
a.axhline(.5, color=INK2, lw=.6, ls='--'); a.legend(fontsize=7, ncol=4, frameon=False, loc='lower left')
a.set_title('v7a: classifier performance by variability state (95% source bootstrap)', loc='left', fontsize=9)
fig.savefig(FG/'v7a_auc_by_state.png'); plt.close(fig)
progress('v7a_states', f"PRIMARY H-LR soft AUC - hard AUC {prim.point:+.3f} [{prim.ci2_5:+.3f},{prim.ci97_5:+.3f}]")
