"""v7b1 step 2 (preregistration_v7.md §3, 1d sensitivity): replace each MINBAR-contaminated v2 observation by the next
eligible candidate of the SAME time bin (v2 candidate ranking), processed with the unchanged 04_fetch_process.py
(XRB_VERSION=v7b1 -> data/v7b1) and required to be MINBAR-clean; up to 3 rounds. Bins without a clean replacement
stay empty. Outputs data/v7b1/replacements.csv, data/v7b1/processed/features_replaced.npz (v2 sample with replacements)."""
import os, sys, subprocess, shutil
os.environ['XRB_VERSION'] = 'v7b1'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress, D
import numpy as np, pandas as pd
import v7lib as L7

PY = sys.executable
c2 = pd.read_csv(ROOT/'data/v2/observation_candidates.csv', dtype={'obs_id': str})
o2 = pd.read_csv(ROOT/'data/v2/observations.csv', dtype={'obs_id': str}, low_memory=False)
fl = pd.read_csv(ROOT/'results/v7b1/minbar_flags.csv', dtype={'obs_id': str})
src = pd.read_csv(ROOT/'data/v2/sources.csv'); src.to_csv(D/'sources.csv', index=False); sp = src.set_index('source_id')
bursts, msrc = L7.load_minbar(), L7.load_minbar_sources()
acc = o2[o2.in_dataset.astype(str).str.lower().eq('true')]
cont = acc[acc.obs_id.isin(fl[fl.contaminated_minbar].obs_id)][['obs_id', 'source_id', 'time_bin', 'rank_in_bin']]
tried = {k: set(v) for k, v in o2.groupby(['source_id', 'time_bin']).obs_id}
state = {(r.source_id, r.time_bin): dict(replaced_obs=r.obs_id, accepted_rank=r.rank_in_bin, replacement=None, status='open', log=[])
         for r in cont.itertuples()}
feats = {}
for rnd in range(1, 4):
    rows = []
    for (s, b), st in state.items():
        if st['status'] != 'open': continue
        cb = c2[(c2.source_id == s) & (c2.time_bin == b) & (c2.rank_in_bin > st['accepted_rank']) & ~c2.obs_id.isin(tried.get((s, b), set()))]
        if not len(cb): st['status'] = 'no_further_candidate'; continue
        rows.append(cb)
    if not rows: break
    cand = pd.concat(rows); cand.to_csv(D/'observation_candidates.csv', index=False)
    print(f'round {rnd}: {cand.groupby(["source_id", "time_bin"]).ngroups} bins, {len(cand)} candidates', flush=True)
    env = dict(os.environ, XRB_VERSION='v7b1')
    with open(ROOT/f'logs/v7b1/04_fetch_round{rnd}.log', 'w') as f:
        subprocess.run([PY, str(ROOT/'scripts/04_fetch_process.py')], cwd=ROOT/'scripts', env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
    ob = pd.read_csv(D/'observations.csv', dtype={'obs_id': str}, low_memory=False); ob.to_csv(D/f'observations_round{rnd}.csv', index=False)
    z = np.load(D/'processed/features.npz'); shutil.copy(D/'processed/features.npz', D/f'processed/features_round{rnd}.npz')
    zi = {o: i for i, o in enumerate(z['obs_id'])}
    for r in ob.itertuples():
        tried.setdefault((r.source_id, r.time_bin), set()).add(r.obs_id)
        st = state[(r.source_id, r.time_bin)]
        if str(r.in_dataset).lower() != 'true':
            st['log'].append(f'{r.obs_id}:quality:{r.reason}'); continue
        n_fov, n_any = L7.minbar_flag(r.path_src, r.obs_id, sp.loc[r.source_id].ra_deg, sp.loc[r.source_id].dec_deg, bursts, msrc)
        if n_fov:
            st['log'].append(f'{r.obs_id}:minbar_contaminated'); continue
        st.update(replacement=r.obs_id, status='replaced', rank=r.rank_in_bin, round=rnd, minbar_any=n_any)
        st['log'].append(f'{r.obs_id}:accepted')
        feats[r.obs_id] = {k: z[k][zi[r.obs_id]] for k in ('rate', 'err', 'srate', 'brate', 'pl2', 'F')}
        feats[r.obs_id]['obs_row'] = r._asdict()
rep =pd.DataFrame([dict(source_id=s, time_bin=b, replaced_obs=st['replaced_obs'], replacement=st['replacement'], status=st['status'],
                         rounds_log=' | '.join(st['log'])) for (s, b), st in state.items()])
for i, r in rep.iterrows():
    if r.status == 'open': rep.loc[i, 'status'] = 'no_clean_replacement_after_3_rounds'
rep.to_csv(D/'replacements.csv', index=False)
print(rep.status.value_counts().to_string()); print(rep.to_string(index=False))

# assemble the v2 sample with replacements (contaminated obs removed; clean replacements added)
z2 = np.load(ROOT/'data/v2/processed/features.npz')
keep = ~np.isin(z2['obs_id'], cont.obs_id.values)
new = [o for o in rep.replacement.dropna()]
lab = dict(zip(src.source_id, src.label))
out = {k: np.concatenate([z2[k][keep], np.array([feats[o][k] for o in new])]) if new else z2[k][keep] for k in ('rate', 'err', 'srate', 'brate', 'pl2', 'F')}
out['obs_id'] = np.concatenate([z2['obs_id'][keep], np.array(new, dtype=z2['obs_id'].dtype)])
out['source_id'] = np.concatenate([z2['source_id'][keep], np.array([feats[o]['obs_row']['source_id'] for o in new], dtype=z2['source_id'].dtype)])
out['y'] = np.concatenate([z2['y'][keep], np.array([int(lab[feats[o]['obs_row']['source_id']] == 'BH') for o in new], dtype=int)])
np.savez_compressed(D/'processed/features_replaced.npz', edges=z2['edges'], **out)
pd.DataFrame([feats[o]['obs_row'] for o in new]).to_csv(D/'replacement_observations.csv', index=False)
print(f'replaced sample: {len(out["y"])} observations ({keep.sum()} kept + {len(new)} replacements)')
progress('v7b1_replace', f"{len(new)} of {len(rep)} contaminated bins replaced; {(rep.status != 'replaced').sum()} without a clean replacement")
