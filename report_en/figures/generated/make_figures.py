"""Figures generated for the English technical report (report_en/main.tex).

Read-only: every figure is drawn from files already committed in the repository (data/**/processed/*.npz,
data/**/*.csv, results/**/*.csv). No analysis is re-run, no model is fitted, nothing is downloaded.
Run from anywhere:  python report_en/figures/generated/make_figures.py
Outputs (next to this script):
  G1_sample_sizes.pdf      sources (BH / NS / candidate) and observations per version and sub-sample
  G2_mean_spectra.pdf      v2 count-space spectra (A: rate, B: shape) with the four colour bands of H
  G3_design_matrix.pdf     the real v2 B-shape design matrix (456 x 45), rows grouped by source, with y and g strips
  G4_leakage.pdf           LOSO vs leaky observation-wise 5-fold balanced accuracy (v1, v2)
  G5_phase12_forest.pdf    Phase 1-2 paired differences against two-colour baselines (source AUC, source BA)
Style: the repository plot style (scripts/plotstyle.py; BH blue, NS orange, validated categorical order)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from plotstyle import plt, CLASS_COLOR, INK, INK2, GRID, SERIES   # noqa: E402

plt.rcParams.update({'savefig.dpi': 200, 'font.size': 8.5, 'axes.titlesize': 9})
CAND = '#9e9d98'          # neutral grey for unlabelled BH candidates
CANDCOL = SERIES[2]       # aqua (third validated slot) where a third identity is needed


def npz(p):
    return np.load(ROOT / p)


def save(fig, name):
    fig.savefig(HERE / name)
    plt.close(fig)
    print('written', HERE / name)


# --------------------------------------------------------------------------------------------- G1
def g1_sample_sizes():
    rows = []

    def add(label, phase, y, g, extra_obs_note=''):
        y, g = np.asarray(y), np.asarray(g)
        rows.append(dict(label=label, phase=phase, n_obs=len(y), n_bh=len(set(g[y == 1])), n_ns=len(set(g[y == 0])), cand=0))

    z1 = npz('data/processed/features.npz'); add('v1 RXTE pilot', 1, z1['y'], z1['source_id'])
    z2 = npz('data/v2/processed/features.npz'); add('v2/v3 RXTE (S1)', 1, z2['y'], z2['source_id'])
    zc = npz('data/v3c/processed/features.npz')
    rows.append(dict(label='v3c BH candidates', phase=1, n_obs=len(zc['y']), n_bh=0, n_ns=0, cand=len(set(zc['source_id']))))
    z41 = npz('data/v4b1/processed/features.npz'); add('v4b1 all epoch-5 pointings (S3)', 2, z41['y'], z41['source_id'])
    z42 = npz('data/v4b2/processed/features.npz')
    add('v4b2 + v2, all gain epochs (S2)', 2, np.r_[z2['y'], z42['y']], np.r_[z2['source_id'], z42['source_id']])
    z6 = npz('data/v6/processed/features.npz'); s6 = pd.read_csv(ROOT / 'data/v6/sources.csv').set_index('source_id').role
    keep6 = np.array([s6[s] != 'stress_slow_pulsar' for s in z6['source_id']])
    add('v6 external set E (frozen test)', 3, np.r_[z42['y'], z6['y'][keep6]], np.r_[z42['source_id'], z6['source_id'][keep6]])
    z7 = npz('data/v7b2/processed/features.npz')
    add('v7b2 v2 + persistent BHs', 4, np.r_[z2['y'], z7['y']], np.r_[z2['source_id'], z7['source_id']])
    m = pd.read_csv(ROOT / 'data/v7c/maxi_points.csv'); m = m[m.cls.isin(['BH', 'NPNS'])]
    add('v7c MAXI BH vs NPNS (1-d points)', 4, (m.cls == 'BH').astype(int).values, m.source.values)
    x = pd.read_csv(ROOT / 'data/v8b/processed/external_states_timing.csv'); x = x[x.role != 'stress_slow_pulsar']
    add('v8b external set X', 4, (x.label == 'BH').astype(int).values, x.source_id.values)
    h = pd.read_csv(ROOT / 'data/v8c/processed/hf_features.csv'); h = h[(h['sample'] == 'S1') & (h.status == 'ok')]
    add('v8c S1-HF (event mode)', 4, (h.label == 'BH').astype(int).values, h.source_id.values)
    n9 = pd.read_csv(ROOT / 'data/v9/processed/nicer_features.csv'); n9 = n9[n9.status == 'ok']
    add('v9 NICER (prefix)', 5, (n9.label == 'BH').astype(int).values, n9.source.values)
    n10 = pd.read_csv(ROOT / 'data/v10/processed/nicer_full_features.csv'); n10 = n10[n10.status == 'ok']
    add('v10 NICER (full files)', 5, (n10.label == 'BH').astype(int).values, n10.source.values)
    n11 = pd.read_csv(ROOT / 'data/v11/processed/nicer_new_features.csv'); n11 = n11[n11.status == 'ok']
    add('v11 NICER new obs', 6, (n11.label == 'BH').astype(int).values, n11.source.values)
    c12 = pd.read_csv(ROOT / 'data/v12/processed/nicer_corrected_screened.csv')
    add('v12 NICER 3C50 kept (v10+v11)', 6, (c12.label == 'BH').astype(int).values, c12.source.values)
    p13 = pd.read_csv(ROOT / 'results/v13/v13_frozen_predictions.csv').drop_duplicates('obs_id')
    add('v13 NICER third set, kept', 6, (p13.true_label == 'BH').astype(int).values, p13.source_id.values)
    d = pd.DataFrame(rows)
    d.to_csv(HERE / 'G1_sample_sizes.csv', index=False)

    fig, (a, b) = plt.subplots(1, 2, figsize=(9.2, 5.6), sharey=True, gridspec_kw=dict(width_ratios=[1.15, 1]))
    yy = np.arange(len(d))[::-1]
    a.barh(yy, d.n_bh, color=CLASS_COLOR['BH'], height=.62, label='BH sources (dynamically confirmed)')
    a.barh(yy, d.n_ns, left=d.n_bh, color=CLASS_COLOR['NS'], height=.62, label='NS sources')
    a.barh(yy, d.cand, left=d.n_bh + d.n_ns, color=CAND, height=.62, label='BH candidates (unlabelled)')
    for v, (nb, nn, nc) in zip(yy, zip(d.n_bh, d.n_ns, d.cand)):
        txt = f'{nb} BH / {nn} NS' if nc == 0 else f'{nc} candidates'
        a.text(nb + nn + nc + 1.2, v, txt, va='center', fontsize=7, color=INK2)
    a.set_yticks(yy); a.set_yticklabels(d.label, fontsize=7.5); a.set_xlabel('number of sources')
    a.set_xlim(0, (d.n_bh + d.n_ns + d.cand).max() * 1.35)
    a.legend(loc='upper right', fontsize=7)
    a.set_title('(a) sources per sample', loc='left')
    b.barh(yy, d.n_obs, color=INK2, height=.62)
    for v, n in zip(yy, d.n_obs):
        b.text(n * 1.08, v, f'{n:,}', va='center', fontsize=7, color=INK2)
    b.set_xscale('log'); b.set_xlim(50, d.n_obs.max() * 6); b.set_xlabel('number of observations (log scale; MAXI: 1-day points)')
    b.set_title('(b) observations per sample', loc='left')
    for ax in (a, b):
        for k, ph in enumerate(sorted(d.phase.unique())):
            idx = yy[d.phase.values == ph]
            if k % 2 == 0: ax.axhspan(idx.min() - .5, idx.max() + .5, color=GRID, alpha=.35, lw=0, zorder=0)
    fig.tight_layout()
    save(fig, 'G1_sample_sizes.pdf')


# --------------------------------------------------------------------------------------------- G2
BANDS = [(5, 7, 'b1'), (7, 10, 'b2'), (10, 16, 'b3'), (16, 25.1, 'b4')]


def g2_spectra():
    z = npz('data/v2/processed/features.npz')
    rate, F, y, e = z['rate'], z['F'], z['y'], z['edges']
    ec = np.sqrt(e[:-1] * e[1:]); B = rate / F[:, None]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.5))
    for ax, M, lab in ((axes[0], rate, 'net count rate  [count s$^{-1}$ keV$^{-1}$ PCU$^{-1}$]'),
                       (axes[1], B, 'shape  rate / F(5–25 keV)  [keV$^{-1}$]')):
        for k, (lo, hi, nm) in enumerate(BANDS):
            m = (ec >= lo) & (ec < hi)
            ax.axvspan(e[:-1][m].min(), e[1:][m].max(), color=GRID if k % 2 == 0 else '#f1f0ec', lw=0, zorder=0)
            ax.text(np.sqrt(e[:-1][m].min() * e[1:][m].max()), 0.97, nm, transform=ax.get_xaxis_transform(),
                    ha='center', va='top', fontsize=7.5, color=INK2)
        for cls, yv in (('NS', 0), ('BH', 1)):
            Mc = M[y == yv]
            Mc = np.where(Mc > 0, Mc, np.nan)
            q16, q50, q84 = np.nanpercentile(Mc, [16, 50, 84], axis=0)
            ax.fill_between(ec, q16, q84, color=CLASS_COLOR[cls], alpha=.18, lw=0)
            ax.plot(ec, q50, color=CLASS_COLOR[cls], lw=1.8, label=f'{cls}: median, 16–84% ({int((y == yv).sum())} obs)')
        ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel('energy  [keV]  (channel geometric centre)')
        ax.set_xticks([5, 7, 10, 16, 25]); ax.set_xticklabels(['5', '7', '10', '16', '25']); ax.minorticks_off()
        ax.set_ylabel(lab, fontsize=7.5)
    axes[0].set_title('(a) representation A before asinh (intensity kept)', loc='left')
    axes[1].set_title('(b) representation B (per-spectrum shape)', loc='left')
    axes[1].legend(loc='lower left', fontsize=7)
    fig.tight_layout()
    save(fig, 'G2_mean_spectra.pdf')


# --------------------------------------------------------------------------------------------- G3
def g3_design_matrix():
    z = npz('data/v2/processed/features.npz')
    rate, F, y, g, e = z['rate'], z['F'], z['y'], z['source_id'], z['edges']
    B = rate / F[:, None]
    order = sorted(range(len(y)), key=lambda i: (-y[i], g[i]))
    Bo, yo, go = B[order], y[order], g[order]
    L = np.log10(np.clip(Bo, 1e-5, None))
    fig = plt.figure(figsize=(8.4, 6.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[0.035, 0.035, 1], wspace=0.04)
    ay, ag, am = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
    ay.imshow(yo[:, None], aspect='auto', cmap=plt.matplotlib.colors.ListedColormap([CLASS_COLOR['NS'], CLASS_COLOR['BH']]), interpolation='nearest')
    codes = pd.factorize(go)[0]
    ag.imshow((codes % 2)[:, None], aspect='auto', cmap=plt.matplotlib.colors.ListedColormap(['#d7d6d1', '#7c7b77']), interpolation='nearest')
    for a_ in (ay, ag, am): a_.grid(False)
    im = am.imshow(L, aspect='auto', cmap='Blues', interpolation='nearest')
    for a_, t in ((ay, 'y'), (ag, 'g')):
        a_.set_xticks([]); a_.set_yticks([]); a_.set_title(t, fontsize=8)
    bounds = np.r_[0, np.where(np.diff(codes) != 0)[0] + 1, len(codes)]
    mids = (bounds[:-1] + bounds[1:]) / 2
    am.set_yticks(mids - .5); am.set_yticklabels([go[int(b)] for b in bounds[:-1]], fontsize=5.2)
    am.yaxis.tick_right()
    for b in bounds[1:-1]:
        am.axhline(b - .5, color='white', lw=.5)
    nb = int((y == 1).sum())
    am.axhline(nb - .5, color=INK, lw=1.2)
    ticks = [0, 4, 11, 26, 44]
    am.set_xticks(ticks); am.set_xticklabels([f'{k}\n{e[k]:.2f}' for k in ticks], fontsize=7)
    am.set_xlabel('column j (energy bin index) and its lower edge [keV]')
    am.set_title('B-shape design matrix, log$_{10}$(rate / F)  —  456 rows (105 BH above the black line, 351 NS below) × 45 columns', loc='left', fontsize=8)
    cax = am.inset_axes([1.24, 0.0, 0.03, 1.0]); cb = fig.colorbar(im, cax=cax); cb.set_label('log$_{10}$ B$_{ij}$  [keV$^{-1}$]', fontsize=7.5)
    save(fig, 'G3_design_matrix.pdf')


# --------------------------------------------------------------------------------------------- G4
def g4_leakage():
    recs = []
    for ver, mo, lk in (('v1 (8 sources)', 'results/metrics_observation_level.csv', 'results/secondary_observation_split.csv'),
                        ('v2 (31 sources)', 'results/v2/metrics_observation_level.csv', 'results/v2/secondary_observation_split.csv')):
        a = pd.read_csv(ROOT / mo); b = pd.read_csv(ROOT / lk)
        a = a[a.model != 'Dummy'].set_index(['representation', 'model']).balanced_accuracy
        b = b.set_index(['representation', 'model']).balanced_accuracy
        for k in b.index:
            recs.append(dict(version=ver, rep=k[0], model=k[1], loso=a.loc[k], leaky=b.loc[k]))
    d = pd.DataFrame(recs); d['gap'] = d.leaky - d.loso
    d.to_csv(HERE / 'G4_leakage.csv', index=False)
    short = {'A_intensity': 'A', 'B_shape': 'B', 'H_colours': 'H', 'HI_colours_intensity': 'HI', 'LogReg': 'LR', 'RandomForest': 'RF'}
    d['lab'] = d.version.str.slice(0, 2) + '  ' + d.rep.map(short) + '-' + d.model.map(short)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    yy = np.arange(len(d))[::-1]
    for v, r in zip(yy, d.itertuples()):
        ax.plot([r.loso, r.leaky], [v, v], color=INK2, lw=1.2, zorder=1)
        ax.text(r.leaky + .006, v, f'+{r.gap:.3f}', va='center', fontsize=7, color=INK2)
    ax.scatter(d.loso, yy, s=36, color=SERIES[0], zorder=2, label='leave-one-source-out (sources never shared)')
    ax.scatter(d.leaky, yy, s=36, facecolor='white', edgecolor=SERIES[1], lw=1.6, zorder=2, label='observation-wise 5-fold (leaky)')
    ax.set_yticks(yy); ax.set_yticklabels(d.lab, fontsize=7.5)
    ax.set_xlabel('observation-level balanced accuracy'); ax.set_xlim(0.55, 0.95)
    ax.legend(loc='lower left', fontsize=7)
    ax.set_title('Optimistic bias of observation-wise splits (number = leaky − LOSO)', loc='left')
    fig.tight_layout()
    save(fig, 'G4_leakage.pdf')


# --------------------------------------------------------------------------------------------- G5
def g5_forest():
    R = lambda p: pd.read_csv(ROOT / p)
    sel = []

    def take(label, df, comp, metric, model=None, extra=None):
        q = df[(df.comparison == comp) & (df.metric == metric)]
        if model is not None: q = q[q.model == model]
        if extra is not None: q = q[extra(q)]
        r = q.iloc[0]
        sel.append(dict(label=label, metric=metric, point=r.point, lo=r.ci2_5, hi=r.ci97_5))

    v3a, v3b = R('results/v3/v3a_bootstrap.csv'), R('results/v3/v3b_bootstrap.csv')
    v4a, v4b3 = R('results/v4/v4a_bootstrap.csv'), R('results/v4b3/v4b3_bootstrap.csv')
    v4b2, v4b1 = R('results/v4b2/v4b2_bootstrap.csv'), R('results/v4b1/v4b1_bootstrap.csv')
    items = [
        ('v3a H+B − H (LR)  [primary]', v3a, 'H_plus_B - H_colours', 'LogReg', None),
        ('v3a H+B − H (RF)  [primary]', v3a, 'H_plus_B - H_colours', 'RandomForest', None),
        ('v3a HI+A − HI (LR)', v3a, 'HI_plus_A - HI_colours_intensity', 'LogReg', None),
        ('v3a HI+A − HI (RF)', v3a, 'HI_plus_A - HI_colours_intensity', 'RandomForest', None),
        ('v3b H3 − H (LR)', v3b, 'H3_colours_3_25 - H_colours', 'LogReg', None),
        ('v3b H3+B3 − H3 (RF)', v3b, 'H3_plus_B3 - H3_colours_3_25', 'RandomForest', None),
        ('v4a nested auto-selection − H-LR  [primary]', v4a, 'auto|nested:auto - H_colours|LogReg', None, None),
        ('v4b3 H+X − H (LR, HEXTE subset)', v4b3, 'H+X|LogReg - H|LogReg', None, lambda q: q.subset == 'HEXTE subset'),
        ('v4b3 H+X − H (RF, HEXTE subset)', v4b3, 'H+X|RandomForest - H|RandomForest', None, lambda q: q.subset == 'HEXTE subset'),
        ('v4b2 H-RF − H-LR (46 sources)', v4b2, 'H_count_space|RandomForest - H_count_space|LogReg', None, None),
        ('v4b1 H-LR[srcw] (7,949 obs) − v2 H-LR  [primary]', v4b1, 'H_colours|LogReg[srcw] - H-LR (v2, 456 obs)', None, None),
    ]
    for lab, df, comp, model, extra in items:
        for metric in ('source_AUC', 'source_balanced_accuracy'):
            take(lab, df, comp, metric, model, extra)
    d = pd.DataFrame(sel); d.to_csv(HERE / 'G5_phase12_forest.csv', index=False)
    labels = [i[0] for i in items]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.4), sharey=True)
    yy = np.arange(len(labels))[::-1]
    for ax, metric, ttl in ((axes[0], 'source_AUC', '(a) source-level AUC difference'),
                            (axes[1], 'source_balanced_accuracy', '(b) source-level balanced-accuracy difference')):
        q = d[d.metric == metric].set_index('label').loc[labels]
        for v, r in zip(yy, q.itertuples()):
            col = SERIES[1] if r.lo > 0 else (SERIES[0] if r.hi < 0 else INK2)
            prim = '[primary]' in r.Index
            ax.plot([r.lo, r.hi], [v, v], color=col, lw=1.6)
            ax.plot(r.point, v, 's' if prim else 'o', color=col, mfc=col if prim else 'white', ms=5.5, mew=1.4)
        ax.axvline(0, color=INK2, lw=.8, ls='--'); ax.set_title(ttl, loc='left'); ax.set_xlabel('paired difference (95% source bootstrap)')
    axes[0].set_yticks(yy); axes[0].set_yticklabels(labels, fontsize=7.2)
    fig.text(0.01, 0.005, 'Squares = pre-registered primary. Orange = 95% CI entirely > 0; blue = entirely < 0; grey = includes 0.',
             fontsize=7, color=INK2)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    save(fig, 'G5_phase12_forest.pdf')


if __name__ == '__main__':
    g1_sample_sizes(); g2_spectra(); g3_design_matrix(); g4_leakage(); g5_forest()
