"""Smoke / unit tests for v4lib (run before any full v4 computation). Uses only committed v2/v3 outputs."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v4'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT
import numpy as np, pandas as pd
import v4lib as L
from sklearn.model_selection import LeaveOneGroupOut

ok = True
def check(name, cond, info=''):
    global ok; ok &= bool(cond); print(('PASS ' if cond else 'FAIL ') + name, info, flush=True)

# 1. threshold chooser
t, ba = L.choose_threshold(np.array([0.1, 0.2, 0.6, 0.7]), np.array([0, 0, 1, 1]))
check('choose_threshold separable -> 0.4, BA 1', abs(t - 0.4) < 1e-12 and ba == 1.0, (t, ba))
t, ba = L.choose_threshold(np.array([0.1, 0.3, 0.9]), np.array([0, 1, 1]))
check('choose_threshold tie -> closest to 0.5', abs(t - 0.2) < 1e-12, (t, ba))

# 2. source-equal weights
w = L.source_equal_weights(np.array([1, 1, 1, 0, 0]), np.array(['a', 'a', 'b', 'c', 'd']))
check('source_equal_weights class sums = n/2', np.isclose(w[:3].sum(), 2.5) and np.isclose(w[3:].sum(), 2.5) and np.isclose(w[0], .625), w)
yy, gg = np.repeat([1, 1, 0, 0, 0], 4), np.repeat(list('abcde'), 4)          # equal obs per source -> identical to balanced
check('source_equal_weights == balanced_weights when every source has the same n', np.allclose(L.source_equal_weights(yy, gg), L.balanced_weights(yy)))

# 3. paired bootstrap reproduces v3a numbers exactly (same draws as v3lib/09)
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
ref = v2[(v2.representation == 'H_colours') & (v2.model == 'LogReg')]
bsh = v2[(v2.representation == 'B_shape') & (v2.model == 'LogReg')]
bs = L.paired_bootstrap({'H-LR': ref, 'B-LR': bsh}, 'H-LR')
v3 = pd.read_csv(ROOT/'results/v3/v3a_bootstrap.csv')
def v3val(comp, metric, col): return v3[(v3.comparison == comp) & (v3.model == 'LogReg') & (v3.metric == metric)][col].iloc[0]
for m4, m3 in [('source_balanced_accuracy', 'source_balanced_accuracy'), ('source_AUC', 'source_AUC'), ('obs_balanced_accuracy', 'obs_balanced_accuracy')]:
    r = bs[(bs.comparison == 'B-LR - H-LR') & (bs.metric == m4)].iloc[0]
    check(f'bootstrap diff {m4} == v3a', np.allclose([r.point, r.ci2_5, r.ci97_5],
          [v3val('B_shape - H_colours', m3, c) for c in ('point', 'ci2_5', 'ci97_5')], atol=1e-12), (r.point, r.ci2_5, r.ci97_5))
    r = bs[(bs.comparison == 'H-LR') & (bs.metric == m4)].iloc[0]
    check(f'bootstrap H-LR {m4} == v3a', np.allclose([r.point, r.ci2_5, r.ci97_5],
          [v3val('H_colours', m3, c) for c in ('point', 'ci2_5', 'ci97_5')], atol=1e-12))

# 4. V4Model reproduces v2 LR and RF OOF on H (and LR on B)
z = np.load(ROOT/'data/v2/processed/features.npz')
y, g, oid = z['y'], z['source_id'], z['obs_id']
reps = L.v2_representations(z['rate'], z['edges'], z['F'])
folds = list(LeaveOneGroupOut().split(np.zeros(len(y)), y, g))
for rep, alg, v2m, tol in [('H_colours', 'LogReg', 'LogReg', 1e-8), ('B_shape', 'LogReg', 'LogReg', 1e-8), ('H_colours', 'RandomForest', 'RandomForest', 0.01)]:
    s = L.loso_scores(reps[rep], y, g, folds, alg)
    o = v2[(v2.representation == rep) & (v2.model == v2m)].set_index('obs_id').loc[oid]
    check(f'reproduce v2 {rep}/{alg}', np.max(np.abs(s - o.BH_score.values)) <= tol, np.max(np.abs(s - o.BH_score.values)))

# 5. every algorithm fits/scores on every representation (one fold), scores finite in [0,1]
tr, te = folds[0]
for rep in L.REPS:
    for alg in L.ALGS:
        sc = L.V4Model(alg, {}, 'fixed').fit(reps[rep][tr], y[tr]).score(reps[rep][te])
        check(f'{alg}/{rep} scores finite', np.isfinite(sc).all() and (sc >= 0).all() and (sc <= 1).all())
    for alg in ['LogReg', 'RandomForest', 'HistGB']:
        sc = L.V4Model(alg).fit(reps[rep][tr], y[tr], L.source_equal_weights(y[tr], g[tr])).score(reps[rep][te])
        check(f'{alg}[srcw]/{rep} scores finite', np.isfinite(sc).all())

# 6. timed nested fold with the FULL grid on one outer fold (timing for the estimate); results not inspected
t0 = time.perf_counter()
rows, preds = L.nested_fold(0, tr, te, reps, y, g)
dt = time.perf_counter() - t0
check('nested_fold returns 140 inner rows and 32 selections', len(rows) == 140 and len(preds) == 32, f'{dt:.0f} s for one outer fold')
print('ALL PASS' if ok else 'SOME TESTS FAILED')
