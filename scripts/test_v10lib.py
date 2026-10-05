"""Synthetic checks of the v10 pooled statistics: pooled_boot with one component equals v8lib.strat_boot; pooled_perm has a
roughly uniform p under the null (fraction p < 0.05 over 200 null data sets between 0.01 and 0.10) and detects a strong
effect shared by two instruments with overlapping sources (power >= 0.8 at a -1.5 sd BH shift)."""
import os, sys
os.environ.setdefault('XRB_VERSION', 'v10')
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import v7lib as L7, v8lib as L8, v10lib as L10

rng = np.random.default_rng(42); rows = []
# 1) pooled_boot == strat_boot for a single component
src = [f'B{i}' for i in range(6)] + [f'N{i}' for i in range(15)]; lab = {s: ('BH' if s[0] == 'B' else 'NS') for s in src}
recs = []
for s in src:
    for j in range(5):
        recs.append(dict(obs_id=f'{s}_{j}', source_id=s, true_label=lab[s], g=rng.choice(['hard-like', 'soft-like'])))
df = pd.DataFrame(recs); A = df.assign(BH_score=rng.uniform(size=len(df)) + 0.3 * (df.true_label == 'BH')); B = df.assign(BH_score=rng.uniform(size=len(df)))
gr = df.set_index('obs_id').g
P, Bm, pp, pb = L10.pooled_boot([dict(name='c', A=A, B=B, groups=gr, stratum='hard-like')], lab, n_boot=300)
dr = L7.boot_draws(lab, 300); sa = L8.strat_boot(A, gr, dr)['hard-like']; sb = L8.strat_boot(B, gr, dr)['hard-like']
rows.append(dict(test='pooled_boot(1 component) == strat_boot difference', passed=bool(np.isclose(pp, sa[0][0] - sb[0][0]) and np.allclose(pb, sa[1][:, 0] - sb[1][:, 0], equal_nan=True))))
# 2) pooled_perm null calibration and power (two instruments, partly overlapping sources)
srcs = [f'B{i}' for i in range(9)] + [f'N{i}' for i in range(40)]; labs = {s: ('BH' if s[0] == 'B' else 'NS') for s in srcs}
inst1 = srcs[:7] + srcs[9:35]; inst2 = srcs[2:9] + srcs[20:49]
ps = []
for k in range(200):
    r1 = pd.Series(rng.normal(size=len(inst1)), index=inst1); r2 = pd.Series(rng.normal(size=len(inst2)), index=inst2)
    ps.append(L10.pooled_perm({'a': r1, 'b': r2}, labs, n_perm=400, seed=k)['p'])
f = float(np.mean(np.array(ps) < 0.05))
rows.append(dict(test=f'pooled_perm null: fraction p < 0.05 over 200 data sets = {f:.3f} (0.01-0.10)', passed=bool(0.01 <= f <= 0.10)))
pw = []
for k in range(50):
    r1 = pd.Series([rng.normal(-1.5 if labs[s] == 'BH' else 0.0) for s in inst1], index=inst1)
    r2 = pd.Series([rng.normal(-1.5 if labs[s] == 'BH' else 0.0) for s in inst2], index=inst2)
    pw.append(L10.pooled_perm({'a': r1, 'b': r2}, labs, n_perm=400, seed=k)['p'])
pwr = float(np.mean(np.array(pw) < 0.05))
rows.append(dict(test=f'pooled_perm power (BH shift -1.5 sd, 50 data sets): fraction p < 0.05 = {pwr:.2f} (>= 0.80)', passed=bool(pwr >= 0.80)))
res = pd.DataFrame(rows); print(res.to_string(index=False))
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'logs', 'v10'), exist_ok=True)
res.to_csv(os.path.join(os.path.dirname(__file__), '..', 'logs', 'v10', 'test_v10lib.csv'), index=False)
print('ALL PASS' if res.passed.all() else 'SOME FAILED'); sys.exit(0 if res.passed.all() else 1)
