"""v7 summary figure (preregistration_v7.md §10): (a) observation-level AUC by variability state (v2 OOF, four models);
(b) source-level AUC before / after adding the persistent BHs (v7b2); (c) MAXI strict pipeline (v7c2 main task) vs RXTE H-LR,
and the RXTE-vs-MAXI source scores of shared sources (v7c3). Output figures/v7/v7_summary.png."""
import os, sys
os.environ['XRB_VERSION'] = 'v7'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT
import numpy as np, pandas as pd
from plotstyle import plt, CLASS_COLOR, INK, INK2

FG = ROOT/'figures/v7'; FG.mkdir(parents=True, exist_ok=True)
COL = {'H-LR': '#2a78d6', 'H-RF': '#c2410c', 'B-LR': '#1baf7a', 'B-RF': '#4a3aa7'}
fig, ax = plt.subplots(1, 4, figsize=(20, 4.8), gridspec_kw=dict(width_ratios=[1.2, 1.0, 1.1, 0.9]), layout='constrained')

# (a) AUC by state
st = pd.read_csv(ROOT/'results/v7a/state_stratified_metrics.csv')
st = st[(st.analysis == 'v2 OOF') & (st.metric == 'obs_AUC')]
S = ['soft-like', 'intermediate', 'hard-like']; a = ax[0]
for i, m in enumerate(COL):
    d = st[st.model == m].set_index('group').loc[S]; x = np.arange(3) + (i - 1.5) * 0.14
    a.errorbar(x, d.point, yerr=[d.point - d.ci2_5, d.ci97_5 - d.point], fmt='o', ms=4, capsize=2, color=COL[m], label=m)
p = st[(st.model == 'H-LR') & (st.group == 'soft-like - hard-like')].iloc[0]
a.set_xticks(range(3)); a.set_xticklabels(['soft-like\n(rms<0.075)', 'intermediate\n(1 BH source)', 'hard-like\n(rms>0.10)'])
a.axhline(.5, color=INK2, ls='--', lw=.6); a.set_ylabel('observation-level AUC (v2 LOSO OOF)'); a.set_ylim(0, 1.05)
a.set_title(f'(a) v7a: by variability state\nH-LR soft − hard = {p.point:+.2f} [{p.ci2_5:+.2f}, {p.ci97_5:+.2f}]', loc='left', fontsize=9)
a.legend(fontsize=7, ncol=2, frameon=False, loc='lower left')

# (b) persistent BHs
b2 = pd.read_csv(ROOT/'results/v7b2/v7b2_bootstrap.csv'); a = ax[1]
lab = []
for j, m in enumerate(['H-LR', 'H-RF']):
    rows = [(f'v2 {m} (31 sources)', 'v2: 31 sources'), (f'{m} [main (34 sources)] on the 31 v2 sources', '+3 BH: on the 31'),
            (f'{m} [main (34 sources)] all sources', '+3 BH: all 34')]
    for k, (cmp_, l) in enumerate(rows):
        r = b2[(b2.comparison == cmp_) & (b2.metric == 'source_AUC')].iloc[0]
        y = k + j * 0.25
        a.errorbar(r.point, y, xerr=[[r.point - r.ci2_5], [r.ci97_5 - r.point]], fmt='o', color=COL[m], capsize=2, label=m if k == 0 else None)
    lab = [l for _, l in rows]
a.set_yticks(np.arange(3) + 0.125); a.set_yticklabels(lab); a.invert_yaxis(); a.set_xlim(0.6, 1.02); a.set_xlabel('source-level AUC (95% source bootstrap)')
a.set_title('(b) v7b2: adding Cyg X-1, LMC X-1, LMC X-3', loc='left', fontsize=9); a.legend(fontsize=7, frameon=False)

# (c) MAXI strict pipeline vs RXTE
a = ax[2]
c2 = pd.read_csv(ROOT/'results/v7c/v7c2_bootstrap.csv')
c2 = c2[c2.task.str.startswith('main') & ~c2.comparison.str.contains(' - ') & (c2.metric == 'source_AUC')].drop_duplicates('comparison')
order = [f'{m} [{f}]' for m in ('LR', 'RF', 'KNN', 'SVM') for f in ('CCI', 'C2D', 'C1D')]
c2 = c2.set_index('comparison').reindex([o for o in order if o in set(c2.comparison)])
y = np.arange(len(c2))
a.errorbar(c2.point, y, xerr=[c2.point - c2.ci2_5, c2.ci97_5 - c2.point], fmt='o', color=INK, capsize=2)
v2b = pd.read_csv(ROOT/'results/v4/v4a_bootstrap.csv'); r = v2b[(v2b.comparison == 'H_colours|LogReg') & (v2b.metric == 'source_AUC')]
if len(r): a.axvline(float(r.point.iloc[0]), color='#2a78d6', ls='--', lw=.8, label='RXTE v2 H-LR')
a.set_yticks(y); a.set_yticklabels([s.replace('C2D', '2 colours').replace('C1D', '>=4 keV colour').replace('CCI', 'CCI') for s in c2.index], fontsize=7)
a.invert_yaxis(); a.set_xlabel('source-level AUC, MAXI BH vs non-pulsing NS'); a.legend(fontsize=7, frameon=False, loc='lower left')
a.set_title('(c) v7c2: MAXI/GSC strict pipeline (LOSO)', loc='left', fontsize=9)

# (d) RXTE vs MAXI source scores
a = ax[3]; pr = pd.read_csv(ROOT/'results/v7c/v7c3_rxte_vs_maxi.csv')
for l in ('NS', 'BH'):
    d = pr[pr.label == l]; a.scatter(d.rxte_score, d.maxi_score, s=26, color=CLASS_COLOR[l], label=l)
a.axhline(.5, color=INK2, ls='--', lw=.6); a.axvline(.5, color=INK2, ls='--', lw=.6); a.plot([0, 1], [0, 1], color=INK2, lw=.5)
from scipy.stats import spearmanr
rho = spearmanr(pr.rxte_score, pr.maxi_score)[0]; agree = ((pr.rxte_score >= .5) == (pr.maxi_score >= .5)).mean()
a.set_xlabel('RXTE source score (H-LR)'); a.set_ylabel('MAXI source score (LR, CCI)'); a.legend(fontsize=7, frameon=False)
a.set_title(f'(d) v7c3: {len(pr)} shared sources\nrho = {rho:.2f}, label agreement {agree:.2f}', loc='left', fontsize=9)
fig.suptitle('v7 summary: state dependence, persistent BHs, cross-instrument (all intervals: 2000-draw class-stratified source bootstrap)', x=.01, ha='left')
fig.savefig(FG/'v7_summary.png'); plt.close(fig); print('written', FG/'v7_summary.png')
