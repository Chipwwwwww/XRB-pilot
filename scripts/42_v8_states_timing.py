"""v8b step 2 (preregistration_v8.md sec. 4): external set X = v6 E (v4b2 15 sources + v6 8 new; the 4 slow-pulsar stress
sources are kept but flagged) + LMC X-1 (v7b2) + the v8b new dynamical BHs. For every X observation: MINBAR burst intervals
(v7b1 field-of-view rule), v7a state (0.1-4 Hz all-pairs rms, v7lib.state_rms, frozen thresholds) and the v5 timing features
T1-T3 (existing v5/v6 tables for v4b2/v6 observations, v5lib.obs_timing for the new ones).
Output: data/v8b/processed/external_states_timing.csv."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v8b'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
import v5lib as L5, v7lib as L7, v8lib as L8

T0 = time.time()
OUT = ROOT/'data/v8b/processed'; OUT.mkdir(parents=True, exist_ok=True)


def obs_table(v):
    o = pd.read_csv(ROOT/f'data/{v}/observations.csv', dtype={'obs_id': str}, low_memory=False)
    return o[o.in_dataset.astype(str).str.lower().eq('true')][['obs_id', 'source_id', 'label', 'path_src', 'path_bkg', 'mjd']]


role6 = pd.read_csv(ROOT/'data/v6/sources.csv').set_index('source_id').role
parts = [obs_table('v4b2').assign(sample='v4b2', role='E_v4b2'),
         obs_table('v6').assign(sample='v6').pipe(lambda d: d.assign(role=d.source_id.map(role6))),
         obs_table('v7b2').query("source_id == 'LMCX1'").assign(sample='v7b2', role='v7b2_LMCX1'),
         obs_table('v8b').assign(sample='v8b', role='v8b_new')]
X = pd.concat(parts, ignore_index=True)
assert not X.obs_id.duplicated().any()
pos = pd.concat([pd.read_csv(ROOT/f'data/{v}/sources.csv')[['source_id', 'ra_deg', 'dec_deg']].assign(sample=v)
                 for v in ('v4b2', 'v6', 'v7b2', 'v8b')]).drop_duplicates(['source_id', 'sample']).set_index(['source_id', 'sample'])
print(X.groupby(['sample', 'role', 'label']).agg(n_obs=('obs_id', 'size'), n_src=('source_id', 'nunique')).to_string(), flush=True)

bursts, msrc = L7.load_minbar(), L7.load_minbar_sources()
iv = []
for r in X.itertuples():
    p = pos.loc[(r.source_id, r.sample)]
    iv.append(L8.minbar_intervals(r.path_src, r.obs_id, float(p.ra_deg), float(p.dec_deg), bursts, msrc))
X['n_minbar_bursts'] = [len(x) for x in iv]
print('MINBAR (FOV rule) bursts in GTI:', int(X.n_minbar_bursts.sum()), 'in', int((X.n_minbar_bursts > 0).sum()), 'observations', flush=True)

st = Parallel(n_jobs=16, batch_size=4)(delayed(L7.state_rms)(r.obs_id, r.path_src, r.path_bkg, b) for r, b in zip(X.itertuples(), iv))
X = X.merge(pd.DataFrame(st), on='obs_id')
# v5 timing features: existing tables for the v4b2 / v6 observations (exactly as used by the frozen v6 models)
T5 = pd.concat([pd.read_csv(ROOT/'data/v5/processed/timing_features.csv', dtype={'obs_id': str}),
                pd.read_csv(ROOT/'data/v6/processed/timing_v5_new.csv', dtype={'obs_id': str})]).drop_duplicates('obs_id').set_index('obs_id')
need = X[~X.obs_id.isin(T5.index)]
r5 = Parallel(n_jobs=16, batch_size=4)(delayed(L5.obs_timing)(r.obs_id, r.path_src, r.path_bkg) for r in need.itertuples())
T5n = pd.DataFrame(r5).set_index('obs_id')
T = pd.concat([T5[['T1', 'T2', 'T3', 'status']], T5n[['T1', 'T2', 'T3', 'status']]])
X = X.join(T.rename(columns={'status': 'timing_status'}), on='obs_id')
X['timing_source'] = np.where(X.obs_id.isin(T5.index), 'existing v5/v6 table', 'v5lib.obs_timing (v8b)')
X.to_csv(OUT/'external_states_timing.csv', index=False)
print('\nstates:\n' + X.groupby(['role', 'label', 'state']).size().unstack(fill_value=0).to_string())
print('\nBH sources, state counts:\n' + X[X.label == 'BH'].groupby(['source_id', 'state']).size().unstack(fill_value=0).to_string())
print('\ntiming status:', X.timing_status.fillna('none').str.slice(0, 25).value_counts().to_dict())
hard = X[(X.state == 'hard-like') & (X.role != 'stress_slow_pulsar')]
print(f"\nX hard-like (excluding stress set): {len(hard)} obs, BH sources {hard[hard.label == 'BH'].source_id.nunique()}, "
      f"NS sources {hard[hard.label == 'NS'].source_id.nunique()} ({time.time() - T0:.0f} s)")
progress('v8b_states_timing', f"X {len(X)} obs; hard-like {len(hard)} obs, BH src {hard[hard.label == 'BH'].source_id.nunique()}, "
         f"NS src {hard[hard.label == 'NS'].source_id.nunique()}")
