"""v7c1 (preregistration_v7.md §6, 4b): faithful reproduction of de Beurs et al. 2022 (arXiv:2204.00346) with their
published inputs: GitHub zdebeurs/3ML_methods_for_XRB_classification, pinned to its current commit; the ten 20% subsamples
D1-D10 (44 .asc files each: System, Type, Date, CC3=RelInt, CC1=SC, CC2=HC). Three classes (1 BH incl. their BH
candidates, 2 NPNS = Atoll/Zsource/Burster, 3 Pulsar) exactly as their R code. LOSO over the 44 systems per subsample;
KNN k=24 on raw features (caret knn3Train equivalent: vote fractions); SVM RBF C=0.655298, gamma=0.585144 on
training-standardised features (e1071 svm default scale=TRUE), Platt probabilities (random_state=42).
Per source: mean probability over its rows -> median (and sd) over the 10 subsamples -> argmax.
Success (preregistered): overall correct within 2 sources of the paper (KNN 37/44, SVM 36/44) and BH correct within 1
(KNN 6/12, SVM 5/12). Also compared per source with their published SVM medians."""
import os, sys, json, urllib.request
os.environ['XRB_VERSION'] = 'v7c'
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, download, progress
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
import config as C

R7, D7 = ROOT/'results/v7c', ROOT/'data/v7c'
for p in (R7, D7): p.mkdir(parents=True, exist_ok=True)
REPO = 'zdebeurs/3ML_methods_for_XRB_classification'
api = lambda u: json.loads(urllib.request.urlopen(u, timeout=60).read())
sha = api(f'https://api.github.com/repos/{REPO}/commits/main')['sha']
tree = api(f'https://api.github.com/repos/{REPO}/git/trees/{sha}?recursive=1')['tree']
want = [t['path'] for t in tree if t['type'] == 'blob' and (
    (t['path'].startswith('10_sampled20Perc_Datasets/D') and t['path'].endswith('.asc')) or t['path'].startswith('Training_and_Testing/')
    and t['path'].endswith('.asc') or t['path'] in ('ref_order.csv', 'SVM_methods/10_runs_med_sd_SVM_2022-05-24.csv', 'LICENSE'))]
print('commit', sha, '|', len(want), 'files', flush=True)
json.dump(dict(repo=REPO, commit=sha, n_files=len(want)), open(D7/'debeurs_repo_pin.json', 'w'), indent=1)
Parallel(n_jobs=8, prefer='threads')(delayed(download)(f'https://raw.githubusercontent.com/{REPO}/{sha}/' + urllib.parse.quote(p),
                                                      f'data/raw/debeurs/{p}') for p in want)
COLS = ['System', 'Type', 'Date', 'CC3', 'CC1', 'CC2']


def load_sub(k):
    d = ROOT/f'data/raw/debeurs/10_sampled20Perc_Datasets/D{k}_Sampled_20percent_Training_and_Testing'
    return {f.stem: pd.read_csv(f, sep=r'\s+', header=None, names=COLS) for f in sorted(d.glob('*.asc'))}


def cls(types):
    t = pd.Series(types); c = np.ones(len(t), int)
    c[t.isin(['Atoll', 'Zsource', 'Burster']).values] = 2; c[(t == 'Pulsar').values] = 3
    return c


def fold(k, test, alg):
    sub = load_sub(k)
    tr = pd.concat([v for s, v in sub.items() if s != test]); te = sub[test]
    Xtr, Xte = tr[['CC3', 'CC1', 'CC2']].values, te[['CC3', 'CC1', 'CC2']].values; ytr = cls(tr.Type)
    if alg == 'KNN':
        m = KNeighborsClassifier(n_neighbors=C.V7_DEBEURS_KNN_K).fit(Xtr, ytr); P = m.predict_proba(Xte)
    else:
        sc = StandardScaler().fit(Xtr)
        m = SVC(kernel='rbf', C=0.655298078515272, gamma=0.585144090708118, probability=True, random_state=C.SEED).fit(sc.transform(Xtr), ytr)
        P = m.predict_proba(sc.transform(Xte))
    p = dict(zip(m.classes_, P.mean(0)))
    return dict(run=k, system=test, alg=alg, true_class=int(cls(te.Type)[0]), type=te.Type.iloc[0], n_rows=len(te),
                p_BH=p.get(1, 0.0), p_NPNS=p.get(2, 0.0), p_Pulsar=p.get(3, 0.0))


systems = sorted(load_sub(1))
types = pd.concat([v.Type for v in load_sub(1).values()]).value_counts(); print(types.to_string(), flush=True)
tasks = [(k, s, a) for a in ('KNN', 'SVM') for k in range(1, 11) for s in systems]
res = pd.DataFrame(Parallel(n_jobs=16, verbose=2)(delayed(fold)(*t) for t in tasks)); res.to_csv(R7/'v7c1_fold_predictions.csv', index=False)
agg = res.groupby(['alg', 'system']).agg(true_class=('true_class', 'first'), type=('type', 'first'),
                                          p_BH=('p_BH', 'median'), sd_BH=('p_BH', 'std'), p_NPNS=('p_NPNS', 'median'), sd_NPNS=('p_NPNS', 'std'),
                                          p_Pulsar=('p_Pulsar', 'median'), sd_Pulsar=('p_Pulsar', 'std')).reset_index()
P = agg[['p_BH', 'p_NPNS', 'p_Pulsar']].values; S = agg[['sd_BH', 'sd_NPNS', 'sd_Pulsar']].values
agg['pred_class'] = P.argmax(1) + 1
o = np.argsort(-P, 1); r_ = np.arange(len(P))
agg['indeterminate_1sigma'] = np.abs(P[r_, o[:, 0]] - P[r_, o[:, 1]]) <= S[r_, o[:, 0]] + S[r_, o[:, 1]]
agg['correct'] = agg.pred_class == agg.true_class
agg.to_csv(R7/'v7c1_source_predictions.csv', index=False)
PAPER = {'KNN': dict(total=37, BH=6), 'SVM': dict(total=36, BH=5)}
rows = []
for a, d in agg.groupby('alg'):
    n = d.groupby('true_class').correct.agg(['sum', 'size'])
    tot, bh = int(d.correct.sum()), int(n.loc[1, 'sum'])
    rows.append(dict(alg=a, correct=tot, of=len(d), accuracy=tot / len(d), BH_correct=bh, BH_of=int(n.loc[1, 'size']),
                     NPNS_correct=int(n.loc[2, 'sum']), Pulsar_correct=int(n.loc[3, 'sum']), indeterminate=int(d.indeterminate_1sigma.sum()),
                     paper_total=PAPER[a]['total'], paper_BH=PAPER[a]['BH'],
                     reproduced=abs(tot - PAPER[a]['total']) <= C.V7_REPRO_TOL_SOURCES and abs(bh - PAPER[a]['BH']) <= C.V7_REPRO_TOL_BH))
rep = pd.DataFrame(rows); rep.to_csv(R7/'v7c1_reproduction.csv', index=False)
print('\n' + rep.to_string(index=False))
pub = pd.read_csv(ROOT/'data/raw/debeurs/SVM_methods/10_runs_med_sd_SVM_2022-05-24.csv')
m = agg[agg.alg == 'SVM'].merge(pub[['systems', 'blackhole_prob', 'non_pulsar_prob', 'pulsar_prob']], left_on='system', right_on='systems')
m['pub_pred'] = m[['blackhole_prob', 'non_pulsar_prob', 'pulsar_prob']].values.argmax(1) + 1
cmp = dict(n=len(m), spearman_pBH=spearmanr(m.p_BH, m.blackhole_prob)[0], max_abs_diff_pBH=float((m.p_BH - m.blackhole_prob).abs().max()),
           argmax_agreement=float((m.pred_class == m.pub_pred).mean()), pub_correct=int((m.pub_pred == m.true_class).sum()))
pd.DataFrame([cmp]).to_csv(R7/'v7c1_vs_published_svm.csv', index=False)
print('\nSVM vs published per-source medians:', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in cmp.items()})
print(m[m.pred_class != m.pub_pred][['system', 'true_class', 'p_BH', 'p_NPNS', 'p_Pulsar', 'blackhole_prob', 'non_pulsar_prob', 'pulsar_prob']].round(3).to_string(index=False))
print('\nper source (BH class):\n' + agg[agg.true_class == 1].pivot_table(index='system', columns='alg', values=['p_BH', 'pred_class']).round(3).to_string())
progress('v7c1_repro', '; '.join(f"{r.alg} {r.correct}/{r.of} (BH {r.BH_correct}/{r.BH_of}) reproduced={r.reproduced}" for r in rep.itertuples()))
if not rep.reproduced.all():
    print('REPRODUCTION OUTSIDE TOLERANCE -> stop (preregistration_v7 4b)'); sys.exit(3)
