"""Unit tests for v7lib: weighted AUC / balanced accuracy vs scikit-learn, bootstrap draws identical to v4lib,
burst-GTI overlap, MET <-> UTC round trip on a real v2 spectrum."""
import os, sys
os.environ['XRB_VERSION'] = 'v7a'
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, balanced_accuracy_score
from common import ROOT
import v7lib as L7

rng = np.random.default_rng(1)
fails = 0


def check(name, ok, info=''):
    global fails
    print(('PASS ' if ok else 'FAIL ') + name, info); fails += (not ok)


y = rng.integers(0, 2, 300); s = np.round(rng.uniform(0, 1, 300), 2); w = rng.integers(1, 4, 300)
a, b = L7.auc_ba(y, s)
check('auc_ba AUC == sklearn (ties)', abs(a - roc_auc_score(y, s)) < 1e-12, (a, roc_auc_score(y, s)))
check('auc_ba BA == sklearn', abs(b - balanced_accuracy_score(y, s >= .5)) < 1e-12)
a, b = L7.auc_ba(y, s, w)
check('auc_ba weighted AUC == sklearn sample_weight', abs(a - roc_auc_score(y, s, sample_weight=w)) < 1e-12)
check('auc_ba weighted BA == sklearn sample_weight', abs(b - balanced_accuracy_score(y, s >= .5, sample_weight=w)) < 1e-12)
check('auc_ba single class -> NaN', np.isnan(L7.auc_ba(np.ones(5), s[:5])[0]))
# draws identical to v4lib.paired_bootstrap (sorted names, default_rng(42))
lab = {f'B{i}': 'BH' for i in range(7)} | {f'N{i:02d}': 'NS' for i in range(24)}
d = L7.boot_draws(lab, n_boot=3)
r = np.random.default_rng(42); bh = np.sort([k for k in lab if lab[k] == 'BH']); ns = np.sort([k for k in lab if lab[k] == 'NS'])
ref = [np.r_[r.choice(bh, 7), r.choice(ns, 24)] for _ in range(3)]
check('boot_draws == v4lib draws', all((x == y_).all() for x, y_ in zip(d, ref)))
# burst overlap
bb = pd.DataFrame(dict(t0=[1.0, 2.0, 5.0], t1=[1.5, 3.0, 6.0]))
check('bursts_in_gti overlap', list(L7.bursts_in_gti(bb, np.array([[1.4, 2.1]]))) == [0, 1])
# MET <-> UTC round trip on a real spectrum
o = pd.read_csv(ROOT/'data/v2/observations.csv', dtype={'obs_id': str}, low_memory=False)
o = o[o.in_dataset.astype(str).str.lower().eq('true')].iloc[0]
utc, gti, mjdref, s_ = L7.gti_utc(o.path_src)
back = L7.utc_to_met(utc.ravel(), mjdref).reshape(gti.shape)
check('MET -> UTC -> MET round trip < 1 ms', np.abs(back - gti).max() < 1e-3, np.abs(back - gti).max())
check('TT - UTC offset ~ 64-66 s', 60 < (mjdref + gti[0, 0] / 86400 - utc[0, 0]) * 86400 < 70, (mjdref + gti[0, 0] / 86400 - utc[0, 0]) * 86400)
print('\nALL PASS' if fails == 0 else f'\n{fails} FAILED'); sys.exit(1 if fails else 0)
