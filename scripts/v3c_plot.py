"""Figure figures/v3/v3c_candidate_scores.png (v3c, preregistration_v3.md §3), drawn only from saved predictions.
Used by the full run of 14_v3c_candidates.py and by its `--plot-only` redraw (no training data, training or bootstrap).

Both panels share one row per source: confirmed sources on top, BH candidates below, each block sorted by the
RandomForest H_colours source-mean BH score (descending, ties by source_id). Each model's own score is looked up by
source_id and drawn at that shared row, so a row is the same source in both panels."""
import numpy as np, pandas as pd
from matplotlib.lines import Line2D
from matplotlib.transforms import blended_transform_factory
from common import ROOT
from plotstyle import plt, INK2, CLASS_COLOR

REP, PLOT_MODELS, SORT_MODEL = 'H_colours', ('LogReg', 'RandomForest'), 'RandomForest'
CAND_COLOR = '#9e9d98'
CAND_CSV = ROOT/'results/v3/v3c_candidate_predictions.csv'      # analysis 1: trained on all 31 confirmed sources
CONF_CSV = ROOT/'results/v2/oof_predictions_loso.csv'           # original v2 LOSO (not the '+cand' sensitivity run)
OUT_PNG = ROOT/'figures/v3/v3c_candidate_scores.png'


def load_inputs(cand_csv=CAND_CSV, conf_csv=CONF_CSV):
    return pd.read_csv(cand_csv, dtype={'obs_id': str}), pd.read_csv(conf_csv, dtype={'obs_id': str})


def source_means(cand_pred, conf_oof):
    """Arithmetic mean BH_score over all observations of each source, per model (H_colours, LogReg/RandomForest)."""
    def sel(d):
        return d[(d.representation == REP) & d.model.isin(PLOT_MODELS)]
    c, f = sel(cand_pred), sel(conf_oof)
    cand = c.groupby(['source_id', 'model']).BH_score.mean().unstack()[list(PLOT_MODELS)]
    conf = f.groupby(['source_id', 'model']).BH_score.mean().unstack()[list(PLOT_MODELS)]
    labels = f.groupby('source_id').true_label.agg(lambda t: t.iloc[0] if t.nunique() == 1 else None)
    assert cand.notna().all().all() and conf.notna().all().all(), 'a source is missing a model'
    assert labels.isin(['BH', 'NS']).all(), 'confirmed source without a single BH/NS label'
    assert not set(cand.index) & set(conf.index), 'candidate and confirmed sources overlap'
    return cand, conf, labels


def row_layout(cand, conf):
    """Top-to-bottom rows: header, confirmed block, separator, header, candidate block. Returns (rows, y, sep, headers)."""
    def order(m):
        return m.reset_index().sort_values([SORT_MODEL, 'source_id'], ascending=[False, True]).source_id.tolist()
    oc, ok = order(conf), order(cand)
    y = {s: 1 + i for i, s in enumerate(oc)}                       # row 0 = confirmed header
    sep = len(oc) + 1
    y.update({s: sep + 2 + i for i, s in enumerate(ok)})            # row sep + 1 = candidate header
    return oc + ok, y, sep, {0: f'confirmed sources ({len(oc)}): v2 LOSO out-of-fold',
                             sep + 1: f'BH candidates ({len(ok)}): models trained on all {len(oc)} confirmed'}


def plot_candidate_scores(cand_pred, conf_oof, out=OUT_PNG):
    """Draw and save the figure; returns the open Figure (caller closes it)."""
    cand, conf, labels = source_means(cand_pred, conf_oof)
    rows, y, sep, headers = row_layout(cand, conf)
    colour = {s: CLASS_COLOR[labels[s]] if s in conf.index else CAND_COLOR for s in rows}
    ymax = max(y.values())
    fig, axes = plt.subplots(1, 2, figsize=(10, 0.2 * ymax + 2.6), sharey=True, layout='constrained')
    axes[0].set_yticks([y[s] for s in rows], labels=rows)                  # shared y axis: ticks and labels set once
    axes[0].set_ylim(ymax + .7, -.7)                                       # shared y axis: inverted once (row 0 on top)
    axes[1].tick_params(axis='y', labelleft=False, labelright=True)        # names on both outer edges
    for a in axes: a.tick_params(axis='y', labelsize=7.5)
    for a, m in zip(axes, PLOT_MODELS):
        score = pd.concat([conf[m], cand[m]])                              # this model's source means, by source_id
        a.scatter([score[s] for s in rows], [y[s] for s in rows], c=[colour[s] for s in rows], s=24, lw=0, zorder=3)
        a.axvline(.5, color=INK2, ls='--', lw=.8); a.axhline(sep, color=INK2, lw=.8)
        tr = blended_transform_factory(a.transAxes, a.transData)
        for yy, txt in headers.items():
            a.text(.01, yy, txt, transform=tr, va='center', ha='left', fontsize=7.5, color=INK2, style='italic')
        a.set_xlim(-.02, 1.02); a.grid(axis='y', lw=.4)
        a.set_xlabel('source-mean BH score (H colours)\nnot a calibrated probability; dashed line = 0.5')
        a.set_title(m + (' (rows sorted by this score)' if m == SORT_MODEL else ''), loc='left')
    handles = [Line2D([], [], ls='', marker='o', ms=6, mec='none', color=col, label=t) for col, t in
               [(CAND_COLOR, 'grey: BH candidate (predicted, unlabelled)'),
                (CLASS_COLOR['BH'], 'blue: confirmed BH (v2 LOSO)'), (CLASS_COLOR['NS'], 'orange: confirmed NS (v2 LOSO)')]]
    fig.legend(handles=handles, loc='outside lower center', ncol=3, fontsize=8.5, handletextpad=.3, columnspacing=1.5)
    fig.suptitle('v3c: source-mean BH score per source, H colours; each row is the same source in both panels',
                 x=.01, ha='left')
    fig.savefig(out)
    return fig
