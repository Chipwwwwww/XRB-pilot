"""v10b input (preregistration_v10.md sec. 5): RXTE observations of S1 (v2, v7a states) and of the external set X (v8b states;
slow-pulsar stress sources kept but flagged) with H_R colours (power-law-normalised, all gain epochs) and the v6 Standard-1
nu_c (data/v6/processed/timing_v6.csv; missing v7b2 / v8b observations computed with v6lib.obs_timing_v6).
Output data/v10/processed/rxte_timing_table.csv."""
import os, sys
os.environ['XRB_VERSION'] = 'v10'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
import v6lib as L6

D10 = ROOT/'data/v10/processed'; D10.mkdir(parents=True, exist_ok=True)


def reps_R(z):                                   # identical to 30_v6_analysis.reps_R
    W = np.diff(z['edges']); ec = np.sqrt(z['edges'][:-1] * z['edges'][1:])
    band = lambda a, lo, hi: np.sum((a * W)[:, (ec >= lo) & (ec < hi)], 1)
    c = {k: band(z['rate'], *b) / band(z['pl2'], *b) for k, b in {'b1': (5, 7), 'b2': (7, 10), 'b3': (10, 16), 'b4': (16, 25.1)}.items()}
    return np.c_[c['b2'] / c['b1'], c['b4'] / c['b3']]


rows = []
for v in ('v2', 'v4b2', 'v6', 'v7b2', 'v8b'):
    z = np.load(ROOT/f'data/{v}/processed/features.npz'); hr = reps_R(z)
    for o, s, y, (a, b) in zip(z['obs_id'], z['source_id'], z['y'], hr):
        rows.append(dict(obs_id=str(o), source_id=str(s), label='BH' if y == 1 else 'NS', sample_dir=v, c1R=a, c2R=b))
T = pd.DataFrame(rows).drop_duplicates('obs_id')
st = pd.read_csv(ROOT/'results/v7a/states.csv', dtype={'obs_id': str})[['obs_id', 'state']].assign(sample='S1', role='S1')
X = pd.read_csv(ROOT/'data/v8b/processed/external_states_timing.csv', dtype={'obs_id': str})[['obs_id', 'state', 'role']].assign(sample='X')
T = T.merge(pd.concat([st, X]), on='obs_id', how='inner')
T6 = pd.read_csv(ROOT/'data/v6/processed/timing_v6.csv', dtype={'obs_id': str}).drop_duplicates('obs_id').set_index('obs_id')
T = T.join(T6[['nu_c', 'T1s', 'T2s', 'T3s', 'Ts_total']], on='obs_id')
miss = T[~T.obs_id.isin(T6.index)]
paths = pd.concat([pd.read_csv(ROOT/f'data/{v}/observations.csv', dtype={'obs_id': str}, low_memory=False)[['obs_id', 'path_src', 'path_bkg']]
                   for v in ('v7b2', 'v8b')]).drop_duplicates('obs_id').set_index('obs_id')
print(len(T), 'RXTE observations;', len(miss), 'need the v6 nu_c computed', flush=True)
rec = Parallel(n_jobs=8)(delayed(L6.obs_timing_v6)(o, paths.loc[o].path_src, paths.loc[o].path_bkg) for o in miss.obs_id)
new = pd.DataFrame(rec).set_index('obs_id')
for k in ('nu_c', 'T1s', 'T2s', 'T3s', 'Ts_total'):
    T.loc[T.obs_id.isin(new.index), k] = T.loc[T.obs_id.isin(new.index), 'obs_id'].map(new[k]).values
T['nu_c_source'] = np.where(T.obs_id.isin(new.index), 'v6lib.obs_timing_v6 (v10)', 'timing_v6.csv')
T.to_csv(D10/'rxte_timing_table.csv', index=False)
h = T[(T.state == 'hard-like') & (T.role != 'stress_slow_pulsar')]
print(h.groupby(['sample', 'label']).agg(n=('obs_id', 'size'), src=('source_id', 'nunique'), nu_c_ok=('nu_c', lambda s: int(s.notna().sum()))).to_string())
progress('v10_rxte_nuc', f'{len(T)} RXTE obs; hard-like non-stress {len(h)} ({int(h.nu_c.notna().sum())} with nu_c)')
