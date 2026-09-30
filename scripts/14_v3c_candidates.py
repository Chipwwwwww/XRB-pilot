"""v3c step 3 (local; preregistration_v3.md §3). Needs data/v3c/processed/features.npz from
`XRB_VERSION=v3c python scripts/03_select_observations.py` and `... 04_fetch_process.py`.
Analysis 1: train on all 31 confirmed v2 sources, PREDICT candidates (no accuracy is computed).
Analysis 2: LOSO over the 31 confirmed sources only; candidates (labelled BH) are always added to training.
            Paired with the v2 OOF predictions (same test observations/folds)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, progress
from v3lib import *
from plotstyle import plt, INK2, CLASS_COLOR

R3, FG3 = ROOT/'results/v3', ROOT/'figures/v3'
for p in (R3, FG3): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 220)
zc2 = np.load(ROOT/'data/v2/processed/features.npz'); zc3 = np.load(ROOT/'data/v3c/processed/features.npz')
assert np.allclose(zc2['edges'], zc3['edges']), 'candidate grid differs from v2 grid'
assert not set(zc2['source_id']) & set(zc3['source_id']) and not set(zc2['obs_id']) & set(zc3['obs_id'])
conf = v2_representations(zc2['rate'], zc2['edges'], zc2['F'])
cand = v2_representations(zc3['rate'], zc3['edges'], zc3['F'])
y, g, oid = zc2['y'], zc2['source_id'], zc2['obs_id']; gc, oc = zc3['source_id'], zc3['obs_id']
print(f'confirmed: {len(y)} obs / {len(set(g))} sources; candidates: {len(oc)} obs / {len(set(gc))} sources')

# ---- analysis 1: prediction only ----
pred = []
for rep in conf:
    for m, mk in MODELS.items():
        mod = mk().fit(conf[rep], y); p = mod.predict_proba(cand[rep])[:, list(mod.classes_).index(1)]
        pred += [dict(representation=rep, model=m, source_id=s, obs_id=o, BH_score=float(v)) for s, o, v in zip(gc, oc, p)]
pred = pd.DataFrame(pred); pred.to_csv(R3/'v3c_candidate_predictions.csv', index=False)
summ = pred.groupby(['source_id', 'representation', 'model']).BH_score.agg(['size', 'mean', 'median']).unstack([1, 2])
summ.to_csv(R3/'v3c_candidate_source_summary.csv')
print('\nCandidate source-mean BH scores (prediction, NOT an accuracy; candidates have no verified label):')
print(pred.groupby(['source_id', 'representation', 'model']).BH_score.mean().unstack([1, 2]).round(2).to_string())

# ---- analysis 2: label-sensitivity, test only on confirmed sources ----
folds = list(LeaveOneGroupOut().split(np.zeros(len(y)), y, g))
rows = []
for rep in conf:
    Xa = np.r_[conf[rep], cand[rep]]; ya = np.r_[y, np.ones(len(oc), int)]
    for m, mk in MODELS.items():
        for k, (tr, te) in enumerate(folds):
            tra = np.r_[tr, len(y) + np.arange(len(oc))]              # + every candidate observation
            mod = mk().fit(Xa[tra], ya[tra]); p = mod.predict_proba(Xa[te])[:, list(mod.classes_).index(1)]
            rows += [dict(representation=rep + '+cand', model=m, fold=k, source_id=g[i], obs_id=oid[i],
                          true_label='BH' if y[i] else 'NS', BH_score=float(s),
                          predicted_label='BH' if s >= SOURCE_THRESHOLD else 'NS') for i, s in zip(te, p)]
        print(f'  {rep}+cand {m} done', flush=True)
oofc = pd.DataFrame(rows); oofc.to_csv(R3/'v3c_oof_with_candidates.csv', index=False)
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str}); v2 = v2[v2.model != 'Dummy']
both = pd.concat([v2, oofc], ignore_index=True)
pm, ps = point_metrics(both); pm.to_csv(R3/'v3c_metrics.csv', index=False); ps.to_csv(R3/'v3c_per_source.csv', index=False)
print('\n' + pm.drop(columns='misclassified_sources').round(3).to_string(index=False))
bs = bootstrap(both, [(r + '+cand', r) for r in conf]); bs.to_csv(R3/'v3c_bootstrap.csv', index=False)
print('\n' + bs[bs.comparison.str.contains(' - ')].round(3).to_string(index=False))

# ---- figure: candidate source-mean scores next to confirmed LOSO source means (H colours, both models) ----
fig, axes = plt.subplots(1, 2, figsize=(11, 0.25 * (len(set(gc)) + 31) + 1.5), sharey=True)
for a, m in zip(axes, MODELS):
    c = pred[(pred.representation == 'H_colours') & (pred.model == m)].groupby('source_id').BH_score.mean()
    f = ps[(ps.representation == 'H_colours') & (ps.model == m)].set_index('source_id').mean_BH_score
    lab = ps[(ps.representation == 'H_colours') & (ps.model == m)].set_index('source_id').true_label
    order = list(c.sort_values().index) + list(f.sort_values().index)
    for i, s in enumerate(order):
        v, col = (c[s], '#9e9d98') if s in c.index else (f[s], CLASS_COLOR[lab[s]])
        a.plot(v, i, 'o', color=col, ms=5)
    a.axvline(.5, color=INK2, ls='--', lw=.8); a.axhline(len(c) - .5, color=INK2, lw=.6)
    a.set_yticks(range(len(order))); a.set_yticklabels(order, fontsize=6.5); a.set_xlim(-.02, 1.02)
    a.set_xlabel('source-mean BH score (H colours; not a calibrated probability)'); a.set_title(m, loc='left')
fig.suptitle('v3c: grey = BH candidates (predicted, unlabelled); blue/orange = confirmed BH/NS (LOSO, v2)', x=.01, ha='left')
fig.savefig(FG3/'v3c_candidate_scores.png'); plt.close(fig)
progress('v3c_candidates', 'results/v3/v3c_* written')
