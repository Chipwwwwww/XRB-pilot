"""Wrap-up figure (descriptive, no new evaluation): the two count-space colours used by H, with
- all 456 v2 observations (BH / NS), source medians of the 7 BHs labelled;
- the LogReg (StandardScaler + LR, v2 hyperparameters) 0.5 boundary and the RandomForest 0.5 contour,
  both fitted on ALL 31 confirmed sources.  These full-data fits are for visualisation only; the performance
  numbers in the reports come from the leave-one-source-out predictions, not from these fits;
- right panel: the 14 v3c BH candidates (source median and 16-84 % range), which were never used in these fits.
Output: figures/final/colour_colour_decision_boundary.png, results/final/colour_colour_source_medians.csv"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, progress
from v3lib import *
from plotstyle import plt, INK, INK2, CLASS_COLOR

FG, RS = ROOT/'figures/final', ROOT/'results/final'
FG.mkdir(parents=True, exist_ok=True); RS.mkdir(parents=True, exist_ok=True)
z = np.load(ROOT/'data/v2/processed/features.npz')
H = v2_representations(z['rate'], z['edges'], z['F'])['H_colours']; y, g = z['y'], z['source_id']
zc = np.load(ROOT/'data/v3c/processed/features.npz')
Hc = v2_representations(zc['rate'], zc['edges'], zc['F'])['H_colours']; gc = zc['source_id']

lr = MODELS['LogReg']().fit(H, y); rf = MODELS['RandomForest']().fit(H, y)
sc, clf = lr.named_steps['standardscaler'], lr.named_steps['logisticregression']
w = clf.coef_[0] / sc.scale_; b = clf.intercept_[0] - np.sum(clf.coef_[0] * sc.mean_ / sc.scale_)  # boundary in raw colours

allx = np.r_[H[:, 0], Hc[:, 0]]; ally = np.r_[H[:, 1], Hc[:, 1]]
xl = np.percentile(allx, [0.5, 99.5]) * [0.9, 1.1]; yl = np.percentile(ally, [0.5, 99.5]) * [0.9, 1.1]
gx, gy = np.meshgrid(np.linspace(*xl, 300), np.linspace(*yl, 300))
prf = rf.predict_proba(np.c_[gx.ravel(), gy.ravel()])[:, 1].reshape(gx.shape)


def med(Hs, groups, lab=None):
    d = pd.DataFrame(dict(source_id=groups, c1=Hs[:, 0], c2=Hs[:, 1]))
    out = d.groupby('source_id').agg(n=('c1', 'size'), c1_med=('c1', 'median'), c2_med=('c2', 'median'),
                                     c1_p16=('c1', lambda v: np.percentile(v, 16)), c1_p84=('c1', lambda v: np.percentile(v, 84)),
                                     c2_p16=('c2', lambda v: np.percentile(v, 16)), c2_p84=('c2', lambda v: np.percentile(v, 84)))
    return out


mc = med(H, g).join(pd.Series(np.where(pd.Series(y, index=g).groupby(level=0).first() == 1, 'BH', 'NS'),
                              index=sorted(set(g)), name='label'))
mk = med(Hc, gc).assign(label='BH candidate')
pd.concat([mc, mk]).round(4).to_csv(RS/'colour_colour_source_medians.csv')


def boundaries(a):
    xx = np.linspace(*xl, 50)
    if abs(w[1]) > 1e-12: a.plot(xx, -(w[0] * xx + b) / w[1], color=INK, lw=1.4, label='LogReg 0.5 boundary')
    a.contour(gx, gy, prf, levels=[0.5], colors=[INK2], linestyles='--', linewidths=1.1)
    a.plot([], [], color=INK2, ls='--', lw=1.1, label='RandomForest 0.5 contour')
    a.set_xlim(*xl); a.set_ylim(*yl)
    a.set_xlabel('soft colour  F(7–10 keV) / F(5–7 keV)'); a.set_ylabel('hard colour  F(16–25 keV) / F(10–16 keV)')


fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5.4), sharex=True, sharey=True)
for lab in ['NS', 'BH']:
    s = y == (lab == 'BH')
    a1.scatter(H[s, 0], H[s, 1], s=9, alpha=.45, color=CLASS_COLOR[lab], lw=0, label=f'{lab} observation')
for sid, r in mc[mc.label == 'BH'].iterrows():
    a1.plot(r.c1_med, r.c2_med, 'o', ms=7, mfc='white', mec=CLASS_COLOR['BH'], mew=1.6)
    a1.annotate(sid, (r.c1_med, r.c2_med), fontsize=7, xytext=(4, 4), textcoords='offset points', color=INK)
boundaries(a1); a1.legend(loc='upper left', fontsize=7.5)
a1.set_title('31 confirmed sources, 456 observations (open circles: BH source medians)', loc='left', fontsize=9)
a2.scatter(H[:, 0], H[:, 1], s=6, alpha=.12, color='#9e9d98', lw=0)
for sid, r in mk.iterrows():
    a2.plot([r.c1_p16, r.c1_p84], [r.c2_med] * 2, color=CLASS_COLOR['BH'], lw=.8, alpha=.6)
    a2.plot([r.c1_med] * 2, [r.c2_p16, r.c2_p84], color=CLASS_COLOR['BH'], lw=.8, alpha=.6)
    a2.plot(r.c1_med, r.c2_med, 'D', ms=5, color=CLASS_COLOR['BH'])
    a2.annotate(sid, (r.c1_med, r.c2_med), fontsize=6.5, xytext=(4, 3), textcoords='offset points', color=INK)
boundaries(a2)
a2.set_title('14 v3c BH candidates (median, 16–84 %); grey = confirmed observations', loc='left', fontsize=9)
fig.suptitle('Colour–colour diagram (RXTE/PCA count space, per PCU). Boundaries fitted on all confirmed sources for '
             'illustration only; reported accuracies are leave-one-source-out.', x=.01, ha='left', fontsize=9.5)
fig.savefig(FG/'colour_colour_decision_boundary.png'); plt.close(fig)
print('LR boundary in raw colours: %.3f*c1 + %.3f*c2 + %.3f = 0' % (w[0], w[1], b))
print(mc[mc.label == 'BH'][['c1_med', 'c2_med']].round(3).to_string())
progress('final_colour_colour', 'figures/final/colour_colour_decision_boundary.png')
