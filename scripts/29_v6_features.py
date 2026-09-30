"""v6 step 2 (preregistration_v6.md §3): all-pairs / hybrid timing features T1*-T3*, T*_total, nu_c for every observation of
S1 (v2), v4b2, v4b1 and v6; v5 timing features (v5 estimator) for the new v6 observations; split-half reliability
(odd vs even rows) of T* vs the v5 A/B estimator on S1. Outputs data/v6/processed/timing_v6.csv,
data/v6/processed/timing_v5_new.csv, results/v6/v6_estimator_reliability.csv."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v6'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
import v5lib as L5, v6lib as L6

D6, R6 = ROOT/'data/v6/processed', ROOT/'results/v6'
for p in (D6, R6): p.mkdir(parents=True, exist_ok=True)
T0 = time.time()


def obs_table(v):
    o = pd.read_csv(ROOT/f'data/{v}/observations.csv', dtype={'obs_id': str}, low_memory=False)
    return o[o.in_dataset.astype(str).str.lower().eq('true')][['obs_id', 'source_id', 'label', 'path_src', 'path_bkg']]


tabs = {v: obs_table(v) for v in ('v2', 'v4b2', 'v4b1', 'v6')}
allo = pd.concat([t.assign(sample=v) for v, t in tabs.items()]).drop_duplicates('obs_id').reset_index(drop=True)
print(len(allo), 'unique observations', {v: len(t) for v, t in tabs.items()}, flush=True)
recs = Parallel(n_jobs=16, batch_size=8)(delayed(L6.obs_timing_v6)(r.obs_id, r.path_src, r.path_bkg) for r in allo.itertuples())
tf = allo[['obs_id', 'source_id', 'label']].merge(pd.DataFrame(recs), on='obs_id')
for v, t in tabs.items(): tf[f'in_{v}'] = tf.obs_id.isin(t.obs_id)
tf.to_csv(D6/'timing_v6.csv', index=False)
print(f'T* done ({time.time()-T0:.0f} s)'); print(tf.status.str.slice(0, 40).value_counts().to_string())
print('rows: pairs', int(tf.n_rows_pairs.sum()), 'single', int(tf.n_rows_single.sum()))

# v5 estimator on the new v6 observations (needed for the frozen v5-type models on E_new)
new = tabs['v6']
r5 = Parallel(n_jobs=16, batch_size=8)(delayed(L5.obs_timing)(r.obs_id, r.path_src, r.path_bkg) for r in new.itertuples())
t5 = new[['obs_id', 'source_id', 'label']].merge(pd.DataFrame(r5), on='obs_id'); t5.to_csv(D6/'timing_v5_new.csv', index=False)
print('v5 estimator on v6 obs:', t5.status.str.slice(0, 30).value_counts().to_dict())

# split-half reliability on S1 (observations where both estimators have both halves)
s1 = tf[tf.in_v2 & tf.status.eq('ok')]
rows = []
for k in L5.BANDS:
    m = s1[[f'{k}s_odd', f'{k}s_even', f'{k}_v5_odd', f'{k}_v5_even']].dropna()
    rows.append(dict(band=k, n=len(m), spearman_allpairs=spearmanr(m[f'{k}s_odd'], m[f'{k}s_even'])[0],
                     spearman_v5_AB=spearmanr(m[f'{k}_v5_odd'], m[f'{k}_v5_even'])[0],
                     mad_halfdiff_allpairs=float(np.median(np.abs(m[f'{k}s_odd'] - m[f'{k}s_even']))),
                     mad_halfdiff_v5_AB=float(np.median(np.abs(m[f'{k}_v5_odd'] - m[f'{k}_v5_even'])))))
rel = pd.DataFrame(rows); rel.to_csv(R6/'v6_estimator_reliability.csv', index=False)
print('\nsplit-half reliability (S1):\n' + rel.round(4).to_string(index=False))
t5v = pd.read_csv(ROOT/'data/v5/processed/timing_features.csv', dtype={'obs_id': str})
mm = tf.merge(t5v[['obs_id', 'T1', 'T2', 'T3', 'status']], on='obs_id', suffixes=('', '_v5'))
mm = mm[mm.status.eq('ok') & mm.status_v5.eq('ok')]
print('\nagreement T* vs v5 T (obs with both):', {k: round(spearmanr(mm[f'{k}s'], mm[k])[0], 4) for k in L5.BANDS}, 'n =', len(mm))
print('missing: v5', int((~t5v.status.eq('ok')).sum()), 'of', len(t5v), '| v6 T*', int((~tf.status.eq('ok')).sum()), 'of', len(tf))
print('nu_c available:', int(tf.nu_c.notna().sum()))
progress('v6_features', f"{int(tf.status.eq('ok').sum())}/{len(tf)} obs with T*; reliability "
         + ', '.join(f"{r.band} {r.spearman_allpairs:.3f} vs {r.spearman_v5_AB:.3f}" for r in rel.itertuples()))
print(f'total {time.time()-T0:.0f} s')
