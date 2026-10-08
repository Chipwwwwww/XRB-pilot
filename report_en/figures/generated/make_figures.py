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
  G6_v6a_external.pdf      redraw of figures/v6/v6a_external_sources.png from results/v6/v6a_external_per_source.csv
                           (same points; labels placed without overlap)
  G7_v7c3_rxte_maxi.pdf    redraw of figures/v7c/v7c3_rxte_vs_maxi.png from results/v7c/v7c3_rxte_vs_maxi.csv
                           (same points; labels placed without overlap; y axis zoomed to the data)
  G8_v4a_forest.pdf        redraw of figures/v4/v4a_forest_source_auc.png from results/v4/v4a_bootstrap.csv
                           (same rows, order, colours and intervals; short row labels and part bands for legibility)
Style: the repository plot style (scripts/plotstyle.py; BH blue, NS orange, validated categorical order)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from plotstyle import plt, CLASS_COLOR, INK, INK2, GRID, SERIES   # noqa: E402

# Figures are drawn at close to their printed width (\textwidth = 6.27 in), so the font sizes below are the printed sizes.
plt.rcParams.update({'savefig.dpi': 200, 'font.size': 8.5, 'axes.titlesize': 9, 'axes.axisbelow': True})
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

    fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 5.5), sharey=True, gridspec_kw=dict(width_ratios=[1.25, 1]))
    yy = np.arange(len(d))[::-1]
    a.barh(yy, d.n_bh, color=CLASS_COLOR['BH'], height=.62, label='BH sources (dynamically confirmed)')
    a.barh(yy, d.n_ns, left=d.n_bh, color=CLASS_COLOR['NS'], height=.62, label='NS sources')
    a.barh(yy, d.cand, left=d.n_bh + d.n_ns, color=CAND, height=.62, label='BH candidates (unlabelled)')
    for v, (nb, nn, nc) in zip(yy, zip(d.n_bh, d.n_ns, d.cand)):
        txt = f'{nb} BH / {nn} NS' if nc == 0 else f'{nc} candidates'
        a.text(nb + nn + nc + 1.2, v, txt, va='center', fontsize=7.5, color=INK2)
    a.set_yticks(yy); a.set_yticklabels(d.label, fontsize=8); a.set_xlabel('number of sources')
    a.set_xlim(0, (d.n_bh + d.n_ns + d.cand).max() * 1.4)
    fig.legend(*a.get_legend_handles_labels(), loc='lower center', ncol=3, fontsize=8, bbox_to_anchor=(0.5, 0.0))
    a.set_title('(a) sources per sample', loc='left')
    b.barh(yy, d.n_obs, color=INK2, height=.62)
    for v, n in zip(yy, d.n_obs):
        b.text(n * 1.08, v, f'{n:,}', va='center', fontsize=7.5, color=INK2)
    b.set_xscale('log'); b.set_xlim(50, d.n_obs.max() * 8); b.set_xlabel('observations (log; MAXI: 1-day points)')
    b.set_title('(b) observations per sample', loc='left')
    for ax in (a, b):
        for k, ph in enumerate(sorted(d.phase.unique())):
            idx = yy[d.phase.values == ph]
            if k % 2 == 0: ax.axhspan(idx.min() - .5, idx.max() + .5, color=GRID, alpha=.35, lw=0, zorder=0)
        ax.grid(axis='y', visible=False)
    fig.tight_layout(rect=[0, 0.045, 1, 1])
    save(fig, 'G1_sample_sizes.pdf')


# --------------------------------------------------------------------------------------------- G2
BANDS = [(5, 7, 'b1'), (7, 10, 'b2'), (10, 16, 'b3'), (16, 25.1, 'b4')]


def g2_spectra():
    z = npz('data/v2/processed/features.npz')
    rate, F, y, e = z['rate'], z['F'], z['y'], z['edges']
    ec = np.sqrt(e[:-1] * e[1:]); B = rate / F[:, None]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.1))
    for ax, M, lab in ((axes[0], rate, 'net count rate  [count s$^{-1}$ keV$^{-1}$ PCU$^{-1}$]'),
                       (axes[1], B, 'shape: rate / F(5–25 keV)  [keV$^{-1}$]')):
        for k, (lo, hi, nm) in enumerate(BANDS):
            m = (ec >= lo) & (ec < hi)
            ax.axvspan(e[:-1][m].min(), e[1:][m].max(), color=GRID if k % 2 == 0 else '#f1f0ec', lw=0, zorder=0)
            ax.text(np.sqrt(e[:-1][m].min() * e[1:][m].max()), 0.97, nm, transform=ax.get_xaxis_transform(),
                    ha='center', va='top', fontsize=8, color=INK2)
        for cls, yv in (('NS', 0), ('BH', 1)):
            Mc = M[y == yv]
            Mc = np.where(Mc > 0, Mc, np.nan)
            q16, q50, q84 = np.nanpercentile(Mc, [16, 50, 84], axis=0)
            ax.fill_between(ec, q16, q84, color=CLASS_COLOR[cls], alpha=.18, lw=0)
            ax.plot(ec, q50, color=CLASS_COLOR[cls], lw=1.8, label=f'{cls}: median, 16–84% ({int((y == yv).sum())} obs)')
        ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel('energy [keV] (channel geometric centre)')
        ax.set_xticks([5, 7, 10, 16, 25]); ax.set_xticklabels(['5', '7', '10', '16', '25']); ax.minorticks_off()
        ax.set_ylabel(lab, fontsize=7.5)
    axes[0].set_title('(a) A before asinh (intensity kept)', loc='left')
    axes[1].set_title('(b) B (per-spectrum shape)', loc='left')
    axes[1].legend(loc='lower left', fontsize=7.5)
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
    fig = plt.figure(figsize=(6.6, 6.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[0.045, 0.045, 1], wspace=0.05)
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
    # source names on the right; where two blocks are too close, the second name moves to a second column
    am.set_yticks([]); col, last = 0, -1e9
    for m_, b_ in zip(mids, bounds[:-1]):
        col = 1 - col if m_ - last < 9 else 0; last = m_
        am.annotate(go[int(b_)], xy=(1.0, m_ - .5), xycoords=('axes fraction', 'data'), xytext=(3 + 62 * col, 0),
                    textcoords='offset points', va='center', fontsize=6.5, color=INK2,
                    arrowprops=dict(arrowstyle='-', color=GRID, lw=.6) if col else None)
    nb = int((y == 1).sum())
    ay.text(0, nb / 2, 'BH', rotation=90, ha='center', va='center', color='white', fontsize=7.5, fontweight='bold')
    ay.text(0, (nb + len(y)) / 2, 'NS', rotation=90, ha='center', va='center', color='white', fontsize=7.5, fontweight='bold')
    for b in bounds[1:-1]:
        am.axhline(b - .5, color='white', lw=.5)
    am.axhline(nb - .5, color=INK, lw=1.2)
    ticks = [0, 4, 11, 26, 44]
    am.set_xticks(ticks); am.set_xticklabels([f'{k}\n{e[k]:.2f}' for k in ticks], fontsize=7.5)
    am.set_xlabel('column j (energy bin index) and its lower edge [keV]')
    am.set_title('B-shape design matrix log$_{10}$(rate / F): 456 rows (105 BH above the black line,\n351 NS below) × 45 columns', loc='left', fontsize=8.5)
    cax = am.inset_axes([0.0, -0.17, 0.45, 0.022]); cb = fig.colorbar(im, cax=cax, orientation='horizontal')
    cb.set_label('log$_{10}$ B$_{ij}$  [keV$^{-1}$]', fontsize=7.5); cb.ax.tick_params(labelsize=7)
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
    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    yy = np.arange(len(d))[::-1]
    for v, r in zip(yy, d.itertuples()):
        ax.plot([r.loso, r.leaky], [v, v], color=INK2, lw=1.2, zorder=1)
        ax.text(r.leaky + .006, v, f'+{r.gap:.3f}', va='center', fontsize=7.5, color=INK2)
    ax.scatter(d.loso, yy, s=36, color=SERIES[0], zorder=2, label='leave-one-source-out (sources never shared)')
    ax.scatter(d.leaky, yy, s=36, facecolor='white', edgecolor=SERIES[1], lw=1.6, zorder=2, label='observation-wise 5-fold (leaky)')
    ax.set_yticks(yy); ax.set_yticklabels(d.lab, fontsize=8)
    ax.axhline(yy[d.version.str.startswith('v1').values].min() - .5, color=INK2, lw=.6)
    ax.set_xlabel('observation-level balanced accuracy'); ax.set_xlim(0.58, 0.95)
    ax.legend(loc='upper center', bbox_to_anchor=(0.42, -0.13), ncol=1, fontsize=8)
    ax.set_title('Optimistic bias of observation-wise splits\n(number = leaky − LOSO)', loc='left')
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
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 4.4), sharey=True)
    yy = np.arange(len(labels))[::-1]
    for ax, metric, ttl in ((axes[0], 'source_AUC', '(a) source AUC difference'),
                            (axes[1], 'source_balanced_accuracy', '(b) source BA difference')):
        q = d[d.metric == metric].set_index('label').loc[labels]
        for v, r in zip(yy, q.itertuples()):
            col = SERIES[1] if r.lo > 0 else (SERIES[0] if r.hi < 0 else INK2)
            prim = '[primary]' in r.Index
            ax.plot([r.lo, r.hi], [v, v], color=col, lw=1.6)
            ax.plot(r.point, v, 's' if prim else 'o', color=col, mfc=col if prim else 'white', ms=5.5, mew=1.4)
        ax.axvline(0, color=INK2, lw=.8, ls='--'); ax.set_title(ttl, loc='left'); ax.set_xlabel('paired difference, 95% CI')
    axes[0].set_yticks(yy); axes[0].set_yticklabels(labels, fontsize=7.5)
    fig.text(0.01, 0.005, 'Squares = pre-registered primary. Orange = 95% CI entirely > 0; blue = entirely < 0; grey = includes 0.',
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    save(fig, 'G5_phase12_forest.pdf')


def place_labels(ax, x, y, names, fs=6.5, color=None):
    """Greedy, deterministic label placement: for every point (most crowded first) try offsets on rings of growing
    radius and keep the first position whose text box overlaps no other label, no data point and stays inside the axes.
    Labels not directly next to their marker get a thin leader line."""
    fig = ax.figure; fig.canvas.draw(); R = fig.canvas.get_renderer(); pt = fig.dpi / 72
    P = ax.transData.transform(np.c_[x, y]); axbb = ax.get_window_extent(R)
    size = []
    for nm in names:
        t = ax.text(0, 0, nm, fontsize=fs); bb = t.get_window_extent(R); size.append((bb.width, bb.height)); t.remove()
    crowd = np.array([(np.hypot(*(P - p).T) < 40 * pt).sum() for p in P])
    pr = 3.2 * pt                                   # marker half-size used as an obstacle
    pts_boxes = [(px - pr, py - pr, px + pr, py + pr) for px, py in P]
    placed = []

    def hits(b, boxes, pad=1.0 * pt):
        return sum(1 for c in boxes if not (b[2] + pad < c[0] or c[2] + pad < b[0] or b[3] + pad < c[1] or c[3] + pad < b[1]))
    angles = np.deg2rad([45, 135, -45, -135, 0, 180, 90, -90, 22.5, 157.5, -22.5, -157.5, 67.5, 112.5, -67.5, -112.5])
    for i in sorted(range(len(P)), key=lambda k: (-crowd[k], k)):
        (px, py), (w, h) = P[i], size[i]
        best = None
        for r in (4, 8, 13, 19, 26, 34, 44, 56):
            for a in angles:
                c, s_ = np.cos(a), np.sin(a)
                ax_, ay_ = px + r * pt * c, py + r * pt * s_
                l = ax_ if c > .25 else (ax_ - w if c < -.25 else ax_ - w / 2)
                b = ay_ if s_ > .25 else (ay_ - h if s_ < -.25 else ay_ - h / 2)
                box = (l, b, l + w, b + h)
                inside = box[0] >= axbb.x0 and box[2] <= axbb.x1 and box[1] >= axbb.y0 and box[3] <= axbb.y1
                own = [pb for j, pb in enumerate(pts_boxes) if j != i]
                cost = hits(box, placed) * 10 + hits(box, own) + (0 if inside else 100)
                if best is None or cost < best[0]: best = (cost, r, a, box)
                if cost == 0: break
            if best[0] == 0: break
        cost, r, a, box = best; placed.append(box)
        c, s_ = np.cos(a), np.sin(a)
        ax.annotate(names[i], (x[i], y[i]), xytext=(r * c, r * s_), textcoords='offset points', fontsize=fs,
                    ha='left' if c > .25 else ('right' if c < -.25 else 'center'),
                    va='bottom' if s_ > .25 else ('top' if s_ < -.25 else 'center'), color=color or INK,
                    arrowprops=dict(arrowstyle='-', lw=.4, color=INK2, shrinkA=0, shrinkB=2.5) if r >= 8 else None)


# --------------------------------------------------------------------------------------------- G6
def g6_v6a_external():
    """Same data and encoding as scripts/30_v6_analysis.py (figure v6a_external_sources.png)."""
    perE = pd.read_csv(ROOT / 'results/v6/v6a_external_per_source.csv')
    pe = perE.pivot_table(index=['source_id', 'true_label', 'role'], columns='name', values='score').reset_index()
    mk = {'E_v4b2': 'o', 'E_new': 's', 'stress_slow_pulsar': '^'}
    rl = {'E_v4b2': 'external (v4b2 sources)', 'E_new': 'external (new sources)', 'stress_slow_pulsar': 'slow-pulsar stress set'}
    fig, axes = plt.subplots(2, 1, figsize=(6.4, 9.0))
    for a, m in zip(axes, ['H_R+T-LR', 'CCTLR (H_R)']):
        for (lab, role), d in pe.groupby(['true_label', 'role']):
            a.scatter(d['H_R-LR'], d[m], marker=mk[role], s=34, color=CLASS_COLOR[lab], alpha=.85, zorder=3,
                      label=f'{lab}, {rl[role]}')
        a.plot([0, 1], [0, 1], color=INK2, lw=.6); a.axhline(.5, color=INK2, ls='--', lw=.6); a.axvline(.5, color=INK2, ls='--', lw=.6)
        a.set_xlim(-0.04, 1.04); a.set_ylim(-0.1, 1.0)
        a.set_xlabel('frozen H_R-LR source score'); a.set_ylabel(f'frozen {m} source score'); a.set_title(m, loc='left')
        place_labels(a, pe['H_R-LR'].values, pe[m].values, list(pe.source_id), fs=6.3)
    axes[0].legend(fontsize=7, loc='upper left')
    fig.tight_layout()
    save(fig, 'G6_v6a_external.pdf')


# --------------------------------------------------------------------------------------------- G7
def g7_v7c3():
    """Same data and encoding as scripts/39_v7c2_analysis.py (figure v7c3_rxte_vs_maxi.png)."""
    from scipy.stats import spearmanr
    pr = pd.read_csv(ROOT / 'results/v7c/v7c3_rxte_vs_maxi.csv')
    agree = float(((pr.rxte_score >= .5) == (pr.maxi_score >= .5)).mean()); rho = spearmanr(pr.rxte_score, pr.maxi_score)[0]
    fig, a = plt.subplots(figsize=(6.0, 4.6))
    for lab in ('NS', 'BH'):
        d = pr[pr.label == lab]; a.scatter(d.rxte_score, d.maxi_score, s=26, color=CLASS_COLOR[lab], label=lab, zorder=3)
    a.axhline(.5, color=INK2, ls='--', lw=.6); a.axvline(.5, color=INK2, ls='--', lw=.6); a.plot([0, 1], [0, 1], color=INK2, lw=.5)
    a.set_xlim(-0.02, 1.0); a.set_ylim(0.22, 0.66)
    a.set_xlabel('RXTE/PCA source score (H-LR, LOSO)'); a.set_ylabel('MAXI/GSC source score (LR, CCI, LOSO)')
    a.legend(fontsize=7.5, loc='upper left')
    a.set_title(f'v7c3: {len(pr)} sources seen by both instruments (Spearman rho = {rho:.2f}, agreement {agree:.2f})', loc='left', fontsize=8.5)
    place_labels(a, pr.rxte_score.values, pr.maxi_score.values, list(pr.rxte_source), fs=6.3)
    fig.tight_layout()
    save(fig, 'G7_v7c3_rxte_maxi.pdf')


# --------------------------------------------------------------------------------------------- G8
def g8_v4a_forest():
    """Same rows, order, colours and intervals as scripts/16_v4a_algorithms.py (figure v4a_forest_source_auc.png)."""
    bs = pd.read_csv(ROOT / 'results/v4/v4a_bootstrap.csv'); REF = 'H_colours|LogReg'
    part_of = bs.groupby('name', sort=False).part.first().to_dict()
    S = bs[bs.metric == 'source_AUC']; pt = S[~S.comparison.str.contains(' - ')].set_index('name')
    B_ = bs[(bs.metric == 'source_balanced_accuracy') & bs.comparison.str.contains(' - ')].set_index('name')
    order = [REF] + [n for p in ['1e_primary', '1d_nested_per_algorithm', '1b_fixed', '1c_source_weighted'] for n in pt.index if part_of[n] == p]
    colp = {'reference_v2': INK, '1e_primary': '#c2410c', '1d_nested_per_algorithm': '#4a3aa7', '1b_fixed': '#2a78d6', '1c_source_weighted': '#1baf7a'}
    plab = {'reference_v2': 'reference', '1e_primary': 'PRIMARY 1e', '1d_nested_per_algorithm': '1d: nested, per algorithm',
            '1b_fixed': '1b: fixed settings', '1c_source_weighted': '1c: source-equal weights'}
    rs = {'H_colours': 'H', 'HI_colours_intensity': 'HI', 'B_shape': 'B', 'A_intensity': 'A', 'auto': 'auto'}
    ms = {'LogReg': 'LR', 'RandomForest': 'RF', 'ExtraTrees': 'ExtraTrees', 'HistGB': 'HistGB', 'SVM_RBF': 'SVM-RBF', 'kNN': 'kNN',
          'QDA': 'QDA', 'MLP': 'MLP', 'auto': 'automatic selection'}

    def short(n):
        r, m = n.split('|'); m = m.replace('nested:', '').replace('[srcw]', '')
        return f'{rs[r]} · {ms[m]}' + ('  (v2 baseline)' if n == REF else '')
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 8.3), sharey=True, gridspec_kw=dict(width_ratios=[1, 1], wspace=0.06))
    yy = np.arange(len(order))
    for i, n in enumerate(order):
        c = colp[part_of[n]]; lw = 1.6 if part_of[n] in ('1e_primary', 'reference_v2') else 1.0
        axes[0].plot([pt.loc[n, 'ci2_5'], pt.loc[n, 'ci97_5']], [i, i], color=c, lw=lw); axes[0].plot(pt.loc[n, 'point'], i, 'o', color=c, ms=3)
        if n != REF:
            axes[1].plot([B_.loc[n, 'ci2_5'], B_.loc[n, 'ci97_5']], [i, i], color=c, lw=lw); axes[1].plot(B_.loc[n, 'point'], i, 'o', color=c, ms=3)
    parts = [part_of[n] for n in order]
    for k, p in enumerate(dict.fromkeys(parts)):
        idx = [i for i, q in enumerate(parts) if q == p]
        for ax in axes:
            if k % 2 == 1: ax.axhspan(min(idx) - .5, max(idx) + .5, color=GRID, alpha=.45, lw=0, zorder=0)
        axes[1].text(1.02, (min(idx) + max(idx)) / 2, plab[p], transform=axes[1].get_yaxis_transform(), rotation=-90 if len(idx) > 3 else 0,
                     ha='left', va='center', fontsize=7, color=colp[p])
    axes[0].axvline(pt.loc[REF, 'point'], color=INK2, ls='--', lw=.8); axes[1].axvline(0, color=INK2, ls='--', lw=.8)
    axes[0].set_yticks(yy); axes[0].set_yticklabels([short(n) for n in order], fontsize=6.4); axes[0].set_ylim(len(order) - .5, -.5)
    for t, n in zip(axes[0].get_yticklabels(), order): t.set_color(colp[part_of[n]])
    for ax in axes: ax.grid(axis='y', visible=False); ax.tick_params(axis='y', length=0)
    axes[0].set_xlabel('source AUC (95% source bootstrap)'); axes[1].set_xlabel('source BA minus H-LR (paired, 95%)')
    axes[0].set_title('(a) source AUC; dashed = H-LR', loc='left'); axes[1].set_title('(b) source BA difference', loc='left')
    fig.subplots_adjust(left=0.17, right=0.93, top=0.965, bottom=0.06)
    save(fig, 'G8_v4a_forest.pdf')


if __name__ == '__main__':
    g1_sample_sizes(); g2_spectra(); g3_design_matrix(); g4_leakage(); g5_forest(); g6_v6a_external(); g7_v7c3(); g8_v4a_forest()
