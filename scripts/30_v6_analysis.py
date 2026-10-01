"""v6 step 3 (preregistration_v6.md §2, §4-6). PRIMARY v6a: frozen H_R-LR vs H_R+T-LR (trained once on S1) on external
sources E. v6c CCTLR (S1/S2/S3 LOSO, E frozen); v6d colour-conditional source-permutation test (S1, E replication);
v6e source-level conformal sets; v6f observation-budget curves (S3); v6g proper scores; v6h robustness (S1)."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v6'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import LeaveOneGroupOut
import config as C
import v4lib as L, v5lib as L5, v6lib as L6
from plotstyle import plt, CLASS_COLOR, INK, INK2

R6, FG = ROOT/'results/v6', ROOT/'figures/v6'
for p in (R6, FG): p.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300); pd.set_option('display.max_colwidth', 70)
T0 = time.time()
TC = ['T1', 'T2', 'T3']


def reps_R(z):                                   # identical to 22_v4b2_analysis.reps_R (H_R: colours of rate / folded Gamma=2 PL)
    W = np.diff(z['edges']); ec = np.sqrt(z['edges'][:-1] * z['edges'][1:])
    band = lambda a, lo, hi: np.sum((a * W)[:, (ec >= lo) & (ec < hi)], 1)
    c = {k: band(z['rate'], *b) / band(z['pl2'], *b) for k, b in {'b1': (5, 7), 'b2': (7, 10), 'b3': (10, 16), 'b4': (16, 25.1)}.items()}
    return np.c_[c['b2'] / c['b1'], c['b4'] / c['b3']]


def txt(bs):
    t = bs[bs.comparison.str.contains(' - ')].copy()
    t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]", axis=1)
    return t.pivot_table(index='comparison', columns='metric', values='txt', aggfunc='first').to_string()


def pts(bs):
    t = bs[~bs.comparison.str.contains(' - ')]
    return t.pivot_table(index='comparison', columns='metric', values='point', aggfunc='first').round(3).to_string()


def oof(idx, s, y, g, o, rep, model):
    return L.to_oof(idx, s, 0.5, y, g, o, rep, model)


# ---------------- timing tables ----------------
T5 = pd.concat([pd.read_csv(ROOT/'data/v5/processed/timing_features.csv', dtype={'obs_id': str}),
                pd.read_csv(ROOT/'data/v6/processed/timing_v5_new.csv', dtype={'obs_id': str})]).drop_duplicates('obs_id').set_index('obs_id')
T6 = pd.read_csv(ROOT/'data/v6/processed/timing_v6.csv', dtype={'obs_id': str}).drop_duplicates('obs_id').set_index('obs_id')
t5 = lambda o: T5.reindex(o)[TC].values.astype(float)
t6 = lambda o: T6.reindex(o)[[f'{k}s' for k in TC]].values.astype(float)

# ---------------- S1 ----------------
z = np.load(ROOT/'data/v2/processed/features.npz')
y, g, oid = z['y'], z['source_id'], z['obs_id']
H = L.v2_representations(z['rate'], z['edges'], z['F'])['H_colours']; HR = reps_R(z)
T, Ts = t5(oid), t6(oid)
folds = list(LeaveOneGroupOut().split(np.zeros(len(y)), y, g))
v2oof = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
REF = v2oof[(v2oof.representation == 'H_colours') & (v2oof.model == 'LogReg')]
v5oof = pd.read_csv(ROOT/'results/v5/v5_oof_predictions.csv', dtype={'obs_id': str})
V5 = lambda smp, name: v5oof[(v5oof['sample'] == smp) & (v5oof['name'] == name)]
bs_all, ps_all = [], []


def boot(oofs, ref, label):
    b = L.paired_bootstrap(oofs, ref); b['analysis'] = label; bs_all.append(b)
    p = L6.proper_score_bootstrap(oofs, ref); p['analysis'] = label; ps_all.append(p)
    return b, p


def fillfit(Ttr, Tte):
    return L5.fill_missing(Ttr, Tte)


# ================= v6a PRIMARY: frozen external validation =================
src6 = pd.read_csv(ROOT/'data/v6/sources.csv'); role6 = src6.set_index('source_id').role
z3, z6 = np.load(ROOT/'data/v4b2/processed/features.npz'), np.load(ROOT/'data/v6/processed/features.npz')
yE = np.r_[z3['y'], z6['y']]; gE = np.r_[z3['source_id'], z6['source_id']]; oE = np.r_[z3['obs_id'], z6['obs_id']]
HRE = np.r_[reps_R(z3), reps_R(z6)]; TE = t5(oE)
roleE = np.array(['E_v4b2'] * len(z3['y']) + [role6.get(s, '?') for s in z6['source_id']])
Tf_tr, Tf_E = fillfit(T, TE)
fro = {'H_R-LR': L.V4Model('LogReg').fit(HR, y), 'H_R+T-LR': L.V4Model('LogReg').fit(np.c_[HR, Tf_tr], y),
       'CCTLR (H_R)': L6.CCTLR().fit(HR, T, y, g)}
coef = fro['H_R+T-LR'].m.coef_[0]
print('frozen H_R+T-LR coefficients [c1, c2, T1, T2, T3, miss]:', np.round(coef, 3), flush=True)
sE = {'H_R-LR': fro['H_R-LR'].score(HRE), 'H_R+T-LR': fro['H_R+T-LR'].score(np.c_[HRE, Tf_E]), 'CCTLR (H_R)': fro['CCTLR (H_R)'].score(HRE, TE)}
oE_ = {k: oof(np.arange(len(yE)), s, yE, gE, oE, 'H_R', k).assign(role=roleE) for k, s in sE.items()}
pd.concat([v.assign(name=k) for k, v in oE_.items()]).to_csv(R6/'v6a_external_scores.csv', index=False)
isE = roleE != 'stress_slow_pulsar'; isNew = roleE == 'E_new'
nbhE = len(set(gE[isE & (yE == 1)]))
print(f'\nE: {len(set(gE[isE]))} sources ({nbhE} BH), {isE.sum()} obs; E_new: {len(set(gE[isNew]))} sources '
      f'({len(set(gE[isNew & (yE == 1)]))} BH); stress: {len(set(gE[~isE]))} sources', flush=True)
subE = {k: v[isE] for k, v in oE_.items()}
bE, pE = boot(subE, 'H_R-LR', 'v6a PRIMARY external E (frozen, trained on S1)')
print('\n[v6a PRIMARY] E\n' + pts(bE) + '\n' + txt(bE) + '\n' + txt(pE), flush=True)
if len({*gE[isNew & (yE == 1)]}) and len({*gE[isNew & (yE == 0)]}):
    bN, pN = boot({k: v[isNew] for k, v in oE_.items()}, 'H_R-LR', 'v6a sensitivity E_new only')
    print('\n[v6a sensitivity] E_new\n' + pts(bN) + '\n' + txt(bN), flush=True)
perE = pd.concat([L.src_table(v).assign(name=k) for k, v in oE_.items()]).reset_index()
perE['role'] = perE.source_id.map(dict(zip(gE, roleE)))
perE.to_csv(R6/'v6a_external_per_source.csv', index=False)
print('\n' + perE.pivot_table(index=['role', 'source_id', 'true_label'], columns='name', values='score').round(2).to_string(), flush=True)

# ================= S1 LOSO: H_R models (conformal calibration for E) and CCTLR =================
def loso_fill(Hx, Tx, yy, gg, ff, alg='LogReg', weighting=None):
    s = np.full(len(yy), np.nan)
    for tr, te in ff:
        a, b = fillfit(Tx[tr], Tx[te]); w = L.source_equal_weights(yy[tr], gg[tr]) if weighting else None
        s[te] = L.V4Model(alg).fit(np.c_[Hx[tr], a], yy[tr], w).score(np.c_[Hx[te], b])
    return s


s1 = {'H-LR (v2)': REF, 'H+T-LR (v5)': V5('S1', 'H+T|LogReg'),
      'CCTLR': oof(np.arange(len(y)), L6.cctlr_loso(H, T, y, g, folds), y, g, oid, 'H+T', 'CCTLR'),
      'H+T*-LR': oof(np.arange(len(y)), loso_fill(H, Ts, y, g, folds), y, g, oid, 'H+T*', 'LogReg')}
s1R = {'H_R-LR': oof(np.arange(len(y)), L.loso_scores(HR, y, g, folds, 'LogReg'), y, g, oid, 'H_R', 'LogReg'),
       'H_R+T-LR': oof(np.arange(len(y)), loso_fill(HR, T, y, g, folds), y, g, oid, 'H_R+T', 'LogReg'),
       'CCTLR (H_R)': oof(np.arange(len(y)), L6.cctlr_loso(HR, T, y, g, folds), y, g, oid, 'H_R+T', 'CCTLR')}
b1, p1 = boot(s1, 'H-LR (v2)', 'v6c S1 LOSO')
b1b, _ = boot({'H+T-LR (v5)': s1['H+T-LR (v5)'], 'CCTLR': s1['CCTLR']}, 'H+T-LR (v5)', 'v6c S1 CCTLR vs H+T-LR')
print('\n[v6c S1]\n' + pts(b1) + '\n' + txt(b1) + '\n' + txt(b1b) + '\n' + txt(p1), flush=True)
lam = np.full(len(y), np.nan)
for tr, te in folds: lam[te] = L6.CCTLR().fit(H[tr], T[tr], y[tr], g[tr]).timing_llr(H[te], T[te])

# ---- S2 (v2 + v4b2, 46 sources) ----
y2 = np.r_[y, z3['y']]; g2 = np.r_[g, z3['source_id']]; o2 = np.r_[oid, z3['obs_id']]
H2 = np.r_[H, L.v2_representations(z3['rate'], z3['edges'], z3['F'])['H_colours']]; T2 = t5(o2)
f2 = list(LeaveOneGroupOut().split(np.zeros(len(y2)), y2, g2))
v4b2 = pd.read_csv(ROOT/'results/v4b2/v4b2_oof_predictions.csv', dtype={'obs_id': str})
s2 = {'H-LR (S2)': v4b2[(v4b2.representation == 'H_count_space') & (v4b2.model == 'LogReg')], 'H+T-LR (v5 S2)': V5('S2', 'H+T|LogReg'),
      'CCTLR': oof(np.arange(len(y2)), L6.cctlr_loso(H2, T2, y2, g2, f2), y2, g2, o2, 'H+T', 'CCTLR')}
b2, p2 = boot(s2, 'H-LR (S2)', 'v6c S2 LOSO (46 sources)')
print('\n[v6c S2]\n' + pts(b2) + '\n' + txt(b2), flush=True)

# ---- S3 (v4b1, 7949 obs, source-equal weights) ----
z4 = np.load(ROOT/'data/v4b1/processed/features.npz')
y3, g3, o3 = z4['y'], z4['source_id'], z4['obs_id']
H3 = L.v2_representations(z4['rate'], z4['edges'], z4['F'])['H_colours']; T3 = t5(o3)
f3 = list(LeaveOneGroupOut().split(np.zeros(len(y3)), y3, g3))
v4b1 = pd.read_csv(ROOT/'results/v4b1/v4b1_oof_predictions.csv', dtype={'obs_id': str})
c3 = Parallel(n_jobs=16)(delayed(lambda tr, te: (te, L6.CCTLR().fit(H3[tr], T3[tr], y3[tr], g3[tr], L.source_equal_weights(y3[tr], g3[tr])).score(H3[te], T3[te])))(tr, te) for tr, te in f3)
sc3 = np.full(len(y3), np.nan)
for te, s in c3: sc3[te] = s
s3 = {'H-LR (v2)': REF, 'H-LR[srcw] (S3)': v4b1[(v4b1.representation == 'H_colours') & (v4b1.model == 'LogReg[srcw]')],
      'H+T-LR[srcw] (v5 S3)': V5('S3', 'H+T|LogReg[srcw]'), 'CCTLR[srcw]': oof(np.arange(len(y3)), sc3, y3, g3, o3, 'H+T', 'CCTLR[srcw]')}
b3, p3 = boot(s3, 'H-LR (v2)', 'v6c S3 LOSO (7949 obs)')
print('\n[v6c S3]\n' + pts(b3) + '\n' + txt(b3), flush=True)
print(f'LOSO done ({time.time()-T0:.0f} s)', flush=True)

# ================= v6d colour-conditional source-permutation test =================
feats = {'T1*': T6.reindex(oid)['T1s'].values, 'T2*': T6.reindex(oid)['T2s'].values, 'T3*': T6.reindex(oid)['T3s'].values,
         'log10 nu_c': np.log10(T6.reindex(oid)['nu_c'].values)}
featsE = {'T1*': T6.reindex(oE)['T1s'].values, 'T2*': T6.reindex(oE)['T2s'].values, 'T3*': T6.reindex(oE)['T3s'].values,
          'log10 nu_c': np.log10(T6.reindex(oE)['nu_c'].values)}
labS1 = pd.Series(y, index=g).groupby(level=0).first(); labE = pd.Series(yE[isE], index=gE[isE]).groupby(level=0).first()
prow = []
for k in feats:
    r1 = L6.source_residuals(HR, feats[k], g); a = L6.perm_test(r1, labS1)
    rE = L6.source_residuals(HR, feats[k], g, HRE[isE], featsE[k][isE], gE[isE]); e = L6.perm_test(rE, labE)
    prow.append(dict(feature=k, S1_D=a['D'], S1_p=a['p'], S1_sources=a['n_sources'], S1_bh=a['n_bh'],
                     E_D=e['D'], E_p=e['p'], E_sources=e['n_sources'], E_bh=e['n_bh']))
perm = pd.DataFrame(prow); perm['S1_p_holm'] = L6.holm(perm.S1_p); perm['E_p_holm'] = L6.holm(perm.E_p)
perm.to_csv(R6/'v6d_permutation_test.csv', index=False)
print('\n[v6d] colour-conditional source-permutation test\n' + perm.round(4).to_string(index=False), flush=True)

# ================= v6e conformal =================
crow, cset = [], []
for name, d in {**s1, **s1R}.items():
    t = L.src_table(d); sy = (t.true_label == 'BH').astype(int).values
    for eps in C.V6_CONFORMAL_EPS:
        for (p1_, p0_, st), sid, yy in zip(L6.conformal_loso(t.score.values, sy, eps), t.index, sy):
            cset.append(dict(sample='S1 LOSO', model=name, eps=eps, source_id=sid, true=('BH' if yy else 'NS'), p_BH=p1_, p_NS=p0_, set=st))
for name in ('H_R-LR', 'H_R+T-LR', 'CCTLR (H_R)'):
    cal = L.src_table(s1R[name]); tE = L.src_table(subE[name])
    for eps in C.V6_CONFORMAL_EPS:
        res = L6.conformal_sets(cal.score.values, (cal.true_label == 'BH').astype(int).values, tE.score.values, eps)
        for (p1_, p0_, st), sid, tl in zip(res, tE.index, tE.true_label):
            cset.append(dict(sample='E (frozen, S1 calibration)', model=name, eps=eps, source_id=sid, true=tl, p_BH=p1_, p_NS=p0_, set=st))
cs = pd.DataFrame(cset); cs.to_csv(R6/'v6e_conformal_sets.csv', index=False)
for (smp, m, eps), d in cs.groupby(['sample', 'model', 'eps'], sort=False):
    cov = d.apply(lambda r: r.true in r.set, axis=1)
    crow.append(dict(sample=smp, model=m, eps=eps, coverage_BH=cov[d.true == 'BH'].mean(), coverage_NS=cov[d.true == 'NS'].mean(),
                     mean_set_size=d.set.map({'{BH}': 1, '{NS}': 1, '{BH,NS}': 2, '{}': 0}).mean(),
                     n_singleton_correct=int(((d.set == '{BH}') & (d.true == 'BH') | (d.set == '{NS}') & (d.true == 'NS')).sum()),
                     n_ambiguous=int((d.set == '{BH,NS}').sum()), n_empty=int((d.set == '{}').sum()), n_sources=len(d),
                     ambiguous=';'.join(d[d.set == '{BH,NS}'].source_id)))
csum = pd.DataFrame(crow); csum.to_csv(R6/'v6e_conformal_summary.csv', index=False)
print('\n[v6e] conformal\n' + csum.drop(columns='ambiguous').round(3).to_string(index=False), flush=True)

# ================= v6f observation-budget curves (S3) =================
bud = pd.concat([L6.budget_curves(s3[k]).assign(model=k) for k in ('H-LR[srcw] (S3)', 'H+T-LR[srcw] (v5 S3)', 'CCTLR[srcw]')])
bud.to_csv(R6/'v6f_budget_curves.csv', index=False)
print('\n[v6f] budget\n' + bud.pivot_table(index=['metric', 'k'], columns='model', values='median').round(3).to_string(), flush=True)

# ================= v6h robustness (S1) =================
ob2 = pd.read_csv(ROOT/'data/v2/observations.csv', dtype={'obs_id': str}); ob2 = ob2[ob2.in_dataset.astype(str).str.lower().eq('true')].set_index('obs_id').loc[oid]
Nn = np.c_[np.log10(np.clip(z['F'], 1e-3, None)), ob2.std1_npcu_on.values, ob2.bkg_fraction.values, 2000 + (ob2.mjd.values - 51544.5) / 365.25]
rob = {'H-LR (v2)': REF,
       'H+N-LR': oof(np.arange(len(y)), L.loso_scores(np.c_[H, Nn], y, g, folds, 'LogReg'), y, g, oid, 'H+N', 'LogReg'),
       'H+N+T-LR': oof(np.arange(len(y)), loso_fill(np.c_[H, Nn], T, y, g, folds), y, g, oid, 'H+N+T', 'LogReg')}
for j, k in enumerate(TC):
    rob[f'H+{k}-LR'] = oof(np.arange(len(y)), loso_fill(H, T[:, [j]], y, g, folds), y, g, oid, f'H+{k}', 'LogReg')
bR, _ = boot(rob, 'H-LR (v2)', 'v6h S1 robustness')
bR2, _ = boot({'H+N-LR': rob['H+N-LR'], 'H+N+T-LR': rob['H+N+T-LR']}, 'H+N-LR', 'v6h S1 nuisance-adjusted: H+N+T vs H+N')
print('\n[v6h]\n' + pts(bR) + '\n' + txt(bR) + '\n' + txt(bR2), flush=True)

# ================= outputs =================
bs = pd.concat(bs_all, ignore_index=True); bs.to_csv(R6/'v6_bootstrap.csv', index=False)
psc = pd.concat(ps_all, ignore_index=True); psc.to_csv(R6/'v6_proper_scores.csv', index=False)
pd.concat([v.assign(analysis='S1', name=k) for k, v in s1.items() if k in ('CCTLR', 'H+T*-LR')] +
          [v.assign(analysis='S1 H_R', name=k) for k, v in s1R.items()] +
          [s2['CCTLR'].assign(analysis='S2', name='CCTLR'), s3['CCTLR[srcw]'].assign(analysis='S3', name='CCTLR[srcw]')] +
          [v.assign(analysis='S1 robustness', name=k) for k, v in rob.items() if k != 'H-LR (v2)'], ignore_index=True).to_csv(R6/'v6_oof_predictions.csv', index=False)
print('\n[v6g] proper scores (lower is better)\n' + txt(psc), flush=True)

# ---- figures ----
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
pe = perE.pivot_table(index=['source_id', 'true_label', 'role'], columns='name', values='score').reset_index()
mk = {'E_v4b2': 'o', 'E_new': 's', 'stress_slow_pulsar': '^'}
for a, m in zip(axes, ['H_R+T-LR', 'CCTLR (H_R)']):
    for (lab, role), d in pe.groupby(['true_label', 'role']):
        a.scatter(d['H_R-LR'], d[m], marker=mk[role], s=40, color=CLASS_COLOR[lab], alpha=.8, label=f'{lab} {role}')
        for _, r in d.iterrows(): a.annotate(r['source_id'], (r['H_R-LR'], r[m]), fontsize=5.5, xytext=(3, 2), textcoords='offset points')
    a.plot([0, 1], [0, 1], color=INK2, lw=.6); a.axhline(.5, color=INK2, ls='--', lw=.6); a.axvline(.5, color=INK2, ls='--', lw=.6)
    a.set_xlabel('frozen H_R-LR source score'); a.set_ylabel(f'frozen {m} source score'); a.set_title(m, loc='left')
axes[0].legend(fontsize=6, frameon=False, loc='upper left')
fig.suptitle('v6a: external sources never used in training (models frozen on the 31 v2 sources); ^ = slow-pulsar stress set', x=.01, ha='left')
fig.savefig(FG/'v6a_external_sources.png'); plt.close(fig)

fig, a = plt.subplots(figsize=(7.5, 5.5))
ok = np.isfinite(lam)
scp = a.scatter(H[ok, 0], H[ok, 1], c=np.clip(lam[ok], -6, 6), cmap='coolwarm', s=14, vmin=-6, vmax=6, lw=0)
a.scatter(H[~ok, 0], H[~ok, 1], s=8, facecolor='none', edgecolor=INK2, lw=.5, label='timing missing')
for lab, mk_ in (('BH', 'x'), ('NS', '+')):
    m = (y == (lab == 'BH')) & ok; a.scatter(H[m, 0], H[m, 1], marker=mk_, s=6, color=INK, lw=.4, alpha=.5, label=f'{lab} (marker)')
plt.colorbar(scp, ax=a, label='OOF timing log-likelihood ratio  log p(T|H,BH)/p(T|H,NS)')
a.set_xlabel('soft colour F(7–10)/F(5–7)'); a.set_ylabel('hard colour F(16–25)/F(10–16)'); a.legend(fontsize=6, loc='upper left')
a.set_title('v6c CCTLR: where timing carries evidence (S1, LOSO)', loc='left', fontsize=9)
fig.savefig(FG/'v6c_timing_evidence_map.png'); plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
for a, met in zip(axes, ['source_balanced_accuracy', 'source_AUC']):
    for m, col in (('H-LR[srcw] (S3)', INK), ('H+T-LR[srcw] (v5 S3)', '#2a78d6'), ('CCTLR[srcw]', '#c2410c')):
        d = bud[(bud.model == m) & (bud.metric == met)]
        a.plot(d.k, d['median'], 'o-', color=col, label=m, ms=3); a.fill_between(d.k, d.p2_5, d.p97_5, color=col, alpha=.12)
    a.set_xscale('log'); a.set_xticks(C.V6_BUDGET_K); a.set_xticklabels(C.V6_BUDGET_K); a.set_xlabel('observations per source (random)'); a.set_title(met, loc='left')
axes[0].legend(fontsize=7, frameon=False)
fig.suptitle('v6f: observation-budget curves (S3, 31 sources, LOSO OOF scores; median and 95% of 500 draws)', x=.01, ha='left')
fig.savefig(FG/'v6f_budget_curves.png'); plt.close(fig)

prim = bE[bE.comparison.str.contains(' - ') & (bE['name'] == 'H_R+T-LR')].set_index('metric')
progress('v6_analysis', f"PRIMARY frozen external E: H_R+T-LR - H_R-LR source AUC {prim.loc['source_AUC','point']:+.3f} "
         f"[{prim.loc['source_AUC','ci2_5']:+.3f},{prim.loc['source_AUC','ci97_5']:+.3f}], source BA "
         f"{prim.loc['source_balanced_accuracy','point']:+.3f} [{prim.loc['source_balanced_accuracy','ci2_5']:+.3f},{prim.loc['source_balanced_accuracy','ci97_5']:+.3f}]")
print(f'total {time.time()-T0:.0f} s')
