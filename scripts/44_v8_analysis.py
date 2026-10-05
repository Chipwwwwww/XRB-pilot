"""v8 analysis (preregistration_v8.md sec. 3-5).
v8a: S1 hard-like (v7a states), existing OOF; PRIMARY hard-like observation-level AUC, v5 H+T-LR - v2 H-LR. IC1.
v8b: external set X (v6 E + LMC X-1 + new dynamical BHs), frozen v6 models refitted on S1 (IC2);
     PRIMARY X hard-like observation-level AUC, H_R+T-LR - H_R-LR (testable if >= 3 BH and >= 3 NS sources).
v8c: event-mode HF features; LOSO inside S1-HF; PRIMARY S1-HF observation-level AUC, H+HF-LR - H-LR.
Stratified observation-level intervals: v7a procedure (v8lib.strat_boot, draws over the whole sample)."""
import os, sys, time
os.environ['XRB_VERSION'] = 'v8'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
import config as C
import v4lib as L, v5lib as L5, v7lib as L7, v8lib as L8
from plotstyle import plt, CLASS_COLOR, INK, INK2

T0 = time.time()
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400); pd.set_option('display.max_colwidth', 80)
RA, RB, RC = ROOT/'results/v8a', ROOT/'results/v8b', ROOT/'results/v8c'
FA, FB, FC = ROOT/'figures/v8a', ROOT/'figures/v8b', ROOT/'figures/v8c'
for p in (RA, RB, RC, FA, FB, FC): p.mkdir(parents=True, exist_ok=True)
TC = ['T1', 'T2', 'T3']; HFC = ['HF1', 'HF2', 'HF3']


def reps_R(z):                                   # identical to 30_v6_analysis.reps_R
    W = np.diff(z['edges']); ec = np.sqrt(z['edges'][:-1] * z['edges'][1:])
    band = lambda a, lo, hi: np.sum((a * W)[:, (ec >= lo) & (ec < hi)], 1)
    c = {k: band(z['rate'], *b) / band(z['pl2'], *b) for k, b in {'b1': (5, 7), 'b2': (7, 10), 'b3': (10, 16), 'b4': (16, 25.1)}.items()}
    return np.c_[c['b2'] / c['b1'], c['b4'] / c['b3']]


ROWS = []


def rec(part, analysis, name, metric, pt, bt, role='descriptive', **kw):
    r = dict(part=part, analysis=analysis, comparison=name, metric=metric, **L8.summarize(pt, bt), role=role, **kw)
    if ' - ' in name: r['verdict'] = L8.verdict(r); r['frac_first_better'] = float(np.nanmean(bt[np.isfinite(bt)] > 0)) if np.isfinite(bt).any() else np.nan
    ROWS.append(r); return r


def strat_record(part, analysis, oofs, groups, draws, pairs, strata, primary=None, prim_role='PRIMARY'):
    """oofs {name: frame}; pairs [(a, b)] -> a - b; strata to report. primary = (a, b, stratum)."""
    sb = {k: L8.strat_boot(v, groups, draws) for k, v in oofs.items()}
    for k, d in sb.items():
        for g in strata:
            if g in d:
                for j, m in enumerate(['obs_AUC', 'obs_balanced_accuracy']):
                    rec(part, analysis + f' | {g}', k, m, d[g][0][j], d[g][1][:, j])
    for a, b in pairs:
        for g in strata:
            if g in sb[a] and g in sb[b]:
                for j, m in enumerate(['obs_AUC', 'obs_balanced_accuracy']):
                    role = prim_role if (primary == (a, b, g) and m == 'obs_AUC') else 'descriptive'
                    rec(part, analysis + f' | {g}', f'{a} - {b}', m, sb[a][g][0][j] - sb[b][g][0][j], sb[a][g][1][:, j] - sb[b][g][1][:, j], role=role)
    return sb


def src_record(part, analysis, oofs, ref):
    b = L.paired_bootstrap(oofs, ref); b['part'] = part; b['analysis'] = analysis + ' | source level (restricted OOF)'
    for r in b.to_dict('records'):
        r.setdefault('role', 'descriptive'); ROWS.append(r)
    return b


def fill_loso(Xf, Tm, y, g, alg):
    """LOSO with train-fold median fill + missing indicator for the columns Tm (v5 rule); Xf columns used as they are."""
    s = np.full(len(y), np.nan)
    for src in np.unique(g):
        te = g == src; tr = ~te
        if Tm is not None:
            a, b = L5.fill_missing(Tm[tr], Tm[te]); Xtr, Xte = np.c_[Xf[tr], a], np.c_[Xf[te], b]
        else:
            Xtr, Xte = Xf[tr], Xf[te]
        s[te] = L.V4Model(alg).fit(Xtr, y[tr]).score(Xte)
    return s


def oof(idx, s, y, g, o, rep, name):
    return L.to_oof(idx, s, 0.5, y, g, o, rep, name)


# =========================================================================== v8a
st = pd.read_csv(ROOT/'results/v7a/states.csv', dtype={'obs_id': str})
stmap = st.set_index('obs_id').state
srcS1 = st.drop_duplicates('source_id').set_index('source_id').label.to_dict()
drawsS1 = L7.boot_draws(srcS1)
v2 = pd.read_csv(ROOT/'results/v2/oof_predictions_loso.csv', dtype={'obs_id': str})
v5 = pd.read_csv(ROOT/'results/v5/v5_oof_predictions.csv', dtype={'obs_id': str})
v6 = pd.read_csv(ROOT/'results/v6/v6_oof_predictions.csv', dtype={'obs_id': str})
V2 = lambda rep, alg: v2[(v2.representation == rep) & (v2.model == alg)]
V5 = lambda smp, nm: v5[(v5['sample'] == smp) & (v5['name'] == nm)]
V6 = lambda nm: v6[v6['name'] == nm]
A = {'H-LR': V2('H_colours', 'LogReg'), 'H-RF': V2('H_colours', 'RandomForest'), 'H+T-LR': V5('S1', 'H+T|LogReg'), 'H+T-RF': V5('S1', 'H+T|RandomForest'),
     'H+T*-LR': V6('H+T*-LR'), 'H+N-LR': V6('H+N-LR'), 'H+N+T-LR': V6('H+N+T-LR'), 'H+T1-LR': V6('H+T1-LR'), 'H+T2-LR': V6('H+T2-LR'), 'H+T3-LR': V6('H+T3-LR')}
for k, v in A.items(): assert len(v) == 456 and v.obs_id.nunique() == 456, k
S3 = ['soft-like', 'intermediate', 'hard-like']
sbA = strat_record('v8a', 'S1 existing OOF', A, stmap, drawsS1,
                   [('H+T-LR', 'H-LR'), ('H+T-RF', 'H-RF'), ('H+T*-LR', 'H-LR'), ('H+N+T-LR', 'H+N-LR'), ('H+T1-LR', 'H-LR'), ('H+T2-LR', 'H-LR'), ('H+T3-LR', 'H-LR')],
                   S3, primary=('H+T-LR', 'H-LR', 'hard-like'))
# IC1: reproduce v7a H-LR hard-like AUC and interval exactly
v7a = pd.read_csv(ROOT/'results/v7a/state_stratified_metrics.csv')
ref = v7a[(v7a.analysis == 'v2 OOF') & (v7a.model == 'H-LR') & (v7a.group == 'hard-like') & (v7a.metric == 'obs_AUC')].iloc[0]
mine = L8.summarize(sbA['H-LR']['hard-like'][0][0], sbA['H-LR']['hard-like'][1][:, 0])
ic1 = dict(check='IC1 v2 H-LR hard-like obs AUC = v7a', v7a=(ref.point, ref.ci2_5, ref.ci97_5), v8=(mine['point'], mine['ci2_5'], mine['ci97_5']),
           passed=bool(np.allclose([ref.point, ref.ci2_5, ref.ci97_5], [mine['point'], mine['ci2_5'], mine['ci97_5']], atol=1e-12)))
print('IC1:', ic1, flush=True)
if not ic1['passed']: print('IC1 FAILED -> stop'); sys.exit(3)
# difference in differences (soft - hard gap), H+T-LR vs H-LR, and RF
for a, b in (('H+T-LR', 'H-LR'), ('H+T-RF', 'H-RF')):
    ga = sbA[a]['soft-like'][1][:, 0] - sbA[a]['hard-like'][1][:, 0]; gb = sbA[b]['soft-like'][1][:, 0] - sbA[b]['hard-like'][1][:, 0]
    pa = sbA[a]['soft-like'][0][0] - sbA[a]['hard-like'][0][0]; pb = sbA[b]['soft-like'][0][0] - sbA[b]['hard-like'][0][0]
    rec('v8a', 'S1 existing OOF | soft-like - hard-like gap', f'{a} gap', 'obs_AUC', pa, ga)
    rec('v8a', 'S1 existing OOF | difference in differences', f'{a} gap - {b} gap', 'obs_AUC', pa - pb, ga - gb)
# burst-excluded v5 OOF (S1 burst-excluded: H+T|LogReg vs H|LogReg)
strat_record('v8a', 'S1 burst-excluded (v5)', {'H+T-LR (burst-excl.)': V5('S1 burst-excluded', 'H+T|LogReg'), 'H-LR (burst-excl.)': V5('S1 burst-excluded', 'H|LogReg')},
             stmap, drawsS1, [('H+T-LR (burst-excl.)', 'H-LR (burst-excl.)')], ['hard-like'])
# source level within hard-like
hard = set(st[st.state == 'hard-like'].obs_id)
src_record('v8a', 'S1 hard-like', {'H-LR': A['H-LR'][A['H-LR'].obs_id.isin(hard)], 'H+T-LR': A['H+T-LR'][A['H+T-LR'].obs_id.isin(hard)]}, 'H-LR')
# trained on hard-like observations only (LOSO inside hard-like)
z = np.load(ROOT/'data/v2/processed/features.npz')
H_all = L.v2_representations(z['rate'], z['edges'], z['F'])['H_colours']; HR_all = reps_R(z)
y_all, g_all, o_all = z['y'], z['source_id'], z['obs_id']
T5 = pd.concat([pd.read_csv(ROOT/'data/v5/processed/timing_features.csv', dtype={'obs_id': str}),
                pd.read_csv(ROOT/'data/v6/processed/timing_v5_new.csv', dtype={'obs_id': str})]).drop_duplicates('obs_id').set_index('obs_id')
T_all = T5.reindex(o_all)[TC].values.astype(float)
mh = np.isin(o_all, list(hard)); ih = np.where(mh)[0]
s_h = fill_loso(H_all[mh], None, y_all[mh], g_all[mh], 'LogReg'); s_ht = fill_loso(H_all[mh], T_all[mh], y_all[mh], g_all[mh], 'LogReg')
ho = {'H-LR [hard-only]': oof(ih, s_h, y_all, g_all, o_all, 'H', 'H-LR [hard-only]'), 'H+T-LR [hard-only]': oof(ih, s_ht, y_all, g_all, o_all, 'H+T', 'H+T-LR [hard-only]')}
v7h = pd.read_csv(ROOT/'results/v7a/hard_only_oof.csv', dtype={'obs_id': str})
v7h = v7h[v7h.name == 'H-LR [hard-like only, trained on hard-like]'].set_index('obs_id').BH_score
print('hard-only H-LR reproduces v7a 2f: max diff', float((ho['H-LR [hard-only]'].set_index('obs_id').BH_score - v7h).abs().max()), flush=True)
strat_record('v8a', 'S1 trained on hard-like only', ho, stmap, drawsS1, [('H+T-LR [hard-only]', 'H-LR [hard-only]')], ['hard-like'])
pd.concat([v.assign(name=k) for k, v in ho.items()]).to_csv(RA/'v8a_hard_only_oof.csv', index=False)
print(f'v8a done ({time.time() - T0:.0f} s)', flush=True)

# =========================================================================== v8b
X = pd.read_csv(ROOT/'data/v8b/processed/external_states_timing.csv', dtype={'obs_id': str})
feats = {}
for v in ('v4b2', 'v6', 'v7b2', 'v8b'):
    zz = np.load(ROOT/f'data/{v}/processed/features.npz')
    for o, hr, yy in zip(zz['obs_id'], reps_R(zz), zz['y']): feats.setdefault(str(o), (hr, int(yy)))
X = X[X.obs_id.isin(feats)].reset_index(drop=True)
HRX = np.array([feats[o][0] for o in X.obs_id]); yX = np.array([feats[o][1] for o in X.obs_id]); gX = X.source_id.values; oX = X.obs_id.values
assert (yX == (X.label == 'BH').astype(int).values).all()
Tf_S1, Tf_X = L5.fill_missing(T_all, X[TC].values.astype(float))
fro = {'H_R-LR': L.V4Model('LogReg').fit(HR_all, y_all), 'H_R+T-LR': L.V4Model('LogReg').fit(np.c_[HR_all, Tf_S1], y_all)}
sX = {'H_R-LR': fro['H_R-LR'].score(HRX), 'H_R+T-LR': fro['H_R+T-LR'].score(np.c_[HRX, Tf_X])}
OX = {k: oof(np.arange(len(yX)), s, yX, gX, oX, 'H_R', k).assign(role=X.role.values, state=X.state.values, sample=X['sample'].values) for k, s in sX.items()}
pd.concat([v.assign(name=k) for k, v in OX.items()]).to_csv(RB/'v8b_external_scores.csv', index=False)
# IC2: E scores equal v6a
v6e = pd.read_csv(ROOT/'results/v6/v6a_external_scores.csv', dtype={'obs_id': str})
ic2 = []
for k in sX:
    a = OX[k].set_index('obs_id').BH_score; b = v6e[v6e.name == k].set_index('obs_id').BH_score
    cm = a.index.intersection(b.index); ic2.append(dict(model=k, n_common=len(cm), n_v6=len(b), max_abs_diff=float((a[cm] - b[cm]).abs().max())))
ic2 = pd.DataFrame(ic2); ic2['passed'] = (ic2.max_abs_diff < 1e-9) & (ic2.n_common == ic2.n_v6)
print('IC2:\n' + ic2.to_string(index=False), flush=True)
if not ic2.passed.all(): print('IC2 FAILED -> stop'); sys.exit(3)
nonstress = X.role != 'stress_slow_pulsar'
srcX = X[nonstress].drop_duplicates('source_id').set_index('source_id').label.to_dict()
drawsX = L7.boot_draws(srcX)
xmap = X[nonstress].set_index('obs_id').state
hx = X[nonstress & (X.state == 'hard-like')]
nbh, nns = hx[hx.label == 'BH'].source_id.nunique(), hx[hx.label == 'NS'].source_id.nunique()
testable = nbh >= C.V8_MIN_SOURCES_PER_CLASS and nns >= C.V8_MIN_SOURCES_PER_CLASS
print(f'X hard-like: {len(hx)} obs, {nbh} BH / {nns} NS sources -> testable {testable}', flush=True)
OXn = {k: v[nonstress.values] for k, v in OX.items()}
sbB = strat_record('v8b', 'X frozen v6 models', OXn, xmap, drawsX, [('H_R+T-LR', 'H_R-LR')], S3, primary=('H_R+T-LR', 'H_R-LR', 'hard-like') if testable else None)
strat_record('v8b', 'X frozen v6 models, all states', OXn, pd.Series('all', index=xmap.index), drawsX, [('H_R+T-LR', 'H_R-LR')], ['all'])
hxo = set(hx.obs_id)
src_record('v8b', 'X hard-like', {k: v[v.obs_id.isin(hxo)] for k, v in OXn.items()}, 'H_R-LR')
per = pd.concat([v.assign(name=k) for k, v in OX.items()]).groupby(['role', 'source_id', 'true_label', 'state', 'name']).BH_score.agg(['mean', 'size']).unstack('name')
per.to_csv(RB/'v8b_per_source_state.csv'); print('\nX per source x state (mean score, n):\n' + per.round(2).to_string(), flush=True)
print(f'v8b done ({time.time() - T0:.0f} s)', flush=True)

# =========================================================================== v8c
def run_v8c():
    hf = pd.read_csv(ROOT/'data/v8c/processed/hf_features.csv', dtype={'obs_id': str})
    okS1 = hf[(hf['sample'] == 'S1') & (hf.status == 'ok')].set_index('obs_id')
    m = np.isin(o_all, okS1.index); ic = np.where(m)[0]
    HFm = okS1.reindex(o_all[m])[HFC].values.astype(float)
    yc, gc = y_all[m], g_all[m]
    print(f'\nS1-HF: {m.sum()} obs, {len(set(gc))} sources ({len(set(gc[yc == 1]))} BH)', flush=True)
    specs = {'H-LR': (H_all[m], None, 'LogReg'), 'H+HF-LR': (np.c_[H_all[m], HFm], None, 'LogReg'), 'H+T-LR': (H_all[m], T_all[m], 'LogReg'),
             'H+T+HF-LR': (np.c_[H_all[m], HFm], T_all[m], 'LogReg'), 'HF-LR': (HFm, None, 'LogReg'),
             'H-RF': (H_all[m], None, 'RandomForest'), 'H+HF-RF': (np.c_[H_all[m], HFm], None, 'RandomForest'),
             'H+T-RF': (H_all[m], T_all[m], 'RandomForest'), 'H+T+HF-RF': (np.c_[H_all[m], HFm], T_all[m], 'RandomForest')}
    res = Parallel(n_jobs=9)(delayed(fill_loso)(Xf, Tm, yc, gc, alg) for Xf, Tm, alg in specs.values())
    OC = {k: oof(ic, s, y_all, g_all, o_all, 'S1-HF', k) for k, s in zip(specs, res)}
    pd.concat([v.assign(name=k) for k, v in OC.items()]).to_csv(RC/'v8c_oof_predictions.csv', index=False)
    cmap = pd.Series('S1-HF', index=okS1.index)
    strat_record('v8c', 'S1-HF LOSO', OC, cmap, drawsS1,
                 [('H+HF-LR', 'H-LR'), ('H+T+HF-LR', 'H+T-LR'), ('H+T-LR', 'H-LR'), ('HF-LR', 'H-LR'), ('H+HF-RF', 'H-RF'), ('H+T+HF-RF', 'H+T-RF')],
                 ['S1-HF'], primary=('H+HF-LR', 'H-LR', 'S1-HF'), prim_role='PRIMARY (exploratory: IC4 failed)')
    src_record('v8c', 'S1-HF', {k: OC[k] for k in ('H-LR', 'H+HF-LR', 'H+T-LR', 'H+T+HF-LR', 'HF-LR')}, 'H-LR')
    # excluding the AMXPs (retrained)
    na = ~np.isin(gc, C.V8_AMXP); ina = ic[na]
    res2 = Parallel(n_jobs=4)(delayed(fill_loso)(Xf[na], None if Tm is None else Tm[na], yc[na], gc[na], alg)
                              for k, (Xf, Tm, alg) in specs.items() if k in ('H-LR', 'H+HF-LR', 'H+T-LR', 'H+T+HF-LR'))
    OCa = {k + ' [no AMXP]': oof(ina, s, y_all, g_all, o_all, 'S1-HF', k) for k, s in zip(('H-LR', 'H+HF-LR', 'H+T-LR', 'H+T+HF-LR'), res2)}
    strat_record('v8c', 'S1-HF LOSO without AMXPs', OCa, cmap, drawsS1,
                 [('H+HF-LR [no AMXP]', 'H-LR [no AMXP]'), ('H+T+HF-LR [no AMXP]', 'H+T-LR [no AMXP]')], ['S1-HF'])
    # SR2000-type description: per-source inverse-variance mean of the HF3 variance
    allok = hf[hf.status == 'ok'].copy()
    rows = []
    for (smp, sid, lab), d in allok.groupby(['sample', 'source_id', 'label']):
        w = 1.0 / d.HF3_se.values ** 2
        for b in ('HF1', 'HF2', 'HF3'):
            wb = 1.0 / d[f'{b}_se'].values ** 2; mu = float((d[f'{b}_var'] * wb).sum() / wb.sum()); se = float(1.0 / np.sqrt(wb.sum()))
            rows.append(dict(sample=smp, source_id=sid, label=lab, band=b, n_obs=len(d), var_mean=mu, var_se=se, z=mu / se,
                             rms=float(np.sign(mu) * np.sqrt(abs(mu))), rms_3sigma_upper=float(np.sqrt(max(mu, 0) + 3 * se))))
    sr = pd.DataFrame(rows); sr.to_csv(RC/'v8c_per_source_hf.csv', index=False)
    h3 = sr[(sr.band == 'HF3') & (sr['sample'] == 'S1')].copy(); h3['SR2000_call'] = np.where(h3.z > 3, 'NS', 'BH')
    print('\nSR2000-type rule on S1-HF sources (HF3 detected at > 3 sigma -> NS):\n' + h3[['source_id', 'label', 'n_obs', 'rms', 'z', 'SR2000_call']].round(3).to_string(index=False))
    acc = pd.crosstab(h3.label, h3.SR2000_call); print(acc.to_string(), flush=True)
    h3.to_csv(RC/'v8c_sr2000_rule_S1.csv', index=False)
    # external frozen test: H_R-LR and H_R+HF-LR fitted on S1-HF, applied to X-HF (non-stress)
    okX = hf[(hf['sample'] == 'X') & (hf.status == 'ok') & (hf.role != 'stress_slow_pulsar')]
    okX = okX[okX.obs_id.isin(feats)]
    HRx = np.array([feats[o][0] for o in okX.obs_id]); yx = okX.label.eq('BH').astype(int).values
    fz = {'H_R-LR [S1-HF]': L.V4Model('LogReg').fit(HR_all[m], yc), 'H_R+HF-LR [S1-HF]': L.V4Model('LogReg').fit(np.c_[HR_all[m], HFm], yc)}
    sx = {'H_R-LR [S1-HF]': fz['H_R-LR [S1-HF]'].score(HRx), 'H_R+HF-LR [S1-HF]': fz['H_R+HF-LR [S1-HF]'].score(np.c_[HRx, okX[HFC].values.astype(float)])}
    OXc = {k: oof(np.arange(len(yx)), s, yx, okX.source_id.values, okX.obs_id.values, 'H_R', k) for k, s in sx.items()}
    pd.concat([v.assign(name=k) for k, v in OXc.items()]).to_csv(RC/'v8c_external_scores.csv', index=False)
    print(f"\nX-HF (non-stress): {len(okX)} obs, {okX[okX.label == 'BH'].source_id.nunique()} BH / {okX[okX.label == 'NS'].source_id.nunique()} NS sources", flush=True)
    strat_record('v8c', 'X-HF frozen (fitted on S1-HF)', OXc, pd.Series('X-HF', index=okX.obs_id.values), drawsX, [('H_R+HF-LR [S1-HF]', 'H_R-LR [S1-HF]')], ['X-HF'])
    # ---- POST HOC (decision_log, after the v8c results): a white cross-PCU component (seen in the 1536-2048 Hz null band, e.g.
    # 4U 1323-619) is subtracted from every band in proportion to its width: HFk_c = HFk - NULL * (width_k / width_NULL) ----
    J = C.V8_HF_BANDS_J; wN = J['NULL'][1] - J['NULL'][0] + 1
    hfc = hf[hf.status == 'ok'].copy()
    for b in HFC:
        wk = (J[b][1] - J[b][0] + 1) / wN
        hfc[f'{b}c_var'] = hfc[f'{b}_var'] - wk * hfc.NULL_var; hfc[f'{b}c_se'] = np.sqrt(hfc[f'{b}_se'] ** 2 + (wk * hfc.NULL_se) ** 2)
        hfc[f'{b}c'] = np.sign(hfc[f'{b}c_var']) * np.sqrt(np.abs(hfc[f'{b}c_var']))
    hfc.to_csv(RC/'v8c_hf_null_subtracted.csv', index=False)
    rows = []
    for (smp, sid, lab), d in hfc.groupby(['sample', 'source_id', 'label']):
        for b in HFC:
            wb = 1.0 / d[f'{b}c_se'].values ** 2; mu = float((d[f'{b}c_var'] * wb).sum() / wb.sum()); se = float(1.0 / np.sqrt(wb.sum()))
            rows.append(dict(sample=smp, source_id=sid, label=lab, band=b + 'c', n_obs=len(d), var_mean=mu, var_se=se, z=mu / se,
                             rms=float(np.sign(mu) * np.sqrt(abs(mu)))))
    src = pd.DataFrame(rows); src.to_csv(RC/'v8c_per_source_hf_null_subtracted.csv', index=False)
    h3c = src[src.band == 'HF3c'].copy(); h3c['SR2000_call'] = np.where(h3c.z > 3, 'NS', 'BH')
    h3c.to_csv(RC/'v8c_sr2000_rule_null_subtracted.csv', index=False)
    print('\n[post hoc] SR2000-type rule with the null band subtracted (HF3 - NULL, equal widths; > 3 sigma -> NS):\n'
          + h3c[['sample', 'source_id', 'label', 'n_obs', 'rms', 'z', 'SR2000_call']].round(3).to_string(index=False))
    for smp in ('S1', 'X'):
        print(smp, '\n' + pd.crosstab(h3c[h3c['sample'] == smp].label, h3c[h3c['sample'] == smp].SR2000_call).to_string())
    HFcm = hfc.set_index('obs_id').reindex(o_all[m])[[b + 'c' for b in HFC]].values.astype(float)
    sp2 = {'H+HFc-LR [post hoc]': (np.c_[H_all[m], HFcm], None, 'LogReg'), 'H+HFc-RF [post hoc]': (np.c_[H_all[m], HFcm], None, 'RandomForest'),
           'H+T+HFc-LR [post hoc]': (np.c_[H_all[m], HFcm], T_all[m], 'LogReg'), 'H+T+HFc-RF [post hoc]': (np.c_[H_all[m], HFcm], T_all[m], 'RandomForest')}
    r3 = Parallel(n_jobs=4)(delayed(fill_loso)(Xf, Tm, yc, gc, alg) for Xf, Tm, alg in sp2.values())
    OCp = {k: oof(ic, s_, y_all, g_all, o_all, 'S1-HF', k) for k, s_ in zip(sp2, r3)}
    pd.concat([v.assign(name=k) for k, v in OCp.items()]).to_csv(RC/'v8c_oof_predictions_post_hoc.csv', index=False)
    OCp.update({k: OC[k] for k in ('H-LR', 'H-RF', 'H+T-LR', 'H+T-RF')})
    strat_record('v8c', 'S1-HF LOSO, null-subtracted HF [post hoc]', OCp, cmap, drawsS1,
                 [('H+HFc-LR [post hoc]', 'H-LR'), ('H+HFc-RF [post hoc]', 'H-RF'), ('H+T+HFc-LR [post hoc]', 'H+T-LR'), ('H+T+HFc-RF [post hoc]', 'H+T-RF')], ['S1-HF'])
    coef = fz['H_R+HF-LR [S1-HF]'].m.coef_[0]
    print('frozen H_R+HF-LR coefficients [c1, c2, HF1, HF2, HF3] (standardised):', np.round(coef, 3), flush=True)


if os.environ.get('V8_SKIP_HF') != '1': run_v8c()

# =========================================================================== output
out = pd.DataFrame(ROWS)
for part, R_ in (('v8a', RA), ('v8b', RB), ('v8c', RC)):
    if (out.part == part).any(): out[out.part == part].to_csv(R_/f'{part}_metrics.csv', index=False)
t = out[out.comparison.astype(str).str.contains(' - ') & out.metric.isin(['obs_AUC', 'source_AUC', 'source_balanced_accuracy'])].copy()
t['txt'] = t.apply(lambda r: f"{r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]" + (' *' if str(r.get('role')).startswith('PRIMARY') else ''), axis=1)
print('\n' + t.pivot_table(index=['part', 'analysis', 'comparison'], columns='metric', values='txt', aggfunc='first').to_string())
p = out[(out.part.isin(['v8a', 'v8b', 'v8c'])) & ~out.comparison.astype(str).str.contains(' - ') & (out.metric == 'obs_AUC')]
print('\n' + p.assign(txt=p.apply(lambda r: f"{r.point:.3f} [{r.ci2_5:.3f},{r.ci97_5:.3f}]", axis=1))
      .pivot_table(index=['part', 'analysis'], columns='comparison', values='txt', aggfunc='first').to_string())
out.loc[out.role.astype(str).str.contains('exploratory'), 'verdict'] = 'exploratory only (IC4 failed; no confirmatory claim)'
prim = out[out.role.astype(str).str.startswith('PRIMARY')]
for r in prim.itertuples(): print(f'PRIMARY {r.part} {r.analysis} {r.comparison} {r.metric}: {r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}] -> {r.verdict}')
progress('v8_analysis', '; '.join(f'{r.part} {r.point:+.3f} [{r.ci2_5:+.3f},{r.ci97_5:+.3f}]' for r in prim.itertuples()))
print(f'total {time.time() - T0:.0f} s')
