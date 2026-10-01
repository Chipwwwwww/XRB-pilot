"""v4b3 (preregistration_v4.md §4, 3a): HEXTE cluster B high-energy colours for the v2 observations.
Download xh<obs>_s1.pha / _b1.pha (+ the rmf/arf named in their headers) from each observation's stdprod/,
net = s1 - b1 (EXPOSURE, BACKSCAL scaling; DEADAPP=T already), bands 25-40 and 40-60 keV via rmf EBOUNDS.
X1 = F_X(25-40) / F_PCA(16-25), X2 = F_X(40-60) / F_X(25-40); colour missing if its denominator S/N < 3
(train-fold median + 0/1 indicator). Main comparison on the HEXTE subset: H+X vs H (LR, RF), LOSO, paired bootstrap.
Secondary: fixed colour-overlap box (c1 >= 0.70, c2 >= 0.20)."""
import os, sys, urllib.error
os.environ['XRB_VERSION'] = 'v4b3'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, download, progress, D
from spectra import read_pha, read_rsp, overlap_matrix
import config as C
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from sklearn.model_selection import LeaveOneGroupOut
import v4lib as L
from plotstyle import plt, CLASS_COLOR

R, FG = ROOT/'results/v4b3', ROOT/'figures/v4b3'
for p in (R, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250)
obs = pd.read_csv(ROOT/'data/v2/observations.csv', dtype={'obs_id': str})
obs = obs[obs.in_dataset.astype(str).str.lower().eq('true')].reset_index(drop=True)
z = np.load(ROOT/'data/v2/processed/features.npz')
assert list(obs.obs_id) == list(z['obs_id'])
y, g, oid, edges = z['y'], z['source_id'], z['obs_id'], z['edges']
W = np.diff(edges); ec = np.sqrt(edges[:-1] * edges[1:]); m1625 = (ec >= 16) & (ec < 25.1)
F1625 = np.sum((z['rate'] * W)[:, m1625], 1); E1625 = np.sqrt(np.sum(((z['err'] * W)[:, m1625]) ** 2, 1))
BE = np.array([C.V4_HEXTE_BANDS['X_25_40'][0], C.V4_HEXTE_BANDS['X_25_40'][1], C.V4_HEXTE_BANDS['X_40_60'][1]])
_resp = {}


def fetch(r):
    o = r.obs_id.replace('-', ''); base = r.url_base
    rec = dict(obs_id=r.obs_id, source_id=r.source_id, label=r.label, mjd=r.mjd)
    if r.mjd >= C.V4_HEXTE_LAST_MJD:
        rec.update(status='no_hexte', reason='on/after 2009-12-14 16:10 UT (cluster B not rocking)'); return rec
    try:
        ps = download(base + f'xh{o}_s1.pha.gz', f'data/raw/hexte/{r.obs_id}/xh{o}_s1.pha.gz')
        pb = download(base + f'xh{o}_b1.pha.gz', f'data/raw/hexte/{r.obs_id}/xh{o}_b1.pha.gz')
    except urllib.error.HTTPError as e:
        rec.update(status='no_hexte', reason=f'cluster B file missing (HTTP {e.code})'); return rec
    s, b = read_pha(ps), read_pha(pb)
    from astropy.io import fits
    with fits.open(ps) as h: hd = h[1].header; resp, arf, deadapp = hd.get('RESPFILE'), hd.get('ANCRFILE'), hd.get('DEADAPP')
    rp = download(base + resp + '.gz', f'data/raw/hexte/resp/{resp}.gz')
    download(base + arf + '.gz', f'data/raw/hexte/resp/{arf}.gz')
    if resp not in _resp: _resp[resp] = read_rsp(rp)
    rsp = _resp[resp]
    ts, tb = s['exposure'] * s['areascal'], b['exposure'] * b['areascal']
    net = s['counts'] / ts - (s['backscal'] / b['backscal']) * b['counts'] / tb
    err = np.sqrt((s['stat_err'] / ts) ** 2 + ((s['backscal'] / b['backscal']) * b['stat_err'] / tb) ** 2)
    Wx = overlap_matrix(rsp['ch_lo'], rsp['ch_hi'], BE)
    fx, ex = Wx @ net, np.sqrt((Wx ** 2) @ err ** 2)
    rec.update(status='ok', reason='', respfile=resp, ancrfile=arf, deadapp=bool(deadapp), exposure_src=s['exposure'],
               exposure_bkg=b['exposure'], X_25_40=fx[0], X_25_40_err=ex[0], X_40_60=fx[1], X_40_60_err=ex[1],
               nchan=len(s['counts']))
    if deadapp is not True:
        rec.update(status='no_hexte', reason='DEADAPP not True')
    return rec


with ThreadPoolExecutor(max_workers=4) as ex:
    rows = list(ex.map(fetch, obs.itertuples()))
hx = pd.DataFrame(rows)
hx['F_PCA_16_25'], hx['F_PCA_16_25_err'] = F1625, E1625
hx['X1'] = hx.X_25_40 / hx.F_PCA_16_25; hx['X2'] = hx.X_40_60 / hx.X_25_40
hx['X1_den_snr'] = hx.F_PCA_16_25 / hx.F_PCA_16_25_err; hx['X2_den_snr'] = hx.X_25_40 / hx.X_25_40_err
hx.loc[hx.X1_den_snr < C.V4_HEXTE_MIN_DEN_SNR, 'X1'] = np.nan
hx.loc[hx.X2_den_snr < C.V4_HEXTE_MIN_DEN_SNR, 'X2'] = np.nan
hx.to_csv(D/'processed/hexte_features.csv', index=False)
ok = hx.status.eq('ok').values
print(hx.status.value_counts().to_dict(), hx[~ok].reason.value_counts().to_dict())
print('missing colours (among ok):', hx[ok].groupby('label')[['X1', 'X2']].apply(lambda d: d.isna().sum()).to_dict())
print('respfiles:', hx[ok].respfile.value_counts().to_dict(), '| DEADAPP all True:', bool(hx[ok].deadapp.all()))

# ---- modelling on the HEXTE subset ----
H = L.v2_representations(z['rate'], edges, z['F'])['H_colours']
Hs, ys, gs, os_ = H[ok], y[ok], g[ok], oid[ok]
X = hx.loc[ok, ['X1', 'X2']].values
folds = list(LeaveOneGroupOut().split(np.zeros(len(ys)), ys, gs))


def hx_features(tr, te):
    med = np.nanmedian(X[tr], axis=0); med = np.where(np.isfinite(med), med, 0.0)
    def f(idx):
        xx = X[idx].copy(); miss = ~np.isfinite(xx); xx[miss] = np.take(med, np.where(miss)[1])
        return np.c_[Hs[idx], xx, miss.astype(float)]
    return f(tr), f(te)


oofs = {}
for alg in ['LogReg', 'RandomForest']:
    sH = L.loso_scores(Hs, ys, gs, folds, alg)
    sX = np.full(len(ys), np.nan)
    for tr, te in folds:
        a, b = hx_features(tr, te); sX[te] = L.V4Model(alg).fit(a, ys[tr]).score(b)
    for name, s in (('H', sH), ('H+X', sX)):
        d = L.to_oof(np.arange(len(ys)), s, 0.5, ys, gs, os_, name, alg); oofs[f'{name}|{alg}'] = d
allo = pd.concat(oofs.values(), ignore_index=True); allo.to_csv(R/'v4b3_oof_predictions.csv', index=False)
bs = []
for alg in ['LogReg', 'RandomForest']:
    b = L.paired_bootstrap({f'H|{alg}': oofs[f'H|{alg}'], f'H+X|{alg}': oofs[f'H+X|{alg}']}, f'H|{alg}'); b['subset'] = 'HEXTE subset'; bs.append(b)
# secondary: colour-overlap box, sources with >= 3 box observations
box = (Hs[:, 0] >= C.V4_OVERLAP_BOX['c1_min']) & (Hs[:, 1] >= C.V4_OVERLAP_BOX['c2_min'])
inbox = set(os_[box]); nbox = pd.Series(gs[box]).value_counts(); srcs = set(nbox[nbox >= 3].index)
print(f'overlap box: {box.sum()} obs ({int(ys[box].sum())} BH), {len(srcs)} sources with >=3 box obs '
      f'({sum(ys[gs == s][0] for s in srcs)} BH)')
for alg in ['LogReg', 'RandomForest']:
    sub = {k: d[d.obs_id.isin(inbox) & d.source_id.isin(srcs)] for k, d in oofs.items() if k.endswith(alg)}
    if len({v for v in sub[f'H|{alg}'].true_label}) == 2:
        b = L.paired_bootstrap(sub, f'H|{alg}'); b['subset'] = 'overlap box (sources with >=3 box obs)'; bs.append(b)
bs = pd.concat(bs, ignore_index=True); bs.to_csv(R/'v4b3_bootstrap.csv', index=False)
d = bs.copy(); d['txt'] = d.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
print('\n' + d.pivot_table(index=['subset', 'comparison'], columns='metric', values='txt', aggfunc='first').to_string())

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for a, col, lab in zip(axes, ['X1', 'X2'], ['X1 = F_HEXTE(25–40) / F_PCA(16–25)', 'X2 = F_HEXTE(40–60) / F_HEXTE(25–40)']):
    for cl in ('NS', 'BH'):
        v = hx.loc[ok & (hx.label == cl).values, col].dropna()
        a.hist(v.clip(v.quantile(.01), v.quantile(.99)), bins=40, alpha=.6, color=CLASS_COLOR[cl], label=f'{cl} (n={len(v)})')
    a.set_xlabel(lab); a.legend(fontsize=7)
fig.suptitle('v4b3: HEXTE cluster B high-energy colours (count space; cross-instrument ratio for X1)', x=.01, ha='left')
fig.savefig(FG/'v4b3_hexte_colours.png'); plt.close(fig)
prim = bs[(bs.subset == 'HEXTE subset') & bs.comparison.str.contains(' - ')]
progress('v4b3_hexte', f"{ok.sum()} obs with HEXTE; " + '; '.join(f"{r.comparison} {r.metric} {r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]"
                                                                  for r in prim[prim.metric != 'obs_balanced_accuracy'].itertuples()))
