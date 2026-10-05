"""v11 checks before any new data (preregistration_v11.md sec. 8, IC4 + streaming check): zero-centred Lorentzian fits to the
13 log-bin variances recover the width within +-30% (single Lorentzian, nu0 = 0.3 / 5 Hz, rms 0.3, 10% noise; and the lower
component of a two-Lorentzian spectrum); the in-memory streamed parse of a real NICER file equals the v10 prefix+tail parse."""
import os, sys
os.environ.setdefault('XRB_VERSION', 'v11')
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import v10lib as L10, v11lib as L11

rng = np.random.default_rng(42); rows = []
for nu0 in (0.3, 5.0):
    est = []
    for k in range(20):
        true = L11.lor_int(0.09, nu0); se = 0.10 * true + 1e-5
        f = L11.fit_lorentz(true + rng.normal(0, se), se); est.append(f['nu_L'])
    med = float(np.median(est))
    rows.append(dict(test=f'single Lorentzian nu0 = {nu0} Hz: median fitted width over 20 noisy draws', value=round(med, 3), passed=bool(abs(med / nu0 - 1) <= 0.3)))
est = []
for k in range(20):
    true = L11.lor_int(0.05, 0.1) + L11.lor_int(0.04, 3.0); se = 0.05 * true + 1e-5
    f = L11.fit_lorentz(true + rng.normal(0, se), se); est.append((f['nu_L'], f['n_lor']))
med = float(np.median([e[0] for e in est])); n2 = float(np.mean([e[1] == 2 for e in est]))
rows.append(dict(test=f'two Lorentzians (0.1 + 3 Hz): lower width (two components chosen in {n2:.0%})', value=round(med, 3), passed=bool(abs(med / 0.1 - 1) <= 0.3)))
# streaming parse = v10 prefix + tail parse (real file used for the v10 IC1)
o = '6403520101'
a10, _, c10 = L10.read_full(o)
meta = __import__('json').loads(L10.prefix_paths(o)[1].read_text())
a11, info = L11.stream_events(meta['url'])
ok = info['complete'] and c10 and all(np.array_equal(a10[k], a11[k]) for k in ('TIME', 'PI', 'DET_ID'))
rows.append(dict(test=f'streamed parse == v10 prefix+tail parse ({o}, {info["bytes"]} bytes)', value=len(a11['TIME']), passed=bool(ok)))
res = pd.DataFrame(rows); print(res.to_string(index=False))
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'logs', 'v11'), exist_ok=True)
res.to_csv(os.path.join(os.path.dirname(__file__), '..', 'logs', 'v11', 'test_v11lib.csv'), index=False)
print('ALL PASS' if res.passed.all() else 'SOME FAILED'); sys.exit(0 if res.passed.all() else 1)
