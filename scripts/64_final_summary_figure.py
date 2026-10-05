"""Wrap-up figure (v14): the two lines of evidence across versions, read from the result files.
(a) hard-state timing gain (observation-level AUC, H+T - H) with 95% source-bootstrap intervals: LR (v8a, v8b, v9a, v10a pooled,
v11a, v12, v13) and RF (v8a S1, v9, v10 NICER, v11, v12, v13); (b) colour-conditional D(log10 nu_c) (BH - NS) with
permutation p (v6d S1, v9b, v10b RXTE / NICER / pooled, v11b, v12a, v13b). Output figures/final/summary_across_versions.png."""
import os, sys
os.environ['XRB_VERSION'] = 'v14'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT
import numpy as np, pandas as pd
from plotstyle import plt, INK, INK2

FG = ROOT/'figures/final'; FG.mkdir(parents=True, exist_ok=True)
rd = lambda f: pd.read_csv(ROOT/f)


def pick(f, **kw):
    d = rd(f)
    for k, v in kw.items(): d = d[d[k] == v]
    r = d.iloc[0]; return float(r.point), float(r.ci2_5), float(r.ci97_5)


G = []   # (label, instrument, model, point, lo, hi, primary)
G.append(('v8a RXTE v2 sample', 'RXTE', 'LR', *pick('results/v8a/v8a_metrics.csv', role='PRIMARY'), True))
G.append(('v8a RXTE v2 sample', 'RXTE', 'RF', *pick('results/v8a/v8a_metrics.csv', analysis='S1 existing OOF | hard-like', comparison='H+T-RF - H-RF', metric='obs_AUC'), False))
G.append(('v8b RXTE external (frozen)', 'RXTE', 'LR', *pick('results/v8b/v8b_metrics.csv', role='PRIMARY'), True))
G.append(('v9a NICER (prefix)', 'NICER', 'LR', *pick('results/v9a/v9a_metrics.csv', role='PRIMARY'), True))
G.append(('v9a NICER (prefix)', 'NICER', 'RF', *pick('results/v9a/v9a_metrics.csv', analysis='NICER all-state LOSO | hard-like', comparison='H_N+T_N-RF - H_N-RF'), False))
G.append(('v10a pooled RXTE+NICER', 'both', 'LR', *pick('results/v10a/v10a_pooled_gain.csv', role='PRIMARY'), True))
G.append(('v10 NICER full', 'NICER', 'RF', *pick('results/v10a/v10a_pooled_gain.csv', component='NICER full (RF)'), False))
G.append(('v11a NICER new obs (frozen)', 'NICER', 'LR', *pick('results/v11/v11a_metrics.csv', role='PRIMARY'), True))
G.append(('v11 NICER new obs (frozen)', 'NICER', 'RF', *pick('results/v11/v11a_metrics.csv', analysis='new obs | hard-like', comparison='H_N+T_N-RF - H_N-RF'), False))
G.append(('v12 NICER 3C50-corrected', 'NICER', 'LR', *pick('results/v12/v12b_gain.csv', analysis='hard-like', comparison='H_N+T_N-LR - H_N-LR'), False))
G.append(('v12b NICER 3C50-corrected', 'NICER', 'RF', *pick('results/v12/v12b_gain.csv', role='PRIMARY'), True))
G.append(('v13 NICER third set (frozen)', 'NICER', 'LR', *pick('results/v13/v13a_gain.csv', analysis='hard-like', comparison='H_N+T_N-LR - H_N-LR'), False))
G.append(('v13a NICER third set (frozen)', 'NICER', 'RF', *pick('results/v13/v13a_gain.csv', role='PRIMARY'), True))
G = pd.DataFrame(G, columns=['label', 'instrument', 'model', 'point', 'lo', 'hi', 'primary'])
G.to_csv(ROOT/'results/final_timing_gain_across_versions.csv', index=False)

v6 = rd('results/v6/v6d_permutation_test.csv').set_index('feature').loc['log10 nu_c']
v10 = rd('results/v10b/v10b_pooled_nuc.csv')
Dn = [('v6d RXTE v2 (all states)', float(v6.S1_D), float(v6.S1_p), False),
      ('v6d RXTE external (all states)', float(v6.E_D), float(v6.E_p), False),
      ('v9b NICER prefix', *rd('results/v9b/v9b_permutation_test.csv').query("role == 'PRIMARY'")[['D', 'p']].iloc[0], True),
      ('v10b RXTE hard-like', *v10[v10.analysis.str.startswith('RXTE alone')][['D', 'p']].iloc[0], False),
      ('v10b NICER full', *v10[v10.analysis.str.startswith('NICER alone')][['D', 'p']].iloc[0], False),
      ('v10b pooled RXTE+NICER', *v10[v10.role == 'PRIMARY'][['D', 'p']].iloc[0], True),
      ('v11b NICER new obs', *rd('results/v11/v11b_nuc.csv').query("role == 'PRIMARY'")[['D', 'p']].iloc[0], True),
      ('v12a NICER 3C50-corrected', *rd('results/v12/v12a_nuc.csv').query("role == 'PRIMARY'")[['D', 'p']].iloc[0], True),
      ('v13b NICER third set', *rd('results/v13/v13b_nuc.csv').query("role == 'PRIMARY'")[['D', 'p']].iloc[0], True)]
Dn = pd.DataFrame(Dn, columns=['label', 'D', 'p', 'primary']); Dn.to_csv(ROOT/'results/final_nuc_difference_across_versions.csv', index=False)

fig, ax = plt.subplots(1, 2, figsize=(15, 6.2), layout='constrained')
a = ax[0]; y = np.arange(len(G))[::-1]
for (i, r), yy in zip(G.iterrows(), y):
    col = '#2a78d6' if r.model == 'LR' else '#c2410c'
    a.errorbar(r.point, yy, xerr=[[r.point - r.lo], [r.hi - r.point]], fmt='s' if r.primary else 'o', color=col, mfc=col if r.primary else 'white', capsize=2, ms=6)
a.set_yticks(y); a.set_yticklabels([f'{r.label} [{r.model}]' for r in G.itertuples()], fontsize=8); a.axvline(0, color=INK2, lw=.8, ls='--')
a.set_xlabel('hard-state AUC gain from low-frequency (0.016-4 Hz) timing features (H+T - H), 95% source bootstrap')
a.set_title('(a) timing information inside the hard state (filled = pre-registered primary; blue LR, orange RF)', loc='left', fontsize=9)
a = ax[1]; y = np.arange(len(Dn))[::-1]
for (i, r), yy in zip(Dn.iterrows(), y):
    a.scatter(r.D, yy, s=60 if r.primary else 40, color='#1baf7a' if r.p < 0.05 else '#9aa5b1', marker='s' if r.primary else 'o', edgecolors=INK, linewidths=.5)
    a.annotate(f'p = {r.p:.3g}', (r.D, yy), xytext=(6, -3), textcoords='offset points', fontsize=7)
a.set_yticks(y); a.set_yticklabels(Dn.label, fontsize=8); a.axvline(0, color=INK2, lw=.8, ls='--')
a.set_xlabel('D = BH - NS mean residual of log10 nu_c at matched colour (dex)')
a.set_title('(b) characteristic frequency of BHs relative to NSs (green p < 0.05; squares = primary)', loc='left', fontsize=9)
fig.suptitle('XRB-pilot v5-v13: the two timing results across samples, instruments and analysis choices', x=.01, ha='left')
fig.savefig(FG/'summary_across_versions.png'); plt.close(fig); print('written', FG/'summary_across_versions.png')
