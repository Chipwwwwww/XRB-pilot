"""v6 methods (preregistration_v6.md §3-6).
- all-pairs cospectrum estimator (+ single-PCU auto-power hybrid) and the nuPnu centroid frequency nu_c
- CCTLR: colour-conditional timing likelihood-ratio classifier = H-LR logit + Student-t log p(T|H,BH)/p(T|H,NS)
- colour-conditional source-permutation test, source-level conformal prediction sets, proper-score bootstrap,
  observation-budget curves."""
import numpy as np, pandas as pd
from scipy.stats import t as student_t, rankdata
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
import config as C
import v4lib as L
import v5lib as L5

N, DT, SINC2, BANDS = L5.N, L5.DT, L5.SINC2, L5.BANDS
_e = np.unique(np.round(np.geomspace(1, N // 2, C.V6_NLOGBINS + 1)).astype(int))
LOGBINS = [(int(a), int(b) - 1) for a, b in zip(_e[:-1], _e[1:])]                 # inclusive Fourier index ranges
NU_B = np.array([np.sqrt(a * b) / (N * DT) for a, b in LOGBINS])                    # geometric centre (Hz)
DLN = np.array([np.log((b + 0.5) / (a - 0.5)) for a, b in LOGBINS])                # bin width in ln(nu)


# ------------------------------------------------------------------ estimators
def _bands(c):
    out = {k: 2.0 / N**2 * c[a:b + 1].sum() for k, (a, b) in BANDS.items()}
    out.update({f'lb{i}': 2.0 / N**2 * c[a:b + 1].sum() for i, (a, b) in enumerate(LOGBINS)})
    return out


def allpairs_row(row5, b_pcu):
    """Fractional variances for one 128-s row: all-pairs cospectrum if >= 2 PCUs on, else the single-PCU auto-power hybrid."""
    on = np.where(L5.pcus_on(row5))[0]
    if len(on) >= 2:
        x = row5[on]; s = x.mean(1) - b_pcu * DT
        if (s <= 0).any(): return None
        X = np.fft.rfft(x, axis=1); S = X.sum(0)
        cross = (np.abs(S) ** 2 - (np.abs(X) ** 2).sum(0)) / 2.0 / SINC2
        den = (s.sum() ** 2 - (s ** 2).sum()) / 2.0
        v = _bands(cross); kind = 'pairs'
    elif len(on) == 1:
        x = row5[on[0]]
        if x.mean() / DT > C.V6_AUTO_MAX_RATE: return None
        s = x.mean() - b_pcu * DT
        if s <= 0: return None
        Z = np.fft.rfft(x); p = (np.abs(Z) ** 2 - N * x.mean()) / SINC2
        den = s ** 2; v = _bands(p); kind = 'single'
    else:
        return None
    out = {k: val / den for k, val in v.items()}
    out.update(kind=kind, n_on=len(on))
    return out


def nu_centroid(lb, total_rms):
    """nuPnu centroid from log-bin fractional variances (medians over rows)."""
    if not np.isfinite(total_rms) or total_rms < C.V6_NUC_MIN_RMS: return np.nan
    w = np.maximum(np.asarray(lb, float), 0) / DLN
    if not np.isfinite(w).all() or w.sum() <= 0: return np.nan
    return float(np.exp((w * np.log(NU_B)).sum() / w.sum()))


def obs_timing_v6(obs_id, path_src, path_bkg):
    """T1*-T3*, T*_total, nu_c; split-half (odd/even rows) for T* and for the v5 A/B estimator (reliability check)."""
    rec = dict(obs_id=obs_id)
    try:
        s, bk = L5.read_pha(L5.fix(path_src)), L5.read_pha(L5.fix(path_bkg))
        cnt = bk['counts'].sum()
        rate = cnt if str(bk['unit']).lower().replace(' ', '').endswith('/s') else cnt / bk['exposure']
        b_pcu = rate / bk['npcu']
        rows = L5.std1_rows(obs_id, s['gti'])
        rr = [(i, allpairs_row(rows[:, i], b_pcu)) for i in range(rows.shape[1])]
        rr = [(i, f) for i, f in rr if f is not None]
        rec.update(n_rows_in_gti=rows.shape[1], n_rows_valid=len(rr), n_rows_pairs=sum(f['kind'] == 'pairs' for _, f in rr),
                   n_rows_single=sum(f['kind'] == 'single' for _, f in rr))
        if len(rr) < C.V5_MIN_ROWS:
            rec['status'] = f'missing (< {C.V5_MIN_ROWS} valid rows)'; return rec
        keys = [k for k in rr[0][1] if k not in ('kind', 'n_on')]
        med = {k: float(np.median([f[k] for _, f in rr])) for k in keys}
        for k in BANDS: rec[f'{k}s'] = float(L5.signed_sqrt(med[k]))
        rec['Ts_total'] = float(L5.signed_sqrt(sum(med[k] for k in BANDS)))
        rec['nu_c'] = nu_centroid([med[f'lb{i}'] for i in range(len(LOGBINS))], rec['Ts_total'])
        for i in range(len(LOGBINS)): rec[f'lb{i}'] = med[f'lb{i}']
        for half, sel in (('odd', 1), ('even', 0)):
            h = [f for i, f in rr if i % 2 == sel]
            if len(h) >= 2:
                for k in BANDS: rec[f'{k}s_{half}'] = float(L5.signed_sqrt(np.median([f[k] for f in h])))
            v5 = [L5.row_features(rows[:, i], b_pcu) for i, _ in rr if i % 2 == sel]
            v5 = [f for f in v5 if f is not None]
            if len(v5) >= 2:
                for k in BANDS: rec[f'{k}_v5_{half}'] = float(L5.signed_sqrt(np.median([f[f'f_{k}'] for f in v5])))
        rec['status'] = 'ok'
    except Exception as e:
        rec['status'] = f'error: {type(e).__name__}: {e}'[:200]
    return rec


# ------------------------------------------------------------------ CCTLR
def source_equal_within_class(y, g):
    w = np.empty(len(y))
    for c in (0, 1):
        srcs = np.unique(g[y == c])
        for s in srcs:
            m = g == s; w[m] = 1.0 / (len(srcs) * m.sum())
    return w


class CCTLR:
    """log-odds = H-LR logit + sum_k [log t4(T_k; mu_BH,k(H), s_BH,k) - log t4(T_k; mu_NS,k(H), s_NS,k)].
    mu_c,k linear in standardised H, fitted by weighted least squares with source-equal weights within each class.
    Missing timing (any T non-finite) -> timing term 0. lr_weight: None (balanced LR) or sample weights for the LR part."""

    def fit(self, H, T, y, g, lr_weight=None):
        y, g = np.asarray(y), np.asarray(g)
        self.sc = StandardScaler().fit(H); h = self.sc.transform(H)
        p = dict(C.LR_PARAMS)
        if lr_weight is not None: p['class_weight'] = None
        self.lr = LogisticRegression(**p).fit(h, y, sample_weight=lr_weight)
        ok = np.isfinite(T).all(1); Z = np.c_[np.ones(len(h)), h]
        w = source_equal_within_class(y[ok], g[ok])
        self.beta, self.sig = {}, {}
        for c in (0, 1):
            m = y[ok] == c; Zc, Tc, wc = Z[ok][m], T[ok][m], w[m]
            A = Zc.T @ (Zc * wc[:, None]); B = Zc.T @ (Tc * wc[:, None])
            self.beta[c] = np.linalg.solve(A + 1e-9 * np.eye(A.shape[0]), B)
            r = Tc - Zc @ self.beta[c]
            self.sig[c] = np.maximum(np.sqrt((wc[:, None] * r ** 2).sum(0) / wc.sum()), C.V6_SIGMA_FLOOR)
        return self

    def timing_llr(self, H, T):
        h = self.sc.transform(H); Z = np.c_[np.ones(len(h)), h]
        lam = np.zeros(len(h)); ok = np.isfinite(T).all(1)
        if ok.any():
            lp = {c: student_t.logpdf(T[ok], C.V6_T_DOF, loc=Z[ok] @ self.beta[c], scale=self.sig[c]).sum(1) for c in (0, 1)}
            lam[ok] = lp[1] - lp[0]
        return lam

    def score(self, H, T):
        return expit(self.lr.decision_function(self.sc.transform(H)) + self.timing_llr(H, T))


def cctlr_loso(H, T, y, g, folds, weighting=None):
    s = np.full(len(y), np.nan)
    for tr, te in folds:
        w = L.source_equal_weights(y[tr], g[tr]) if weighting == 'source_equal' else None
        s[te] = CCTLR().fit(H[tr], T[tr], y[tr], g[tr], w).score(H[te], T[te])
    return s


# ------------------------------------------------------------------ colour-conditional source-permutation test
def source_residuals(Hfit, Ffit, gfit, Happ=None, Fapp=None, gapp=None, k=None):
    """Residual of a feature after a label-free kNN regression on standardised colours.
    If Happ is None: leave-one-source-out within the fit set; else fit on all of the fit set and apply to Happ."""
    k = k or C.V6_KNN
    sc = StandardScaler().fit(Hfit)
    okf = np.isfinite(Ffit)
    if Happ is None:
        r = np.full(len(Ffit), np.nan)
        for s in np.unique(gfit[okf]):
            tr, te = okf & (gfit != s), okf & (gfit == s)
            m = KNeighborsRegressor(n_neighbors=min(k, tr.sum())).fit(sc.transform(Hfit[tr]), Ffit[tr])
            r[te] = Ffit[te] - m.predict(sc.transform(Hfit[te]))
        return pd.Series(r).groupby(gfit).mean()
    m = KNeighborsRegressor(n_neighbors=min(k, okf.sum())).fit(sc.transform(Hfit[okf]), Ffit[okf])
    oka = np.isfinite(Fapp); r = np.full(len(Fapp), np.nan)
    r[oka] = Fapp[oka] - m.predict(sc.transform(Happ[oka]))
    return pd.Series(r).groupby(gapp).mean()


def perm_test(src_resid, src_label, n_perm=None, seed=None):
    """D = mean source residual (BH) - mean (NS); null: permute source labels (fixed #BH). Two-sided p."""
    n_perm = n_perm or C.V6_N_PERM; rng = np.random.default_rng(C.SEED if seed is None else seed)
    s = src_resid.dropna(); lab = np.asarray(src_label.loc[s.index]); r = s.values
    D = r[lab == 1].mean() - r[lab == 0].mean(); nb = int(lab.sum())
    perms = np.array([rng.permutation(len(r)) for _ in range(n_perm)])
    ind = np.zeros((n_perm, len(r)), bool); np.put_along_axis(ind, perms[:, :nb], True, axis=1)
    Dp = (r[None, :] * ind).sum(1) / nb - (r[None, :] * ~ind).sum(1) / (len(r) - nb)
    p = (1 + (np.abs(Dp) >= abs(D) - 1e-15).sum()) / (1 + n_perm)
    return dict(D=float(D), p=float(p), n_sources=len(r), n_bh=nb, null_sd=float(Dp.std()))


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); adj = np.empty(len(ps)); run = 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


# ------------------------------------------------------------------ conformal prediction (source level, Mondrian)
def conformal_sets(cal_score, cal_y, test_score, eps):
    """cal_score/test_score: source mean BH probability. Nonconformity: BH -> 1 - s, NS -> s. Returns p_BH, p_NS, set."""
    cal_score, cal_y = np.asarray(cal_score, float), np.asarray(cal_y, int)
    a1, a0 = 1 - cal_score[cal_y == 1], cal_score[cal_y == 0]
    out = []
    for s in np.atleast_1d(test_score):
        p1 = (1 + (a1 >= 1 - s).sum()) / (1 + len(a1)); p0 = (1 + (a0 >= s).sum()) / (1 + len(a0))
        st = ('BH' if p1 > eps else '') + ('NS' if p0 > eps else '')
        out.append((p1, p0, {'BH': '{BH}', 'NS': '{NS}', 'BHNS': '{BH,NS}', '': '{}'}[st]))
    return out


def conformal_loso(src_score, src_y, eps):
    """Leave-one-source-out: each source's p-values use the other sources' OOF scores as calibration."""
    src_score, src_y = np.asarray(src_score, float), np.asarray(src_y, int); res = []
    for i in range(len(src_score)):
        m = np.arange(len(src_score)) != i
        res.append(conformal_sets(src_score[m], src_y[m], src_score[i], eps)[0])
    return res


# ------------------------------------------------------------------ proper scores with the v4lib bootstrap draws
def proper_score_bootstrap(oofs, ref, n_boot=None, seed=None):
    """Class-balanced source-level log loss and Brier (probabilities clipped); same draws as v4lib.paired_bootstrap.
    Lower is better; 'improvement' if the paired difference (model - ref) has its 95% CI entirely < 0."""
    n_boot = n_boot or C.N_BOOT; seed = C.SEED if seed is None else seed
    lo_, hi_ = C.V6_PROB_CLIP
    tabs = {k: L.src_table(v) for k, v in oofs.items()}; t0 = tabs[ref]
    bh = np.sort(t0.index[t0.true_label == 'BH'].values); ns = np.sort(t0.index[t0.true_label == 'NS'].values)
    rng = np.random.default_rng(seed)
    draws = [np.r_[rng.choice(bh, len(bh)), rng.choice(ns, len(ns))] for _ in range(n_boot)]
    order = np.r_[bh, ns]; isbh = np.r_[np.ones(len(bh), bool), np.zeros(len(ns), bool)]
    B, P, rows = {}, {}, []
    for k, t in tabs.items():
        t = t.loc[order]; p = np.clip(t.score.values, lo_, hi_)
        ll = np.where(isbh, -np.log(p), -np.log(1 - p)); br = np.where(isbh, (1 - p) ** 2, p ** 2)
        pos = {s: i for i, s in enumerate(order)}; idx = np.array([[pos[x] for x in d] for d in draws]); bm = isbh[idx]
        cb = lambda v: 0.5 * ((v[idx] * bm).sum(1) / bm.sum(1) + (v[idx] * ~bm).sum(1) / (~bm).sum(1))
        B[k] = np.c_[cb(ll), cb(br)]
        P[k] = np.array([0.5 * (ll[isbh].mean() + ll[~isbh].mean()), 0.5 * (br[isbh].mean() + br[~isbh].mean())])
        for j, n in enumerate(['source_logloss', 'source_brier']):
            rows.append(dict(name=k, comparison=k, metric=n, point=P[k][j], ci2_5=np.percentile(B[k][:, j], 2.5), ci97_5=np.percentile(B[k][:, j], 97.5)))
    for k in tabs:
        if k == ref: continue
        d = B[k] - B[ref]
        for j, n in enumerate(['source_logloss', 'source_brier']):
            lo, hi = np.percentile(d[:, j], 2.5), np.percentile(d[:, j], 97.5)
            rows.append(dict(name=k, comparison=f'{k} - {ref}', metric=n, point=P[k][j] - P[ref][j], ci2_5=lo, ci97_5=hi,
                             frac_first_better=float(np.mean(d[:, j] < 0)), verdict='improvement' if hi < 0 else 'not detected'))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ observation-budget curves
def budget_curves(oof, ks=None, draws=None, seed=None):
    ks = ks or C.V6_BUDGET_K; draws = draws or C.V6_BUDGET_DRAWS
    rng = np.random.default_rng(C.SEED if seed is None else seed)
    grp = {s: d.BH_score.values for s, d in oof.groupby('source_id')}
    lab = oof.groupby('source_id').true_label.first().loc[list(grp)].eq('BH').values
    rows = []
    for k in ks:
        ba, auc = [], []
        for _ in range(draws):
            sc = np.array([v[rng.choice(len(v), min(k, len(v)), replace=False)].mean() for v in grp.values()])
            pred = sc >= C.SOURCE_THRESHOLD
            ba.append(0.5 * (pred[lab].mean() + (~pred[~lab]).mean()))
            r = rankdata(sc); auc.append((r[lab].sum() - lab.sum() * (lab.sum() + 1) / 2) / (lab.sum() * (~lab).sum()))
        for n, v in (('source_balanced_accuracy', ba), ('source_AUC', auc)):
            rows.append(dict(k=k, metric=n, median=np.median(v), p2_5=np.percentile(v, 2.5), p97_5=np.percentile(v, 97.5)))
    return pd.DataFrame(rows)
