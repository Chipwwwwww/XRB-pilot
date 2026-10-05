"""v9c (preregistration_v9.md sec. 6, descriptive): where does the MAXI 2-4 keV gain sit? The frozen v8d OOF (RF[C2D], RF[C1D],
RF[C2D_NH], RF[C1D_NH]; main task BH vs NPNS) stratified by tertiles of C4 = (H-M)/(H+M) (>= 4 keV colour, independent of the
2-4 keV band); point-level AUC per tertile and the C2D - C1D difference, v7a-type bootstrap over all main-task sources."""
import os, sys
os.environ['XRB_VERSION'] = 'v9'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
import v7lib as L7, v8lib as L8
from plotstyle import plt, INK2

RC, FG = ROOT/'results/v9c', ROOT/'figures/v9'
for p in (RC, FG): p.mkdir(parents=True, exist_ok=True)
pts = pd.read_csv(ROOT/'data/v7c/maxi_points.csv')
pts['C4'] = (pts.H - pts.M) / (pts.H + pts.M); pts['SC'] = (pts.M - pts.L) / (pts.M + pts.L)
pts['obs_id'] = pts.source + '_' + pts.mjd.round(1).astype(str)
main = pts[pts.cls.isin(['BH', 'NPNS'])].drop_duplicates('obs_id')
q = np.percentile(main.C4, [100 / 3, 200 / 3])
lab = np.where(main.C4 < q[0], 'C4 low (softest >=4 keV)', np.where(main.C4 < q[1], 'C4 middle', 'C4 high (hardest)'))
groups = pd.Series(lab, index=main.obs_id.values)
oof = pd.read_csv(ROOT/'results/v8d/v8d_oof_predictions.csv.gz')
M = ['RF [C1D]', 'RF [C2D]', 'RF [C1D_NH]', 'RF [C2D_NH]']
srcs = oof.drop_duplicates('source_id').set_index('source_id').true_label.to_dict()
draws = L7.boot_draws(srcs)
sb = {m: L8.strat_boot(oof[oof.model == m], groups, draws) for m in M}
rows = []
for gname in ['C4 low (softest >=4 keV)', 'C4 middle', 'C4 high (hardest)']:
    d = oof[(oof.model == M[0])].assign(g=lambda x: x.obs_id.map(groups)); d = d[d.g == gname]
    for m in M:
        rows.append(dict(stratum=gname, comparison=m, **L8.summarize(sb[m][gname][0][0], sb[m][gname][1][:, 0]),
                         n_points=len(d), n_BH_sources=int(d[d.true_label == 'BH'].source_id.nunique()), n_NS_sources=int(d[d.true_label == 'NS'].source_id.nunique())))
    for a, b in (('RF [C2D]', 'RF [C1D]'), ('RF [C2D_NH]', 'RF [C1D_NH]')):
        r = dict(stratum=gname, comparison=f'{a} - {b}', **L8.summarize(sb[a][gname][0][0] - sb[b][gname][0][0], sb[a][gname][1][:, 0] - sb[b][gname][1][:, 0]))
        r['verdict'] = L8.verdict(r); rows.append(r)
res = pd.DataFrame(rows); res.to_csv(RC/'v9c_maxi_c4_strata.csv', index=False)
res['txt'] = res.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
print('C4 tertile cuts:', np.round(q, 3))
print(res.pivot_table(index='comparison', columns='stratum', values='txt', aggfunc='first').to_string())
print(res.drop_duplicates('stratum')[['stratum', 'n_points', 'n_BH_sources', 'n_NS_sources']].to_string(index=False))
fig, a = plt.subplots(figsize=(7, 3.8), layout='constrained')
S = ['C4 low (softest >=4 keV)', 'C4 middle', 'C4 high (hardest)']
for i, (m, col) in enumerate((('RF [C1D]', '#9aa5b1'), ('RF [C2D]', '#2a78d6'), ('RF [C2D_NH]', '#1baf7a'))):
    d = res[res.comparison == m].set_index('stratum').loc[S]
    x = np.arange(3) + (i - 1) * 0.15
    a.errorbar(x, d.point, yerr=[d.point - d.ci2_5, d.ci97_5 - d.point], fmt='o', capsize=2, color=col, label=m)
a.set_xticks(range(3)); a.set_xticklabels(S, fontsize=8); a.axhline(.5, color=INK2, lw=.6, ls='--')
a.set_ylabel('point-level AUC (MAXI, BH vs NPNS)'); a.legend(frameon=False, fontsize=7)
a.set_title('v9c: MAXI 2-4 keV gain by >=4 keV colour tertile (descriptive)', loc='left', fontsize=9)
fig.savefig(FG/'v9c_maxi_c4_strata.png'); plt.close(fig)
progress('v9c_maxi', '; '.join(f"{r.stratum}: {r.comparison} {r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]" for r in res[res.comparison == 'RF [C2D] - RF [C1D]'].itertuples()))

# ---- POST HOC (decision_log): source-level version (point-level AUC is dominated by sources with thousands of points) ----
import v4lib as L
srows = []
for gname in S:
    sub = {m: oof[(oof.model == m) & (oof.obs_id.map(groups) == gname)] for m in M}
    for a, b in (('RF [C1D]', 'RF [C2D]'), ('RF [C1D_NH]', 'RF [C2D_NH]')):
        bt = L.paired_bootstrap({a: sub[a], b: sub[b]}, a); bt['stratum'] = gname; srows.append(bt)
sr = pd.concat(srows, ignore_index=True); sr.to_csv(RC/'v9c_maxi_c4_strata_source_level_post_hoc.csv', index=False)
sr = sr[sr.metric == 'source_AUC'].assign(txt=lambda d: d.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1))
print('\n[post hoc] source-level AUC within C4 tertiles:\n' + sr.pivot_table(index='comparison', columns='stratum', values='txt', aggfunc='first').to_string())
