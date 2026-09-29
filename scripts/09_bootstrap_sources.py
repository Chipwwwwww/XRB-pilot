"""Source-level (cluster) bootstrap of LOSO metrics. Resamples OBJECTS with replacement within each class;
all observations of a drawn object come along. Uses the fixed out-of-fold predictions (no retraining),
so intervals describe variability from WHICH objects are in the sample, not from model refitting."""
from common import *
from config import *
from plotstyle import *
import numpy as np, pandas as pd

N_BOOT = getattr(__import__('config'), 'N_BOOT', 2000)
oof = pd.read_csv(R/'oof_predictions_loso.csv', dtype={'obs_id': str})
oof['correct'] = oof.true_label == oof.predicted_label
ps = pd.read_csv(R/'per_source_results.csv')
rng = np.random.default_rng(SEED)
srcs = ps[['source_id', 'true_label']].drop_duplicates()
bh = srcs[srcs.true_label == 'BH'].source_id.values; ns = srcs[srcs.true_label == 'NS'].source_id.values
draws = [np.r_[rng.choice(bh, len(bh)), rng.choice(ns, len(ns))] for _ in range(N_BOOT)]


def metrics(p_src, o_by_src, sample):
    t = p_src.loc[sample]
    src_bacc = 0.5 * (t[t.true_label == 'BH'].source_correct.mean() + t[t.true_label == 'NS'].source_correct.mean())
    per_src_bal = 0.5 * (t[t.true_label == 'BH'].obs_accuracy.mean() + t[t.true_label == 'NS'].obs_accuracy.mean())
    o = pd.concat([o_by_src[s] for s in sample])
    rec = o.groupby('true_label').correct.mean()
    return src_bacc, per_src_bal, 0.5 * (rec.get('BH', np.nan) + rec.get('NS', np.nan))


names = ['source_balanced_accuracy', 'per_source_accuracy_class_balanced', 'observation_balanced_accuracy']
rows, boot = [], {}
for (rep, m), t in ps.groupby(['representation', 'model']):
    if m == 'Dummy': continue
    p_src = t.set_index('source_id')
    o = oof[(oof.representation == rep) & (oof.model == m)]
    o_by_src = {s: g for s, g in o.groupby('source_id')}
    point = metrics(p_src, o_by_src, p_src.index.values)
    B = np.array([metrics(p_src, o_by_src, d) for d in draws])
    boot[(rep, m)] = B
    for k, n in enumerate(names):
        rows.append(dict(representation=rep, model=m, metric=n, point=point[k],
                         ci2_5=np.nanpercentile(B[:, k], 2.5), ci97_5=np.nanpercentile(B[:, k], 97.5)))
PAIRS = [('B_shape', 'A_intensity'), ('B_shape', 'H_colours'), ('A_intensity', 'HI_colours_intensity')]
for m in ['LogReg', 'RandomForest']:
    for r1, r2 in PAIRS:
        if (r1, m) not in boot or (r2, m) not in boot: continue
        dB = boot[(r1, m)] - boot[(r2, m)]
        for k, n in enumerate(names):
            pt = [x for x in rows if x['representation'] == r1 and x['model'] == m and x['metric'] == n][0]['point'] - \
                 [x for x in rows if x['representation'] == r2 and x['model'] == m and x['metric'] == n][0]['point']
            rows.append(dict(representation=f'{r1}_minus_{r2}', model=m, metric=n, point=pt,
                             ci2_5=np.nanpercentile(dB[:, k], 2.5), ci97_5=np.nanpercentile(dB[:, k], 97.5),
                             frac_first_better=float(np.mean(dB[:, k] > 0))))
out = pd.DataFrame(rows)
out.to_csv(R/'bootstrap_source_level.csv', index=False)
pd.set_option('display.width', 200)
print(f'{N_BOOT} source-level bootstrap replicates; {len(bh)} BH + {len(ns)} NS objects')
print(out.round(3).to_string(index=False))
progress(f'bootstrap_{VERSION}', 'results bootstrap_source_level.csv written')
