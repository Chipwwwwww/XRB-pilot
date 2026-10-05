"""v9 summary figure: (a) v9a NICER observation-level AUC by state (H_N vs H_N+T_N, LR / RF); (b) v9a per-source hard-like scores;
(c) v9b nu_c vs colour in the NICER hard-like observations; (d) v9c MAXI 2-4 keV gain by >= 4 keV colour tertile (source level,
post hoc). Output figures/v9/v9_summary.png."""
import os, sys
os.environ['XRB_VERSION'] = 'v9'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT
import numpy as np, pandas as pd
from plotstyle import plt, CLASS_COLOR, INK, INK2

FG = ROOT/'figures/v9'; FG.mkdir(parents=True, exist_ok=True)
A = pd.read_csv(ROOT/'results/v9a/v9a_metrics.csv'); P = pd.read_csv(ROOT/'results/v9b/v9b_permutation_test.csv')
F = pd.read_csv(ROOT/'data/v9/processed/nicer_features.csv', dtype={'obsid': str})
O = pd.read_csv(ROOT/'results/v9a/v9a_oof_predictions.csv', dtype={'obs_id': str})
V = pd.read_csv(ROOT/'results/v9c/v9c_maxi_c4_strata_source_level_post_hoc.csv')
fig, ax = plt.subplots(1, 4, figsize=(22, 5.0), gridspec_kw=dict(width_ratios=[1.1, 1.2, 1.0, 0.9]), layout='constrained')

a = ax[0]; names = ['H_N-LR', 'H_N+T_N-LR', 'H_N-RF', 'H_N+T_N-RF']
for i, m in enumerate(names):
    for st, dx, col in (('soft-like', -0.15, '#9aa5b1'), ('hard-like', 0.15, '#2a78d6')):
        r = A[(A.analysis == f'NICER all-state LOSO | {st}') & (A.comparison == m) & (A.metric == 'obs_AUC')]
        if len(r):
            r = r.iloc[0]; a.errorbar([i + dx], [r.point], yerr=[[r.point - r.ci2_5], [r.ci97_5 - r.point]], fmt='o', color=col, capsize=2, ms=5,
                                      label=st if i == 0 else None)
p = A[A.role == 'PRIMARY']
ttl = f'{p.iloc[0].point:+.3f} [{p.iloc[0].ci2_5:+.3f}, {p.iloc[0].ci97_5:+.3f}]' if len(p) else 'not testable'
a.set_xticks(range(len(names))); a.set_xticklabels(names, fontsize=8); a.axhline(.5, color=INK2, lw=.6, ls='--'); a.set_ylim(0.2, 1.03)
a.set_ylabel('observation-level AUC (NICER, LOSO)'); a.legend(frameon=False, fontsize=7, loc='lower left')
a.set_title(f'(a) v9a: NICER (independent instrument)\nhard-like H_N+T_N-LR - H_N-LR = {ttl} (PRIMARY)', loc='left', fontsize=9)

a = ax[1]
hard = set(F[F.state == 'hard-like'].obsid)
s = O[O.obs_id.isin(hard) & O.name.isin(['H_N-LR', 'H_N+T_N-LR'])].groupby(['true_label', 'source_id', 'name']).BH_score.mean().unstack('name').reset_index()
s = s.sort_values(['true_label', 'H_N+T_N-LR']).reset_index(drop=True)
y = np.arange(len(s))
for lab, d in s.groupby('true_label'):
    a.scatter(d['H_N-LR'], d.index, marker='|', s=60, color=CLASS_COLOR[lab])
    a.scatter(d['H_N+T_N-LR'], d.index, s=18, color=CLASS_COLOR[lab], label=lab)
a.set_yticks(y); a.set_yticklabels(s.source_id, fontsize=5); a.axvline(.5, color=INK2, lw=.6, ls='--')
a.set_xlabel('mean hard-like BH score (| colours only, o colours + timing)'); a.legend(frameon=False, fontsize=7)
a.set_title('(b) v9a: per-source scores, hard-like observations', loc='left', fontsize=9)

a = ax[2]; hb = F[F.state == 'hard-like']
for lab, d in hb.groupby('label'):
    a.scatter(d.c2, d.nu_c, s=14, alpha=.7, color=CLASS_COLOR[lab], label=f'{lab} ({d.source.nunique()} src)')
a.set_yscale('log'); a.set_xlabel('NICER c2 = C(6-10)/C(4-6 keV)'); a.set_ylabel('nu_c (Hz)'); a.legend(frameon=False, fontsize=7)
pp = P[P.role == 'PRIMARY'].iloc[0]
a.set_title(f'(c) v9b: characteristic frequency at matched colour\nD(log nu_c) = {pp.D:+.2f}, p = {pp.p:.3f} (PRIMARY)', loc='left', fontsize=9)

a = ax[3]; S = ['C4 low (softest >=4 keV)', 'C4 middle', 'C4 high (hardest)']
for i, (cmp_, col) in enumerate((('RF [C2D] - RF [C1D]', '#2a78d6'), ('RF [C2D_NH] - RF [C1D_NH]', '#1baf7a'))):
    d = V[(V.comparison == cmp_) & (V.metric == 'source_AUC')].set_index('stratum').reindex(S)
    x = np.arange(3) + (i - 0.5) * 0.2
    a.errorbar(x, d.point, yerr=[d.point - d.ci2_5, d.ci97_5 - d.point], fmt='o', capsize=2, color=col, label=cmp_)
a.axhline(0, color=INK2, lw=.6); a.set_xticks(range(3)); a.set_xticklabels(['softest', 'middle', 'hardest'], fontsize=8)
a.set_xlabel('>= 4 keV colour tertile'); a.set_ylabel('source AUC gain from 2-4 keV'); a.legend(frameon=False, fontsize=7)
a.set_title('(d) v9c: MAXI 2-4 keV gain by state proxy\n(source level, post hoc; descriptive)', loc='left', fontsize=9)
fig.suptitle('v9 summary: NICER independent test of hard-state timing and BH characteristic frequency; MAXI strata '
             '(intervals: 2000-draw class-stratified source bootstrap)', x=.01, ha='left')
fig.savefig(FG/'v9_summary.png'); plt.close(fig); print('written', FG/'v9_summary.png')
