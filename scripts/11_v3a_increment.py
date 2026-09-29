"""v3a (preregistration_v3.md §1): does the full spectrum add information beyond two count-space colours?
Uses only data/v2/processed/features.npz and the v2 LOSO folds. Writes results/v3/, figures/v3/, logs via progress()."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, progress
from v3lib import *
from plotstyle import plt, INK, INK2, CLASS_COLOR

R3, FG3 = ROOT/'results/v3', ROOT/'figures/v3'
R3.mkdir(parents=True, exist_ok=True); FG3.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 220)

z = np.load(ROOT/'data/v2/processed/features.npz')
rate, F, y, g, oid, edges = z['rate'], z['F'], z['y'], z['source_id'], z['obs_id'], z['edges']
assert np.all(F > 0)
reps = v2_representations(rate, edges, F)
reps['H_plus_B'] = np.c_[reps['H_colours'], reps['B_shape']]
reps['HI_plus_A'] = np.c_[reps['HI_colours_intensity'], reps['A_intensity']]
print(f'{len(y)} observations, {len(set(g))} sources ({len(set(g[y==1]))} BH / {len(set(g[y==0]))} NS)')
for k, X in reps.items(): print(f'  {k:<22s} {X.shape[1]} features')

# v2 folds (verified identical to results/v2/folds_loso.csv)
fold_file = pd.read_csv(ROOT/'results/v2/folds_loso.csv', dtype={'obs_id': str})
OOF_FILE = R3/'v3a_oof_predictions.csv'
if OOF_FILE.exists() and '--retrain' not in sys.argv:          # resume: models are deterministic (seeded)
    oof = pd.read_csv(OOF_FILE, dtype={'obs_id': str})
    folds = list(LeaveOneGroupOut().split(rate, y, g)); print('re-using', OOF_FILE.name)
else:
    oof, folds = run_loso(reps, y, g, oid)
assert all((fold_file[fold_file.fold == k].obs_id.values == oid[te]).all() for k, (tr, te) in enumerate(folds))
oof.to_csv(R3/'v3a_oof_predictions.csv', index=False)

# ---- reproduction check against v2 ----
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
rep_rows = []
for (rep, m), d in oof[oof.representation.isin(['A_intensity', 'B_shape', 'H_colours', 'HI_colours_intensity'])].groupby(['representation', 'model']):
    o = v2[(v2.representation == rep) & (v2.model == m)].set_index('obs_id').loc[d.obs_id]
    diff = np.abs(o.BH_score.values - d.BH_score.values)
    rep_rows.append(dict(representation=rep, model=m, max_abs_score_diff=diff.max(),
                         n_label_changes=int((o.predicted_label.values != d.predicted_label.values).sum())))
repro = pd.DataFrame(rep_rows); repro.to_csv(R3/'v3a_reproduction_check.csv', index=False)
print('\nReproduction of v2 OOF predictions:\n' + repro.to_string(index=False))

# ---- metrics, bootstrap, agreement ----
pm, ps = point_metrics(oof)
pm.to_csv(R3/'v3a_metrics.csv', index=False); ps.to_csv(R3/'v3a_per_source.csv', index=False)
print('\nPoint metrics:\n' + pm.drop(columns='misclassified_sources').round(3).to_string(index=False))
PAIRS = [('H_plus_B', 'H_colours'), ('HI_plus_A', 'HI_colours_intensity'), ('B_shape', 'H_colours'),
         ('B_shape', 'A_intensity'), ('A_intensity', 'HI_colours_intensity')]
bs = bootstrap(oof, PAIRS)
bs.to_csv(R3/'v3a_bootstrap.csv', index=False)
print('\nBootstrap (2000 source resamples, fixed OOF):\n' + bs.round(3).to_string(index=False))
ag = pd.DataFrame(agreement(oof, 'B_shape', 'H_colours') + agreement(oof, 'H_plus_B', 'H_colours'))
ag.to_csv(R3/'v3a_agreement.csv', index=False)
print('\nDescriptive agreement:\n' + ag.round(3).to_string(index=False))

# ---- figure: source-mean BH score, H vs H+B, per model ----
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
for a, m in zip(axes, MODELS):
    p1 = ps[(ps.representation == 'H_colours') & (ps.model == m)].set_index('source_id')
    p2 = ps[(ps.representation == 'H_plus_B') & (ps.model == m)].set_index('source_id').loc[p1.index]
    for lab in ['NS', 'BH']:
        s = p1.true_label == lab
        a.scatter(p1.mean_BH_score[s], p2.mean_BH_score[s], s=28, color=CLASS_COLOR[lab], label=f'{lab} source', zorder=3)
    for sid in p1.index:
        if p1.loc[sid, 'true_label'] == 'BH' or abs(p1.loc[sid, 'mean_BH_score'] - p2.loc[sid, 'mean_BH_score']) > .15:
            a.annotate(sid, (p1.loc[sid, 'mean_BH_score'], p2.loc[sid, 'mean_BH_score']), fontsize=6.5, color=INK2,
                       xytext=(3, 3), textcoords='offset points')
    a.plot([0, 1], [0, 1], color=INK2, lw=.8); a.axhline(.5, color=INK2, ls='--', lw=.7); a.axvline(.5, color=INK2, ls='--', lw=.7)
    a.set_xlim(-.02, 1.02); a.set_ylim(-.02, 1.02)
    a.set_xlabel('source-mean BH score, H (2 colours)'); a.set_ylabel('source-mean BH score, H+B (2 colours + 45 shape bins)')
    a.set_title(m, loc='left')
axes[0].legend(loc='upper left')
fig.suptitle('v3a: adding the full 5–25 keV shape to two colours (LOSO, 31 sources; scores are not calibrated probabilities)',
             x=.01, ha='left')
fig.savefig(FG3/'v3a_H_vs_HplusB_source_scores.png'); plt.close(fig)
progress('v3a_increment', 'results/v3/v3a_* written; reproduction ' +
         json.dumps({f'{r.representation}/{r.model}': round(r.max_abs_score_diff, 4) for r in repro.itertuples()}))
