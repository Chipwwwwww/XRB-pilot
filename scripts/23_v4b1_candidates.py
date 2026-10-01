"""v4b1 step 1 (preregistration_v4.md §4, 3c): every eligible epoch-5 pointing of the 31 v2 sources.
Uses the v2 eligible list (data/v2/observation_candidates.csv = all eligible pointings, same rules) and gives each
pointing its own time_bin so 24_v4b1_fetch_process.py processes every one of them once."""
import os, sys, shutil
os.environ['XRB_VERSION'] = 'v4b1'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, D, progress
import pandas as pd
c = pd.read_csv(ROOT/'data/v2/observation_candidates.csv', dtype={'obs_id': str}).sort_values(['source_id', 'mjd']).reset_index(drop=True)
c['time_bin'] = c.groupby('source_id').cumcount(); c['rank_in_bin'] = 0
c.to_csv(D/'observation_candidates.csv', index=False)
s = pd.read_csv(ROOT/'data/v2/sources.csv'); s = s[s.included.astype(bool)]
s.to_csv(D/'sources.csv', index=False)
print(len(c), 'eligible pointings;', c.groupby('label').size().to_dict(), ';', c.source_id.nunique(), 'sources')
progress('v4b1_candidates', f'{len(c)} eligible epoch-5 pointings of {c.source_id.nunique()} v2 sources')
