"""v8 summary figure (preregistration_v8.md sec. 8): (a) v8a S1 AUC by state with / without Standard-1 timing; (b) v8b external
set X, frozen v6 models by state; (c) v8c per-source high-frequency rms (4-64 Hz vs 512-1024 Hz); (d) v8c S1-HF / X-HF AUC;
(e) v8d MAXI RF source AUC before / after the N_H correction. Output figures/v8/v8_summary.png."""
import os, sys
os.environ['XRB_VERSION'] = 'v8'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT
import numpy as np, pandas as pd
from plotstyle import plt, CLASS_COLOR, INK, INK2

FG = ROOT/'figures/v8'; FG.mkdir(parents=True, exist_ok=True)
fig, ax = plt.subplots(1, 5, figsize=(25, 5.0), gridspec_kw=dict(width_ratios=[1.15, 0.9, 1.0, 1.0, 0.9]), layout='constrained')
A = pd.read_csv(ROOT/'results/v8a/v8a_metrics.csv'); Bm = pd.read_csv(ROOT/'results/v8b/v8b_metrics.csv'); Cm = pd.read_csv(ROOT/'results/v8c/v8c_metrics.csv')
Dm = pd.read_csv(ROOT/'results/v8d/v8d_bootstrap.csv')


def get(df, analysis, comp, metric='obs_AUC'):
    r = df[(df.analysis == analysis) & (df.comparison == comp) & (df.metric == metric)]
    return r.iloc[0] if len(r) else None


def errpt(a, x, r, **kw):
    a.errorbar([x], [r.point], yerr=[[r.point - r.ci2_5], [r.ci97_5 - r.point]], capsize=2, **kw)


# (a) v8a
a = ax[0]; models = ['H-LR', 'H+T-LR', 'H+T*-LR', 'H-RF', 'H+T-RF', 'H+N-LR', 'H+N+T-LR']
for i, m in enumerate(models):
    for st, dx, mk, col in (('soft-like', -0.15, 'o', '#9aa5b1'), ('hard-like', 0.15, 's', '#2a78d6')):
        r = get(A, f'S1 existing OOF | {st}', m)
        errpt(a, i + dx, r, fmt=mk, color=col, ms=5, label=st if i == 0 else None)
p = get(A, 'S1 existing OOF | hard-like', 'H+T-LR - H-LR')
a.set_xticks(range(len(models))); a.set_xticklabels(models, rotation=30, fontsize=7); a.axhline(.5, color=INK2, ls='--', lw=.6)
a.set_ylim(0.3, 1.03); a.set_ylabel('observation-level AUC (S1, LOSO OOF)'); a.legend(fontsize=7, frameon=False, loc='lower right')
a.set_title(f'(a) v8a: S1 by state; hard-like H+T-LR - H-LR\n= {p.point:+.3f} [{p.ci2_5:+.3f}, {p.ci97_5:+.3f}] (PRIMARY)', loc='left', fontsize=9)

# (b) v8b
a = ax[1]; groups = [('soft-like', 'X frozen v6 models | soft-like'), ('hard-like', 'X frozen v6 models | hard-like'), ('all', 'X frozen v6 models, all states | all')]
for i, (g, an) in enumerate(groups):
    for m, dx, col in (('H_R-LR', -0.12, '#9aa5b1'), ('H_R+T-LR', 0.12, '#c2410c')):
        errpt(a, i + dx, get(Bm, an, m), fmt='o', color=col, ms=5, label=m if i == 0 else None)
p = get(Bm, 'X frozen v6 models | hard-like', 'H_R+T-LR - H_R-LR')
a.set_xticks(range(3)); a.set_xticklabels([g for g, _ in groups]); a.axhline(.5, color=INK2, ls='--', lw=.6); a.set_ylim(0.3, 1.03)
a.set_ylabel('observation-level AUC (external set X, frozen)'); a.legend(fontsize=7, frameon=False, loc='lower left')
a.set_title(f'(b) v8b: external sources (incl. GS 1354-64, SS 433)\nhard-like = {p.point:+.3f} [{p.ci2_5:+.3f}, {p.ci97_5:+.3f}] (PRIMARY)', loc='left', fontsize=9)

# (c) v8c per-source HF
a = ax[2]; ps = pd.read_csv(ROOT/'results/v8c/v8c_per_source_hf_null_subtracted.csv')
w = ps.pivot_table(index=['sample', 'source_id', 'label'], columns='band', values=['rms', 'z']).reset_index()
for (smp, lab), d in w.groupby(['sample', 'label']):
    mk = 'o' if smp == 'S1' else '^'
    a.scatter(d[('rms', 'HF1c')], d[('z', 'HF3c')], s=34, marker=mk, color=CLASS_COLOR[lab], alpha=.85 if smp == 'S1' else .5, label=f'{lab} ({smp})')
a.axhline(3, color=INK2, lw=.6, ls='--'); a.axhline(0, color=INK2, lw=.4)
a.set_xlabel('rms 4-64 Hz (per source, null band subtracted)'); a.set_ylabel('z of 512-1024 Hz power (null band subtracted)')
a.legend(fontsize=7, frameon=False); a.set_xlim(-0.05, 0.25)
a.set_title('(c) v8c: SR2000 band per source (post hoc null subtraction)\nonly SAX J1808.4-3658 above 3 sigma; no BH', loc='left', fontsize=9)

# (d) v8c AUC
a = ax[3]; mods = [('S1-HF LOSO | S1-HF', m) for m in ('H-LR', 'H+HF-LR', 'H+T-LR', 'H+T+HF-LR', 'HF-LR')] + \
                 [('X-HF frozen (fitted on S1-HF) | X-HF', m) for m in ('H_R-LR [S1-HF]', 'H_R+HF-LR [S1-HF]')]
for i, (an, m) in enumerate(mods):
    r = get(Cm, an, m)
    if r is not None: errpt(a, i, r, fmt='o', color='#1baf7a' if 'HF' in m.replace('S1-HF', '') else '#9aa5b1', ms=5)
p = get(Cm, 'S1-HF LOSO | S1-HF', 'H+HF-LR - H-LR')
a.set_xticks(range(len(mods))); a.set_xticklabels([m.replace(' [S1-HF]', '\n(X-HF, frozen)') for _, m in mods], rotation=30, fontsize=7)
a.axhline(.5, color=INK2, ls='--', lw=.6); a.set_ylim(0.3, 1.03); a.set_ylabel('observation-level AUC')
a.set_title(f'(d) v8c: S1-HF LOSO; H+HF-LR - H-LR\n= {p.point:+.3f} [{p.ci2_5:+.3f}, {p.ci97_5:+.3f}] \n(pre-specified primary; exploratory only: IC4 failed)', loc='left', fontsize=9)

# (e) v8d
a = ax[4]; names = ['RF [C1D]', 'RF [C2D]', 'RF [C1D_NH]', 'RF [C2D_NH]', 'log N_H alone']
r2 = Dm[Dm.metric == 'source_AUC'].drop_duplicates('comparison').set_index('comparison').reindex(names)
y = np.arange(len(names))
a.errorbar(r2.point, y, xerr=[r2.point - r2.ci2_5, r2.ci97_5 - r2.point], fmt='o', color=INK, capsize=2)
a.set_yticks(y); a.set_yticklabels(['RF >=4 keV colour', 'RF 2 colours (2-4 keV)', 'RF >=4 keV, N_H-corr.', 'RF 2 colours, N_H-corr.', 'HI4PI log N_H only'], fontsize=7)
a.invert_yaxis(); a.axvline(.5, color=INK2, ls='--', lw=.6); a.set_xlabel('source-level AUC, MAXI BH vs NPNS')
p = Dm[(Dm.role == 'PRIMARY') & (Dm.metric == 'source_AUC')].iloc[0]
a.set_title(f'(e) v8d: MAXI after HI4PI N_H correction\nRF 2 colours - >=4 keV = {p.point:+.3f} [{p.ci2_5:+.3f}, {p.ci97_5:+.3f}] (PRIMARY)', loc='left', fontsize=9)
fig.suptitle('v8 summary: timing inside the hard state, external hard-state sources, event-mode high frequencies, MAXI N_H control '
             '(intervals: 2000-draw class-stratified source bootstrap)', x=.01, ha='left')
fig.savefig(FG/'v8_summary.png'); plt.close(fig); print('written', FG/'v8_summary.png')
