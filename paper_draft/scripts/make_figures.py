"""Figures for the paper draft (paper_draft/main.tex).

Every number plotted here is read from files committed in the repository (results/, data/*/processed/).
No model is fitted, no resampling is run and no statistic is recomputed: the script only selects rows and draws them.
The single exception is purely descriptive arithmetic on committed per-observation tables (counts and the
min/max of the committed leave-one-BH-out values), which is stated in the figure captions.

Run from the repository root:  python paper_draft/scripts/make_figures.py
Outputs: paper_draft/figures/fig2_colour_ablation.pdf, fig3_states.pdf, fig4_timing_gain.pdf,
         fig5_v13.pdf, figA1_nuc.pdf   (fig1 is a TikZ diagram inside main.tex)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'paper_draft' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
R = ROOT / 'results'

# colours validated with the dataviz palette validator (light surface): classes and models never share a hue
C_BH, C_NS = '#2a78d6', '#eb6834'        # black hole / neutron star
C_LR, C_RF = '#6250d6', '#008300'        # logistic regression / random forest
INK, INK2, GRID = '#1a1a1a', '#55534f', '#dddcd8'
MK = {'LR': 's', 'RF': 'o'}
COL = {'LR': C_LR, 'RF': C_RF}

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.labelsize': 8, 'axes.titlesize': 8.5,
    'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5, 'legend.fontsize': 7.5, 'axes.edgecolor': INK2,
    'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'axes.linewidth': 0.6,
    'xtick.major.width': 0.6, 'ytick.major.width': 0.6, 'axes.spines.top': False, 'axes.spines.right': False,
    'savefig.bbox': 'tight', 'savefig.pad_inches': 0.02, 'pdf.fonttype': 42,
})


def ci_point(ax, y, p, lo, hi, model, primary, size=5.5):
    c = COL[model]
    ax.plot([lo, hi], [y, y], color=c, lw=1.4, solid_capstyle='butt', zorder=2)
    ax.plot([lo, lo], [y - .12, y + .12], color=c, lw=1.0, zorder=2)
    ax.plot([hi, hi], [y - .12, y + .12], color=c, lw=1.0, zorder=2)
    ax.plot(p, y, MK[model], ms=size, mec=c, mew=1.2, mfc=c if primary else 'white', zorder=3)


def row(df, **kw):
    m = np.ones(len(df), bool)
    for k, v in kw.items():
        m &= (df[k] == v).values
    r = df[m]
    assert len(r) == 1, (kw, len(r))
    return r.iloc[0]


# ------------------------------------------------------------------------------------------------ Figure 2
def fig2():
    a3 = pd.read_csv(R / 'v3/v3a_bootstrap.csv')
    b3 = pd.read_csv(R / 'v3/v3b_bootstrap.csv')
    hx = pd.read_csv(R / 'v4b3/v4b3_bootstrap.csv')
    v4 = pd.read_csv(R / 'v4/v4a_bootstrap.csv')
    b1 = pd.read_csv(R / 'v4b1/v4b1_bootstrap.csv')
    met = 'source_AUC'
    # (a) absolute source-level AUC (point estimates, no comparison implied)
    reps = [('H_colours', a3, 'two colours (H)'), ('HI_colours_intensity', a3, 'H + log flux (HI)'),
            ('B_shape', a3, '5-25 keV shape, 45 bins (B)'), ('H_plus_B', a3, 'H + B'),
            ('A_intensity', a3, '5-25 keV spectrum with intensity (A)'),
            ('H3_colours_3_25', b3, 'colours incl. 3-5 keV (H3)'), ('B3_shape_3_25', b3, '3-25 keV shape, 50 bins (B3)')]
    # (b) paired differences in source-level AUC; role from the time-stamped plans (decision log for B - H)
    diffs = [
        (a3, dict(comparison='H_plus_B - H_colours', model='LogReg'), 'LR', '(H + B) - H', 'P'),
        (a3, dict(comparison='H_plus_B - H_colours', model='RandomForest'), 'RF', '(H + B) - H', 'P'),
        (a3, dict(comparison='B_shape - H_colours', model='LogReg'), 'LR', 'B - H', 'h'),
        (a3, dict(comparison='B_shape - H_colours', model='RandomForest'), 'RF', 'B - H', 'h'),
        (b3, dict(comparison='H3_colours_3_25 - H_colours', model='LogReg'), 'LR', 'H3 - H', 'P'),
        (b3, dict(comparison='H3_colours_3_25 - H_colours', model='RandomForest'), 'RF', 'H3 - H', 'P'),
        (hx, dict(comparison='H+X|LogReg - H|LogReg', subset='HEXTE subset'), 'LR', '(H + 25-60 keV) - H, 396 obs', 'P'),
        (hx, dict(comparison='H+X|RandomForest - H|RandomForest', subset='HEXTE subset'), 'RF', '(H + 25-60 keV) - H, 396 obs', 'P'),
        (v4, dict(comparison='auto|nested:auto - H_colours|LogReg', part='1e_primary'), 'auto', 'nested search over 8 algorithms', 'P'),
        (b1, dict(comparison='H_colours|LogReg[srcw] - H-LR (v2, 456 obs)'), 'LR', 'H trained on 7949 obs vs 456 obs', 'P'),
    ]
    fig, ax = plt.subplots(1, 2, figsize=(6.9, 3.35), gridspec_kw=dict(width_ratios=[1, 1.1], wspace=1.05))
    a = ax[0]
    for i, (rep, df, lab) in enumerate(reps):
        y = len(reps) - 1 - i
        for dy, (mname, mk) in zip((.17, -.17), (('LogReg', 'LR'), ('RandomForest', 'RF'))):
            r = row(df, comparison=rep, model=mname, metric=met)
            ci_point(a, y + dy, r.point, r.ci2_5, r.ci97_5, mk, primary=True, size=4.3)
    a.set_yticks(range(len(reps)))
    a.set_yticklabels([r[2] for r in reps][::-1])
    a.set_xlim(0.55, 1.01); a.set_ylim(-.6, len(reps) - .4)
    a.axvline(row(a3, comparison='H_colours', model='LogReg', metric=met).point, color=INK2, lw=.6, ls=':', zorder=0)
    a.set_xlabel('source-level AUC\n(31 sources; 95% source bootstrap)')
    a.set_title('(a) RXTE/PCA development sample, LOSO', loc='left')
    a.grid(axis='x', color=GRID, lw=.5)
    b = ax[1]
    for i, (df, sel, mk, lab, role) in enumerate(diffs):
        y = len(diffs) - 1 - i
        r = row(df, metric=met, **sel)
        if mk == 'auto':
            b.plot([r.ci2_5, r.ci97_5], [y, y], color=INK, lw=1.4)
            b.plot(r.point, y, 'D', ms=4.8, mec=INK, mfc=INK, zorder=4)
        else:
            ci_point(b, y, r.point, r.ci2_5, r.ci97_5, mk, primary=(role == 'P'), size=4.3)
        b.text(1.02, y, 'primary' if role == 'P' else 'post hoc', fontsize=6.4, va='center', color=INK if role == 'P' else INK2,
               transform=b.get_yaxis_transform())
    b.set_yticks(range(len(diffs)))
    b.set_yticklabels([f"{d[3]}, {'auto' if d[2] == 'auto' else d[2]}" if d[2] != 'auto' else d[3] for d in diffs][::-1])
    b.axvline(0, color=INK2, lw=.7, ls='--', zorder=0)
    b.set_xlim(-0.42, 0.22); b.set_ylim(-.6, len(diffs) - .4)
    b.set_xlabel('paired difference in source-level AUC\n(same 31 sources; 95% source bootstrap)')
    b.set_title('(b) adding spectral information to H', loc='left')
    b.grid(axis='x', color=GRID, lw=.5)
    fig.legend(handles=[Line2D([], [], color=C_LR, marker='s', ls='-', ms=4.5, label='logistic regression (LR)'),
                        Line2D([], [], color=C_RF, marker='o', ls='-', ms=4.5, label='random forest (RF)'),
                        Line2D([], [], color=INK, marker='D', ls='-', ms=4.5, label='nested selection vs H-LR'),
                        Line2D([], [], color=INK2, marker='o', mfc='white', ls='', ms=4.5, label='open: post hoc comparison')],
               loc='lower center', bbox_to_anchor=(0.45, -0.2), ncol=4, frameon=False, fontsize=6.8, handlelength=1.6)
    fig.savefig(OUT / 'fig2_colour_ablation.pdf')
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ Figure 3
def fig3():
    s = pd.read_csv(R / 'v7a/states.csv')
    P = pd.read_csv(ROOT / 'data/v12/processed/nicer_corrected_screened.csv', dtype={'obsid': str})
    v7 = pd.read_csv(R / 'v7a/state_stratified_metrics.csv')
    v9 = pd.read_csv(R / 'v9a/v9a_metrics.csv')
    v11 = pd.read_csv(R / 'v11/v11a_metrics.csv')
    v12 = pd.read_csv(R / 'v12/v12b_gain.csv')
    v13 = pd.read_csv(R / 'v13/v13a_gain.csv')
    fig = plt.figure(figsize=(6.9, 5.7))
    gs = fig.add_gridspec(2, 5, height_ratios=[1, 1.45], width_ratios=[1, 1, 0.38, 1, 1], wspace=0.1, hspace=0.5)
    panels = [(0, s, 'RXTE', 'linear', (0.05, 1.1), (-0.05, 0.6), 'F(7-10)/F(5-7 keV)', 'F(16-25)/F(10-16 keV)', 'source_id'),
              (3, P, 'NICER', 'log', (0.015, 1.5), (0.035, 3.0), 'C(4-6)/C(2-4 keV)', 'C(6-10)/C(4-6 keV)', 'source')]
    letters = iter('abcd')
    for c0, d, inst, scale, xl, yl, xlab, ylab, sc in panels:
        for k, st in enumerate(('soft-like', 'hard-like')):
            a = fig.add_subplot(gs[0, c0 + k])
            g = d[d.state == st]
            txt = []
            for L, col in (('NS', C_NS), ('BH', C_BH)):
                x = g[g.label == L]
                a.scatter(x.c1, x.c2, s=5, color=col, alpha=.75, lw=0)
                txt.append(f'{L} {len(x)} obs / {x[sc].nunique()} src')
            a.set_xscale(scale); a.set_yscale(scale); a.set_xlim(*xl); a.set_ylim(*yl)
            a.set_title(f'({next(letters)}) {inst}, {st}', loc='left', fontsize=7.6)
            a.text(0.03, 0.97, txt[1], color=C_BH, fontsize=6.0, transform=a.transAxes, va='top', bbox=dict(fc='white', ec='none', alpha=.85, pad=0.6))
            a.text(0.03, 0.86, txt[0], color=C_NS, fontsize=6.0, transform=a.transAxes, va='top', bbox=dict(fc='white', ec='none', alpha=.85, pad=0.6))
            a.set_xlabel(xlab, fontsize=6.6)
            a.tick_params(labelsize=6.5)
            if k == 0:
                a.set_ylabel(ylab, fontsize=6.6)
            else:
                a.tick_params(labelleft=False)
            a.grid(color=GRID, lw=.4)
    rows = []
    for m, nm in (('LR', 'H-LR'), ('RF', 'H-RF')):
        rows.append(('RXTE dev. sample, LOSO', m, row(v7, analysis='v2 OOF', model=nm, group='soft-like', metric='obs_AUC'),
                     row(v7, analysis='v2 OOF', model=nm, group='hard-like', metric='obs_AUC')))
    for m in ('LR', 'RF'):
        rows.append(('NICER N1 (prefix), LOSO', m, row(v9, analysis='NICER all-state LOSO | soft-like', comparison=f'H_N-{m}', metric='obs_AUC'),
                     row(v9, analysis='NICER all-state LOSO | hard-like', comparison=f'H_N-{m}', metric='obs_AUC')))
    for m in ('LR', 'RF'):
        rows.append(('NICER N2, frozen N1 models', m, row(v11, analysis='new obs | soft-like', comparison=f'H_N-{m}', metric='obs_AUC'),
                     row(v11, analysis='new obs | hard-like', comparison=f'H_N-{m}', metric='obs_AUC')))
    for m in ('LR', 'RF'):
        rows.append(('NICER N1+N2 with 3C50, LOSO', m, row(v12, analysis='soft-like', comparison=f'H_N-{m}'), row(v12, analysis='hard-like', comparison=f'H_N-{m}')))
    for m in ('LR', 'RF'):
        rows.append(('NICER N3 with 3C50, frozen', m, row(v13, analysis='soft-like', comparison=f'H_N-{m}'), row(v13, analysis='hard-like', comparison=f'H_N-{m}')))
    a = fig.add_subplot(gs[1, 1:])
    n = len(rows)
    for i, (lbl, m, so, ha) in enumerate(rows):
        y = n - 1 - i
        for d_, rr, col, mk, filled in ((-.18, so, '#9a9893', 'o', False), (.18, ha, COL[m], MK[m], True)):
            a.plot([rr.ci2_5, rr.ci97_5], [y + d_] * 2, color=col, lw=1.3)
            a.plot(rr.point, y + d_, mk, ms=4.4, color=col, mfc=col if filled else 'white', mew=1.1)
        a.text(1.035, y, f'{ha.point:.2f} / {so.point:.2f}', fontsize=6.4, va='center', color=INK, transform=a.get_yaxis_transform())
    a.text(1.035, n - .35, 'hard / soft', fontsize=6.4, va='bottom', color=INK, fontweight='bold', transform=a.get_yaxis_transform())
    a.set_yticks(range(n)); a.set_yticklabels([f'{r[0]}, {r[1]}' for r in rows][::-1], fontsize=7)
    a.axvline(.5, color=INK2, lw=.7, ls='--'); a.set_xlim(.2, 1.02); a.set_ylim(-.6, n - .4)
    for k in range(2, n, 2):
        a.axhline(n - k - .5, color=GRID, lw=.6)
    a.set_xlabel('observation-level AUC of the colour-only model (95% class-stratified source bootstrap)')
    a.set_title('(e) colours alone: soft-like (grey, open) versus hard-like (colour, filled)', loc='left', fontsize=7.8)
    a.legend(handles=[Line2D([], [], color='#9a9893', marker='o', mfc='white', ls='-', ms=4.5, label='soft-like'),
                      Line2D([], [], color=C_LR, marker='s', ls='-', ms=4.5, label='hard-like, LR'),
                      Line2D([], [], color=C_RF, marker='o', ls='-', ms=4.5, label='hard-like, RF')],
               loc='upper left', frameon=True, framealpha=.95, edgecolor='none', fontsize=6.6, handlelength=1.4)
    fig.savefig(OUT / 'fig3_states.pdf')
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ Figure 4
def fig4():
    F = pd.read_csv(R / 'final_timing_gain_across_versions.csv')
    P10 = pd.read_csv(R / 'v10a/v10a_pooled_gain.csv')
    g = lambda lab, m: row(F, label=lab, model=m)
    nfull = row(P10, component='NICER (full)')
    H = None
    rows = [
        ('RXTE/PCA', H),
        ('development sample, LOSO [180 obs; 7 BH / 17 NS src]', ('LR', g('v8a RXTE v2 sample', 'LR'), True, 'dev.', '-', 'before (v8)')),
        ('', ('RF', g('v8a RXTE v2 sample', 'RF'), False, 'dev.', '-', '')),
        ('external sources, frozen models [99; 5 / 15]', ('LR', g('v8b RXTE external (frozen)', 'LR'), True, 'new src', '-', 'before (v8)')),
        ('NICER N1 (development)', H),
        ('file prefixes, LOSO [142; 7 / 32]', ('LR', g('v9a NICER (prefix)', 'LR'), True, 'dev.', 'none', 'before (v9)')),
        ('', ('RF', g('v9a NICER (prefix)', 'RF'), False, 'dev.', 'none', '')),
        ('full files, LOSO [144; 7 / 32]', ('LR', nfull, False, 'dev.', 'none', '')),
        ('', ('RF', g('v10 NICER full', 'RF'), False, 'dev.', 'none', '')),
        ('Pooled re-analysis', H),
        ('RXTE dev. + external + N1 full [423]', ('LR', g('v10a pooled RXTE+NICER', 'LR'), True, 'reuse', 'none', 'before (v10)')),
        ('NICER N2 (unseen observations, same sources)', H),
        ('frozen N1 models [143; 9 / 33]', ('LR', g('v11a NICER new obs (frozen)', 'LR'), True, 'new obs', 'none', 'before data')),
        ('', ('RF', g('v11 NICER new obs (frozen)', 'RF'), False, 'new obs', 'none', '')),
        ('NICER N1+N2 re-analysed with 3C50 background', H),
        ('corrected + screened, LOSO [202; 8 / 34]', ('RF', g('v12b NICER 3C50-corrected', 'RF'), True, 'reuse', '3C50', 'after N1, N2')),
        ('', ('LR', g('v12 NICER 3C50-corrected', 'LR'), False, 'reuse', '3C50', '')),
        ('NICER N3 (unseen observations, fixed pipeline)', H),
        ('frozen corrected models [74; 8 / 19]', ('RF', g('v13a NICER third set (frozen)', 'RF'), True, 'new obs', '3C50', 'before data')),
        ('', ('LR', g('v13 NICER third set (frozen)', 'LR'), False, 'new obs', '3C50', '')),
    ]
    fig, a = plt.subplots(figsize=(6.9, 5.6))
    n = len(rows)
    ticks, labels, bold = [], [], []
    COLX = (0.55, 0.69, 0.80, 0.93)
    for i, (lab, spec) in enumerate(rows):
        y = n - 1 - i
        if spec is None:
            ticks.append(y); labels.append(lab); bold.append(True)
            if i: a.axhline(y + .5, color=GRID, lw=.7, xmin=0, xmax=1)
            continue
        m, r, prim, dat, bkg, when = spec
        lo = r['ci2_5'] if 'ci2_5' in r else r['lo']; hi = r['ci97_5'] if 'ci97_5' in r else r['hi']
        ci_point(a, y, r['point'], lo, hi, m, prim)
        ticks.append(y); labels.append(f'{lab}   {m}' if lab else m); bold.append(False)
        cells = (dat, bkg, 'primary' if prim else 'descr.', f'{m} {when}' if prim else '')
        for x, t in zip(COLX, cells):
            a.text(x, y, t, fontsize=7.3, va='center', ha='left', color=INK if prim else INK2)
    for x, t in zip(COLX, ('data', 'bkg', 'role', 'model fixed')):
        a.text(x, n - .45, t, fontsize=7.4, fontweight='bold', va='bottom', ha='left', color=INK)
    a.set_yticks(ticks); a.set_yticklabels(labels, fontsize=7.6)
    for tl, b_ in zip(a.get_yticklabels(), bold):
        if b_: tl.set_fontweight('bold'); tl.set_color(INK)
    a.tick_params(axis='y', length=0)
    a.spines['left'].set_visible(False)
    a.axvline(0, color=INK2, lw=.7, ls='--')
    a.set_xlim(-0.25, 1.12); a.set_ylim(-.6, n - .1)
    a.set_xticks(np.arange(-0.2, 0.51, 0.1))
    a.spines['bottom'].set_bounds(-0.25, 0.5)
    a.set_xlabel('hard-like observation-level AUC gain: (two colours + T1, T2, T3) - (two colours), same model class\n'
                 '(95% class-stratified source bootstrap of fixed out-of-source predictions)', x=0.36)
    for x in np.arange(-0.2, 0.51, 0.1):
        a.axvline(x, color=GRID, lw=.4, zorder=0)
    fig.legend(handles=[Line2D([], [], color=C_LR, marker='s', ls='-', ms=5, label='LR'),
                        Line2D([], [], color=C_RF, marker='o', ls='-', ms=5, label='RF'),
                        Line2D([], [], color=INK2, marker='o', ls='', ms=5, label='filled: primary'),
                        Line2D([], [], color=INK2, marker='o', mfc='white', ls='', ms=5, label='open: descriptive')],
               loc='upper center', bbox_to_anchor=(0.42, 0.955), frameon=False, ncol=4, fontsize=7.6)
    fig.savefig(OUT / 'fig4_timing_gain.pdf')
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ Figure 5
def fig5():
    A = pd.read_csv(R / 'v13/v13a_gain.csv')
    G = pd.read_csv(R / 'v13/v13a_gti_restricted.csv').iloc[0]
    I = pd.read_csv(R / 'v13/v13a_influence.csv')
    fig, ax = plt.subplots(2, 1, figsize=(5.6, 4.9), gridspec_kw=dict(height_ratios=[1, 1.3], hspace=0.5))
    a = ax[0]
    mods = [('H_N-LR', 'LR', 'colours'), ('H_N+T_N-LR', 'LR', 'colours + T'), ('H_N-RF', 'RF', 'colours'), ('H_N+T_N-RF', 'RF', 'colours + T')]
    for i, (nm, m, lab) in enumerate(mods):
        y = len(mods) - 1 - i
        so = row(A, analysis='soft-like', comparison=nm); ha = row(A, analysis='hard-like', comparison=nm)
        a.plot([so.ci2_5, so.ci97_5], [y - .17] * 2, color='#9a9893', lw=1.3)
        a.plot(so.point, y - .17, 'o', ms=4.5, color='#9a9893', mfc='white', mew=1.1)
        a.plot([ha.ci2_5, ha.ci97_5], [y + .17] * 2, color=COL[m], lw=1.3)
        a.plot(ha.point, y + .17, MK[m], ms=4.8, color=COL[m], mew=1.1)
        a.text(ha.point, y + .42, f'{ha.point:.3f}', fontsize=6.5, ha='center', color=INK)
    a.set_yticks(range(len(mods))); a.set_yticklabels([f'{m[1]}: {m[2]}' for m in mods][::-1])
    a.axvline(.5, color=INK2, lw=.7, ls='--'); a.set_xlim(.2, 1.02); a.set_ylim(-.6, len(mods) - .25)
    a.set_xlabel('observation-level AUC (95% class-stratified source bootstrap)')
    a.set_title('(a) NICER N3, frozen models: hard-like (colour, filled) and soft-like (grey, open)', loc='left')
    a.grid(axis='x', color=GRID, lw=.5)
    b = ax[1]
    rr = [
        ('obs. AUC gain, primary (RF)', row(A, analysis='hard-like', comparison='H_N+T_N-RF - H_N-RF'), 'RF', True),
        ('obs. AUC gain, 3C50-GTI timing (RF)', dict(point=G.point, ci2_5=G.ci2_5, ci97_5=G.ci97_5), 'RF', False),
        ('obs. AUC gain, LR', row(A, analysis='hard-like', comparison='H_N+T_N-LR - H_N-LR'), 'LR', False),
        ('obs. balanced-accuracy gain (RF)', row(A, analysis='hard-like source level', comparison='H_N+T_N-RF - H_N-RF', metric='obs_balanced_accuracy'), 'RF', False),
        ('source-level AUC gain (RF)', row(A, analysis='hard-like source level', comparison='H_N+T_N-RF - H_N-RF', metric='source_AUC'), 'RF', False),
        ('source-level bal.-acc. gain (RF)', row(A, analysis='hard-like source level', comparison='H_N+T_N-RF - H_N-RF', metric='source_balanced_accuracy'), 'RF', False),
    ]
    n = len(rr) + 1
    for i, (lab, r, m, prim) in enumerate(rr):
        y = n - 1 - i
        ci_point(b, y, r['point'], r['ci2_5'], r['ci97_5'], m, prim)
        b.text(1.0, y, f"{r['point']:+.3f} [{r['ci2_5']:+.3f}, {r['ci97_5']:+.3f}]", fontsize=6.4, va='center', ha='left',
               color=INK, transform=b.get_yaxis_transform())
    y = 0
    lo, hi = I.rf_gain.min(), I.rf_gain.max()
    b.plot([lo, hi], [y, y], color=C_RF, lw=4, alpha=.45, solid_capstyle='butt')
    b.text(1.0, y, f'range {lo:+.3f} to {hi:+.3f} (no CI)', fontsize=6.4, va='center', ha='left', color=INK, transform=b.get_yaxis_transform())
    b.set_yticks(list(range(n))); b.set_yticklabels(['leave one BH source out (8 values)'] + [r[0] for r in rr][::-1])
    b.axvline(0, color=INK2, lw=.7, ls='--'); b.set_xlim(-0.1, 0.4); b.set_ylim(-.6, n - .4)
    b.set_xlabel('difference (colours + T) - (colours only)')
    b.set_title('(b) NICER N3 hard-like gain: alternative features, model and evaluation unit', loc='left')
    b.grid(axis='x', color=GRID, lw=.5)
    fig.savefig(OUT / 'fig5_v13.pdf')
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ Figure A1
def figA1():
    N = pd.read_csv(R / 'final_nuc_difference_across_versions.csv')
    v12 = pd.read_csv(R / 'v12/v12a_nuc.csv')
    v13 = pd.read_csv(R / 'v13/v13b_nuc.csv')
    v11p = pd.read_csv(R / 'v11/v11b_post_hoc_screens.csv')
    rows = [
        ('RXTE dev. sample, all states (v6d)', row(N, label='v6d RXTE v2 (all states)'), 'descr.'),
        ('RXTE external sources, all states (v6d)', row(N, label='v6d RXTE external (all states)'), 'descr.'),
        ('NICER N1 prefix, hard-like (v9b)', row(N, label='v9b NICER prefix'), 'primary'),
        ('RXTE hard-like (v10b)', row(N, label='v10b RXTE hard-like'), 'descr.'),
        ('NICER N1 full, hard-like (v10b)', row(N, label='v10b NICER full'), 'descr.'),
        ('pooled RXTE + NICER N1 (v10b)', row(N, label='v10b pooled RXTE+NICER'), 'primary'),
        ('NICER N2, hard-like (v11b)', row(N, label='v11b NICER new obs'), 'primary'),
        ('  N2, background-ratio screen (post hoc)', dict(D=v11p.D.iloc[1], p=v11p.p.iloc[1]), 'post hoc'),
        ('  N2, also c2 <= 0.7 (post hoc)', dict(D=v11p.D.iloc[3], p=v11p.p.iloc[3]), 'post hoc'),
        ('NICER N1+N2, 3C50 corrected (v12a)', row(N, label='v12a NICER 3C50-corrected'), 'primary'),
        ('  N1+N2, no screening/correction', dict(D=v12.D.iloc[4], p=v12.p.iloc[4]), 'descr.'),
        ('NICER N3, 3C50 corrected (v13b)', row(N, label='v13b NICER third set'), 'primary'),
        ('  N3, no screening/correction', dict(D=v13.D.iloc[1], p=v13.p.iloc[1]), 'descr.'),
        ('  N3, 3C50-GTI timing features', dict(D=v13.D.iloc[-1], p=v13.p.iloc[-1]), 'descr.'),
    ]
    fig, a = plt.subplots(figsize=(6.0, 3.6))
    n = len(rows)
    for i, (lab, r, role) in enumerate(rows):
        y = n - 1 - i
        prim = role == 'primary'
        col = INK if prim else ('#9a9893' if role == 'post hoc' else INK2)
        a.plot(r['D'], y, 's' if prim else ('^' if role == 'post hoc' else 'o'), ms=5.2, color=col, mfc=col if prim else 'white', mew=1.1)
        a.text(0.12, y, f"p = {r['p']:.3g}   {role}", fontsize=6.6, va='center', color=col)
    a.set_yticks(range(n)); a.set_yticklabels([r[0] for r in rows][::-1], fontsize=7)
    a.axvline(0, color=INK2, lw=.7, ls='--'); a.set_xlim(-0.8, 0.45); a.set_ylim(-.6, n - .4)
    a.set_xlabel('D = mean BH residual - mean NS residual of log$_{10}\\,\\nu_c$ at matched colour (dex)')
    a.grid(axis='x', color=GRID, lw=.5)
    fig.savefig(OUT / 'figA1_nuc.pdf')
    plt.close(fig)


if __name__ == '__main__':
    for f in (fig2, fig3, fig4, fig5, figA1):
        f(); print('wrote', f.__name__)
