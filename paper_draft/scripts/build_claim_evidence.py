"""Build paper_draft/claim_evidence.csv and check every numeric claim of main.tex against committed files.

For each claim the script
  1. reads the committed source file(s) named in the row and selects the row(s) given by the filters;
  2. rounds the value(s) to the precision used in the paper and compares them with the numbers written in the claim;
  3. checks that every number of the claim also appears in paper_draft/main.tex.
Nothing is re-estimated: only committed CSV values (and simple counts of committed per-observation tables) are read.
Claims that cannot be checked from a file (literature, timestamps, definitions) are marked 'manual' with the evidence.

Run from the repository root:  python paper_draft/scripts/build_claim_evidence.py
"""
from pathlib import Path
import csv
import re
import subprocess
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TEX = (ROOT / 'paper_draft/main.tex').read_text(encoding='utf-8')
TEXN = TEX.replace('$', '').replace('{', ' ').replace('}', ' ').replace('\\ci', ' ').replace('--', '-')


def rd(path):
    p = ROOT / path
    return pd.read_csv(p, compression='infer', dtype={'obsid': str})


def pick(path, **flt):
    d = rd(path)
    m = np.ones(len(d), bool)
    for k, v in flt.items():
        m &= (d[k].astype(str) == str(v)).values
    r = d[m]
    if len(r) != 1:
        raise ValueError(f'{path} {flt}: {len(r)} rows')
    return r.iloc[0]


def triplet(path, cols=('point', 'ci2_5', 'ci97_5'), **flt):
    r = pick(path, **flt)
    return [float(r[c]) for c in cols]


CLAIMS = []


def claim(cid, section, text, values, source, selector, unit, role, limits, getter=None, dec=3):
    """values: numbers as written in the paper; getter: callable returning the same-length list from committed files."""
    CLAIMS.append(dict(claim_id=cid, section=section, claim=text, paper_values=values, source_file=source,
                       source_rows=selector, sample_and_unit=unit, role=role, required_limitations=limits,
                       getter=getter, dec=dec))


# ---------------------------------------------------------------------------------------------- colour baseline
V3A = 'results/v3/v3a_bootstrap.csv'
claim('C01', '4.1, abstract, conclusions', 'Two-colour LR source-level AUC on the RXTE development sample',
      [0.923, 0.804, 0.994], V3A, 'comparison=H_colours, model=LogReg, metric=source_AUC',
      '31 sources (7 BH/24 NS), 456 obs; LOSO; source-level AUC', 'baseline (v2 analysis; reported in v3a)',
      'source-level AUC, not accuracy; 7 BHs; source bootstrap of fixed predictions only',
      lambda: triplet(V3A, comparison='H_colours', model='LogReg', metric='source_AUC'))
claim('C02', '4.1', 'Two-colour LR source-level balanced accuracy', [0.795, 0.589, 0.958], V3A,
      'comparison=H_colours, model=LogReg, metric=source_balanced_accuracy', '31 sources; threshold 0.5 on mean score',
      'baseline', 'balanced accuracy at fixed threshold 0.5',
      lambda: triplet(V3A, comparison='H_colours', model='LogReg', metric='source_balanced_accuracy'))
claim('C03', '4.1', 'Two-colour LR observation-level balanced accuracy', [0.776, 0.633, 0.893], V3A,
      'comparison=H_colours, model=LogReg, metric=obs_balanced_accuracy', '456 obs; threshold 0.5', 'baseline',
      'observation-level; sources with more observations weigh more',
      lambda: triplet(V3A, comparison='H_colours', model='LogReg', metric='obs_balanced_accuracy'))
claim('C04', '4.1', 'Two-colour RF source-level AUC', [0.905, 0.750, 1.000], V3A,
      'comparison=H_colours, model=RandomForest, metric=source_AUC', '31 sources', 'baseline', 'as C01',
      lambda: triplet(V3A, comparison='H_colours', model='RandomForest', metric='source_AUC'))
claim('C05', '4.1', 'Sources correct under H-LR: 26 of 31 (5/7 BH, 21/24 NS); misclassified GRS 1915+105, XTE J1118+480, '
      'HETE J1900.1-2455, KS 1731-260, SAX J1808.4-3658', [26, 31], 'results/v2/metrics_source_level.csv',
      'representation=H_colours, model=LogReg', '31 sources', 'baseline', 'count at threshold 0.5',
      lambda: [int(pick('results/v2/metrics_source_level.csv', representation='H_colours', model='LogReg').sources_correct), 31], dec=0)
claim('C06', '4.1', 'H+B minus H, source-level AUC, LR (primary of v3a)', [-0.048, -0.179, 0.048], V3A,
      'comparison=H_plus_B - H_colours, model=LogReg, metric=source_AUC', '31 sources; paired', 'primary (v3a plan)',
      'non-detection is not equivalence; interval allows -0.18 to +0.05',
      lambda: triplet(V3A, comparison='H_plus_B - H_colours', model='LogReg', metric='source_AUC'))
claim('C07', '4.1', 'H+B minus H, source-level AUC, RF (primary of v3a)', [-0.012, -0.077, 0.048], V3A,
      'comparison=H_plus_B - H_colours, model=RandomForest, metric=source_AUC', '31 sources; paired', 'primary (v3a plan)',
      'as C06', lambda: triplet(V3A, comparison='H_plus_B - H_colours', model='RandomForest', metric='source_AUC'))
V3B = 'results/v3/v3b_bootstrap.csv'
claim('C08', '4.1', 'Colours incl. 3-5 keV minus H, LR / RF', [-0.018, -0.071, 0.000, -0.054, -0.161, 0.006], V3B,
      'comparison=H3_colours_3_25 - H_colours, model=LogReg|RandomForest, metric=source_AUC', '31 sources', 'primary (v3b plan)',
      'non-detection', lambda: triplet(V3B, comparison='H3_colours_3_25 - H_colours', model='LogReg', metric='source_AUC')
      + triplet(V3B, comparison='H3_colours_3_25 - H_colours', model='RandomForest', metric='source_AUC'))
HX = 'results/v4b3/v4b3_bootstrap.csv'
claim('C09', '4.1', 'HEXTE 25-60 keV colours added to H (396 obs), LR / RF', [-0.048, -0.179, 0.024, 0.000, -0.036, 0.036], HX,
      'comparison=H+X|LogReg - H|LogReg (and RF), metric=source_AUC, subset=HEXTE subset', '396 obs, 31 sources', 'primary (v4 plan)',
      'HEXTE subset only (cluster B, before 2009 Dec)',
      lambda: triplet(HX, comparison='H+X|LogReg - H|LogReg', metric='source_AUC', subset='HEXTE subset')
      + triplet(HX, comparison='H+X|RandomForest - H|RandomForest', metric='source_AUC', subset='HEXTE subset'))
claim('C10', '4.1', 'H-LR trained on all 7949 epoch-5 observations minus 456-observation H-LR', [0.000, -0.048, 0.036],
      'results/v4b1/v4b1_bootstrap.csv', 'comparison=H_colours|LogReg[srcw] - H-LR (v2, 456 obs), metric=source_AUC',
      '31 sources', 'primary (v4 plan)', 'source-equal weights in training',
      lambda: triplet('results/v4b1/v4b1_bootstrap.csv', comparison='H_colours|LogReg[srcw] - H-LR (v2, 456 obs)', metric='source_AUC'))
claim('C11', '4.1', 'Nested search over 8 algorithms x 4 representations minus H-LR', [-0.173, -0.399, 0.012],
      'results/v4/v4a_bootstrap.csv', 'comparison=auto|nested:auto - H_colours|LogReg, metric=source_AUC, part=1e_primary',
      '31 sources; nested LOSO', 'primary (v4 plan)', 'point estimate worse than H-LR; interval includes 0',
      lambda: triplet('results/v4/v4a_bootstrap.csv', comparison='auto|nested:auto - H_colours|LogReg', metric='source_AUC', part='1e_primary'))


def leakage():
    o = rd('results/v2/secondary_observation_split.csv')
    m = rd('results/v2/metrics_observation_level.csv')
    d = o.merge(m[['representation', 'model', 'balanced_accuracy']], on=['representation', 'model'], suffixes=('_obs', '_loso'))
    diff = d.balanced_accuracy_obs - d.balanced_accuracy_loso
    return [round(diff.min(), 2), round(diff.max(), 2)]


claim('C12', '4.1, 5.3', 'Observation-wise 5-fold split inflates observation-level balanced accuracy by +0.04 to +0.16 relative to LOSO',
      [0.04, 0.16], 'results/v2/secondary_observation_split.csv; results/v2/metrics_observation_level.csv',
      'all 8 representation x model pairs; difference computed here (arithmetic on committed values)', '456 obs, 31 sources',
      'descriptive', 'our sample only; not an evaluation of any published model', leakage, dec=2)

# ---------------------------------------------------------------------------------------------- state dependence
V7 = 'results/v7a/state_stratified_metrics.csv'
claim('C13', '4.2, abstract, conclusions', 'H-LR observation-level AUC soft-like / hard-like / difference (RXTE)',
      [0.954, 0.801, 1.000, 0.646, 0.445, 0.841, 0.309, 0.099, 0.510], V7,
      'analysis=v2 OOF, model=H-LR, group=soft-like|hard-like|soft-like - hard-like, metric=obs_AUC',
      '221 soft-like / 180 hard-like obs', 'primary (v7 plan) for the difference', 'rms-defined classes, not spectral states; 5 BHs in soft-like',
      lambda: triplet(V7, analysis='v2 OOF', model='H-LR', group='soft-like', metric='obs_AUC')
      + triplet(V7, analysis='v2 OOF', model='H-LR', group='hard-like', metric='obs_AUC')
      + triplet(V7, analysis='v2 OOF', model='H-LR', group='soft-like - hard-like', metric='obs_AUC'))
claim('C14', '4.2', 'Soft-minus-hard AUC differences for H-RF and B-LR', [0.254, 0.293], V7,
      'analysis=v2 OOF, model=H-RF|B-LR, group=soft-like - hard-like, metric=obs_AUC', 'as C13', 'descriptive', 'as C13',
      lambda: [pick(V7, analysis='v2 OOF', model='H-RF', group='soft-like - hard-like', metric='obs_AUC').point,
               pick(V7, analysis='v2 OOF', model='B-LR', group='soft-like - hard-like', metric='obs_AUC').point])


def state_counts():
    s = rd('results/v7a/states.csv')
    out = []
    for st in ('soft-like', 'hard-like'):
        g = s[s.state == st]
        out += [len(g[g.label == 'BH']), g[g.label == 'BH'].source_id.nunique(), len(g[g.label == 'NS']), g[g.label == 'NS'].source_id.nunique()]
    out.append(int((~s.state.isin(['soft-like', 'hard-like'])).sum()))
    return out


claim('C15', '4.2', 'RXTE state counts: soft-like 38 BH obs/5 BH, 183 NS obs/22 NS; hard-like 59/7, 121/17; 55 other',
      [38, 5, 183, 22, 59, 7, 121, 17, 55], 'results/v7a/states.csv', 'count by state and label (computed here)',
      '456 obs', 'descriptive', 'counts', state_counts, dec=0)


def nicer_colour_ranges():
    v9, v11, v12, v13 = rd('results/v9a/v9a_metrics.csv'), rd('results/v11/v11a_metrics.csv'), rd('results/v12/v12b_gain.csv'), rd('results/v13/v13a_gain.csv')
    hard = {'LR': [], 'RF': []}; soft = []
    for m in ('LR', 'RF'):
        for st, store in (('hard-like', hard[m]), ('soft-like', soft)):
            store.append(pick('results/v9a/v9a_metrics.csv', analysis=f'NICER all-state LOSO | {st}', comparison=f'H_N-{m}', metric='obs_AUC').point)
            store.append(pick('results/v11/v11a_metrics.csv', analysis=f'new obs | {st}', comparison=f'H_N-{m}', metric='obs_AUC').point)
            store.append(pick('results/v12/v12b_gain.csv', analysis=st, comparison=f'H_N-{m}').point)
            store.append(pick('results/v13/v13a_gain.csv', analysis=st, comparison=f'H_N-{m}').point)
    return [round(min(hard['LR']), 2), round(max(hard['LR']), 2), round(min(hard['RF']), 2), round(max(hard['RF']), 2), round(min(soft), 2), round(max(soft), 2)]


claim('C16', '4.2, 5.1', 'NICER colour-only hard-like AUC 0.50-0.68 (LR), 0.67-0.75 (RF); soft-like 0.83-0.95',
      [0.50, 0.68, 0.67, 0.75, 0.83, 0.95], 'results/v9a/v9a_metrics.csv; results/v11/v11a_metrics.csv; results/v12/v12b_gain.csv; results/v13/v13a_gain.csv',
      'colour-only rows (H_N-LR, H_N-RF) in soft-like and hard-like strata; min/max computed here', 'N1 prefix, N2, N1+N2 corrected, N3',
      'descriptive', 'different samples share sources; not independent', nicer_colour_ranges, dec=2)

# ---------------------------------------------------------------------------------------------- timing gain
F = 'results/final_timing_gain_across_versions.csv'
claim('C17', '4.3, abstract, Table 2', 'RXTE development hard-like LR gain (0.646 -> 0.910)', [0.264, 0.048, 0.455], F,
      'label=v8a RXTE v2 sample, model=LR', '180 hard-like obs; 7 BH/17 NS sources', 'primary (v8 plan)',
      'development data; timing signal first seen in v5; plan written after v1-v7',
      lambda: triplet(F, cols=('point', 'lo', 'hi'), label='v8a RXTE v2 sample', model='LR'))
claim('C18', '4.3', 'H+T-LR hard-like observation AUC 0.910', [0.910], 'results/v8a/v8a_metrics.csv',
      'analysis=S1 existing OOF | hard-like, comparison=H+T-LR, metric=obs_AUC', '180 obs', 'descriptive', '',
      lambda: [pick('results/v8a/v8a_metrics.csv', analysis='S1 existing OOF | hard-like', comparison='H+T-LR', metric='obs_AUC').point])
claim('C19', '4.3', 'RXTE development RF hard-like gain', [0.230, 0.074, 0.408], F, 'label=v8a RXTE v2 sample, model=RF',
      '180 obs', 'descriptive', 'RF not primary', lambda: triplet(F, cols=('point', 'lo', 'hi'), label='v8a RXTE v2 sample', model='RF'))
V8 = 'results/v8a/v8a_metrics.csv'
claim('C20', '4.3', 'RXTE soft-like LR gain', [0.036, 0.000, 0.158], V8,
      'analysis=S1 existing OOF | soft-like, comparison=H+T-LR - H-LR, metric=obs_AUC', '221 obs', 'descriptive', '',
      lambda: triplet(V8, analysis='S1 existing OOF | soft-like', comparison='H+T-LR - H-LR', metric='obs_AUC'))
claim('C21', '4.3', 'RXTE hard-like source-level AUC 0.748 -> 0.933', [0.748, 0.933], V8,
      'analysis=S1 hard-like | source level (restricted OOF), comparison=H-LR|H+T-LR, metric=source_AUC', '24 sources', 'descriptive',
      'source-level; small n', lambda: [pick(V8, analysis='S1 hard-like | source level (restricted OOF)', comparison='H-LR', metric='source_AUC').point,
                                         pick(V8, analysis='S1 hard-like | source level (restricted OOF)', comparison='H+T-LR', metric='source_AUC').point])
claim('C22', '4.3', 'RXTE hard-like source-level AUC gain', [0.185, 0.008, 0.403], V8,
      'analysis=S1 hard-like | source level (restricted OOF), comparison=H+T-LR - H-LR, metric=source_AUC', '24 sources', 'descriptive', 'small n',
      lambda: triplet(V8, analysis='S1 hard-like | source level (restricted OOF)', comparison='H+T-LR - H-LR', metric='source_AUC'))
claim('C23', '4.3', 'H+T1 / H+T2 / H+T3 LR hard-like AUC (RXTE)', [0.926, 0.874, 0.654], V8,
      'analysis=S1 existing OOF | hard-like, comparison=H+T1-LR|H+T2-LR|H+T3-LR, metric=obs_AUC', '180 obs', 'descriptive', 'single-band ablation',
      lambda: [pick(V8, analysis='S1 existing OOF | hard-like', comparison=f'H+T{k}-LR', metric='obs_AUC').point for k in (1, 2, 3)])
V8B = 'results/v8b/v8b_metrics.csv'
claim('C24', '4.3, Table 2', 'RXTE external frozen hard-like gain; colour-only baseline 0.817', [0.064, -0.185, 0.367, 0.817], V8B,
      'analysis=X frozen v6 models | hard-like, comparison=H_R+T-LR - H_R-LR / H_R-LR, metric=obs_AUC', '99 obs; 5 BH/15 NS sources',
      'primary (v8 plan)', 'not detected; 15 of the external sources had been seen with other models',
      lambda: triplet(V8B, analysis='X frozen v6 models | hard-like', comparison='H_R+T-LR - H_R-LR', metric='obs_AUC')
      + [pick(V8B, analysis='X frozen v6 models | hard-like', comparison='H_R-LR', metric='obs_AUC').point])
claim('C25', '4.3, Table 2', 'NICER N1 (prefix) hard-like gain LR / RF', [0.112, -0.004, 0.229, 0.236, 0.104, 0.372], F,
      'label=v9a NICER (prefix), model=LR|RF', '142 hard-like obs; 7 BH/32 NS', 'LR primary (v9 plan); RF descriptive', 'not detected with LR',
      lambda: triplet(F, cols=('point', 'lo', 'hi'), label='v9a NICER (prefix)', model='LR') + triplet(F, cols=('point', 'lo', 'hi'), label='v9a NICER (prefix)', model='RF'))
P10 = 'results/v10a/v10a_pooled_gain.csv'
claim('C26', '4.3', 'NICER N1 full files hard-like gain LR / RF', [0.107, -0.010, 0.224, 0.219, 0.100, 0.337], f'{P10}; {F}',
      'component=NICER (full); label=v10 NICER full, model=RF', '144 obs; 7 BH/32 NS', 'descriptive', 'same observations as N1 prefix',
      lambda: triplet(P10, component='NICER (full)') + triplet(F, cols=('point', 'lo', 'hi'), label='v10 NICER full', model='RF'))
V9 = 'results/v9a/v9a_metrics.csv'
claim('C27', '4.3', 'NICER N1 single-band LR gains T1 / T2 / T3', [0.048, -0.041, 0.140, 0.143, 0.028, 0.271, 0.115, 0.030, 0.217], V9,
      'analysis=NICER all-state LOSO | hard-like, comparison=H_N+Tk-LR - H_N-LR, metric=obs_AUC', '142 obs', 'descriptive', 'band carrying the signal differs from RXTE',
      lambda: sum([triplet(V9, analysis='NICER all-state LOSO | hard-like', comparison=f'H_N+T{k}-LR - H_N-LR', metric='obs_AUC') for k in (1, 2, 3)], []))
claim('C28', '4.3', 'Brightness proxy: (H+R+T) - (H+R), LR, NICER N1', [0.069, -0.013, 0.161], V9,
      'analysis=NICER all-state LOSO | hard-like, comparison=H_N+R+T_N-LR - H_N+R-LR, metric=obs_AUC', '142 obs', 'descriptive',
      'log count rate is a brightness proxy, not Eddington ratio',
      lambda: triplet(V9, analysis='NICER all-state LOSO | hard-like', comparison='H_N+R+T_N-LR - H_N+R-LR', metric='obs_AUC'))
claim('C29', '4.3, Table 2', 'Pooled RXTE+NICER hard-like gain (LR)', [0.145, 0.028, 0.257], F, 'label=v10a pooled RXTE+NICER, model=LR',
      '423 hard-like obs (180+99+144)', 'primary (v10 plan)', 'NOT independent: re-uses RXTE dev., external and N1',
      lambda: triplet(F, cols=('point', 'lo', 'hi'), label='v10a pooled RXTE+NICER', model='LR'))

# ---------------------------------------------------------------------------------------------- unseen observations
V11 = 'results/v11/v11a_metrics.csv'
claim('C30', '4.4, Table 2', 'N2 LR hard-like gain (0.660 -> 0.726)', [0.066, -0.095, 0.180, 0.660, 0.726], V11,
      'analysis=new obs | hard-like, comparison=H_N+T_N-LR - H_N-LR / H_N-LR / H_N+T_N-LR, metric=obs_AUC', '143 obs; 9 BH/33 NS (N1 sources)',
      'primary (v11 plan; LR fixed before download)', 'not detected; same sources as N1',
      lambda: triplet(V11, analysis='new obs | hard-like', comparison='H_N+T_N-LR - H_N-LR', metric='obs_AUC')
      + [pick(V11, analysis='new obs | hard-like', comparison=k, metric='obs_AUC').point for k in ('H_N-LR', 'H_N+T_N-LR')])
claim('C31', '4.4', 'N2 LR observation-level balanced accuracy change at frozen threshold', [-0.080, -0.166, -0.022], V11,
      'analysis=new obs hard-like | source level, comparison=H_N+T_N-LR - H_N-LR, metric=obs_balanced_accuracy', '143 obs', 'descriptive',
      'calibration did not transfer', lambda: triplet(V11, analysis='new obs hard-like | source level', comparison='H_N+T_N-LR - H_N-LR', metric='obs_balanced_accuracy'))
claim('C32', '4.4', 'N2 RF hard-like gain (0.665 -> 0.912)', [0.247, 0.128, 0.384, 0.665, 0.912], V11,
      'analysis=new obs | hard-like, comparison=H_N+T_N-RF - H_N-RF / H_N-RF / H_N+T_N-RF, metric=obs_AUC', '143 obs', 'descriptive', 'RF not yet primary',
      lambda: triplet(V11, analysis='new obs | hard-like', comparison='H_N+T_N-RF - H_N-RF', metric='obs_AUC')
      + [pick(V11, analysis='new obs | hard-like', comparison=k, metric='obs_AUC').point for k in ('H_N-RF', 'H_N+T_N-RF')])
V12 = 'results/v12/v12b_gain.csv'
claim('C33', '4.4, Table 2', 'N1+N2 3C50 RF hard-like gain (0.750 -> 0.924)', [0.174, 0.071, 0.300, 0.750, 0.924], V12,
      'analysis=hard-like, comparison=H_N+T_N-RF - H_N-RF / H_N-RF / H_N+T_N-RF', '202 obs; 8 BH/34 NS', 'primary (v12 plan; RF chosen post hoc)',
      'robustness re-analysis of re-used data; not independent',
      lambda: triplet(V12, analysis='hard-like', comparison='H_N+T_N-RF - H_N-RF') + [pick(V12, analysis='hard-like', comparison=k).point for k in ('H_N-RF', 'H_N+T_N-RF')])
claim('C34', '4.4', 'N1+N2 3C50: LR gain; RF source-level AUC and BA gains', [0.090, -0.056, 0.243, 0.074, -0.033, 0.206, 0.173, 0.004, 0.357], V12,
      'analysis=hard-like (LR); analysis=hard-like source level, comparison=H_N+T_N-RF - H_N-RF, metric=source_AUC|source_balanced_accuracy', '202 obs; 42 sources', 'descriptive', '',
      lambda: triplet(V12, analysis='hard-like', comparison='H_N+T_N-LR - H_N-LR')
      + triplet(V12, analysis='hard-like source level', comparison='H_N+T_N-RF - H_N-RF', metric='source_AUC')
      + triplet(V12, analysis='hard-like source level', comparison='H_N+T_N-RF - H_N-RF', metric='source_balanced_accuracy'))


def bkg(path, total):
    b = rd(path)
    ok = b.status.eq('ok')
    f = b.loc[ok, 'f_T']
    return [int(ok.sum()), len(b), round(float(f.median()), 3), int((f > 0.20).sum())]


claim('C35', '2.4', 'N1+N2 3C50: 362 of 503 succeeded; median f 0.008; 9 with f > 0.20', [362, 503, 0.008, 9],
      'data/v12/processed/bkg3c50.csv', 'status, f_T (computed here)', '503 faint obs', 'background processing', 'failures non-random (old gain calibration)',
      lambda: bkg('data/v12/processed/bkg3c50.csv', 503), dec=3)
claim('C36', '2.4', 'N3 3C50: 109 of 148 succeeded; median f 0.006; 1 with f > 0.20', [109, 148, 0.006, 1],
      'data/v13/processed/bkg3c50.csv', 'status, f_T (computed here)', '148 faint obs', 'background processing', 'as C35',
      lambda: bkg('data/v13/processed/bkg3c50.csv', 148), dec=3)
V13 = 'results/v13/v13a_gain.csv'
claim('C37', '4.4, abstract, Table 3, conclusions', 'N3 primary RF hard-like gain (0.680 -> 0.864)',
      [0.184, 0.049, 0.337, 0.680, 0.463, 0.870, 0.864, 0.714, 0.968], V13,
      'analysis=hard-like, comparison=H_N+T_N-RF - H_N-RF / H_N-RF / H_N+T_N-RF', '74 hard-like obs; 8 BH/19 NS sources',
      'primary (v13 plan; RF, pipeline and models fixed before download)',
      'unseen observations of sources already in the sample; observation-level metric; source bootstrap of fixed predictions',
      lambda: triplet(V13, analysis='hard-like', comparison='H_N+T_N-RF - H_N-RF') + triplet(V13, analysis='hard-like', comparison='H_N-RF')
      + triplet(V13, analysis='hard-like', comparison='H_N+T_N-RF'))
claim('C38', '4.4, Table 3', 'N3 LR hard-like gain (0.503 -> 0.685)', [0.182, 0.022, 0.347, 0.503, 0.685], V13,
      'analysis=hard-like, comparison=H_N+T_N-LR - H_N-LR / H_N-LR / H_N+T_N-LR', '74 obs', 'descriptive', '',
      lambda: triplet(V13, analysis='hard-like', comparison='H_N+T_N-LR - H_N-LR') + [pick(V13, analysis='hard-like', comparison=k).point for k in ('H_N-LR', 'H_N+T_N-LR')])
claim('C39', '4.4, Table 3', 'N3 soft-like RF gain', [0.005, -0.015, 0.035], V13, 'analysis=soft-like, comparison=H_N+T_N-RF - H_N-RF',
      '120 soft-like obs', 'descriptive', '', lambda: triplet(V13, analysis='soft-like', comparison='H_N+T_N-RF - H_N-RF'))
claim('C40', '4.4, Table 3', 'N3 RF observation balanced accuracy 0.607 -> 0.744 (gain)', [0.607, 0.744, 0.137, 0.019, 0.275], V13,
      'analysis=hard-like source level, metric=obs_balanced_accuracy', '74 obs; paired bootstrap over 27 sources', 'descriptive', 'threshold 0.5 frozen',
      lambda: [pick(V13, analysis='hard-like source level', comparison=k, metric='obs_balanced_accuracy').point for k in ('H_N-RF', 'H_N+T_N-RF')]
      + triplet(V13, analysis='hard-like source level', comparison='H_N+T_N-RF - H_N-RF', metric='obs_balanced_accuracy'))
claim('C41', '4.4, abstract, Table 3, conclusions', 'N3 RF source-level AUC 0.717 -> 0.842, gain; source BA 0.572 -> 0.671, gain',
      [0.717, 0.842, 0.125, -0.053, 0.303, 0.572, 0.671, 0.099, -0.053, 0.286], V13,
      'analysis=hard-like source level, metric=source_AUC|source_balanced_accuracy', '27 sources (8 BH/19 NS)', 'descriptive',
      'not detected; equal weight per source',
      lambda: [pick(V13, analysis='hard-like source level', comparison=k, metric='source_AUC').point for k in ('H_N-RF', 'H_N+T_N-RF')]
      + triplet(V13, analysis='hard-like source level', comparison='H_N+T_N-RF - H_N-RF', metric='source_AUC')
      + [pick(V13, analysis='hard-like source level', comparison=k, metric='source_balanced_accuracy').point for k in ('H_N-RF', 'H_N+T_N-RF')]
      + triplet(V13, analysis='hard-like source level', comparison='H_N+T_N-RF - H_N-RF', metric='source_balanced_accuracy'))
claim('C42', '4.4, Table 3', 'N3 leave-one-BH-source-out RF gain range', [0.146, 0.212], 'results/v13/v13a_influence.csv',
      'min/max of rf_gain (computed here)', '8 values', 'influence', 'no interval',
      lambda: [rd('results/v13/v13a_influence.csv').rf_gain.min(), rd('results/v13/v13a_influence.csv').rf_gain.max()])
claim('C43', '4.4, Table 3', 'N3 RF gain with timing restricted to 3C50 GTIs (106 faint obs recomputed)', [0.190, 0.065, 0.330],
      'results/v13/v13a_gti_restricted.csv', 'single row', '74 obs', 'descriptive', 'only N3 checked',
      lambda: [float(rd('results/v13/v13a_gti_restricted.csv').iloc[0][c]) for c in ('point', 'ci2_5', 'ci97_5')])


def v13_comp():
    x = rd('results/v13/v13_frozen_predictions.csv'); x = x[x.name == 'H_N-RF']; h = x[x.state == 'hard-like']
    return [len(h[h.true_label == 'BH']), h[h.true_label == 'BH'].source_id.nunique(), len(h[h.true_label == 'NS']), h[h.true_label == 'NS'].source_id.nunique(),
            int((h.source_id == 'Cyg X-1').sum()), int((h.source_id == '4U 1812-12').sum()), len(x), int((x.state == 'soft-like').sum())]


claim('C44', '4.4, Table 1', 'N3 composition: 29 BH obs/8 BHs, 45 NS obs/19 NSs hard-like; Cyg X-1 7, 4U 1812-12 8; 198 retained; 120 soft-like',
      [29, 8, 45, 19, 7, 8, 198, 120], 'results/v13/v13_frozen_predictions.csv', 'name=H_N-RF; counts computed here', '198 obs', 'descriptive', 'uneven per-source counts',
      v13_comp, dec=0)

# ---------------------------------------------------------------------------------------------- nu_c
N = 'results/final_nuc_difference_across_versions.csv'
claim('C45', '4.5, App. C', 'nu_c D (p): pooled -0.368 (0.0012); N2 -0.663 (0.0225); N1+N2 3C50 -0.514 (0.073); N3 -0.427 (0.209); RXTE external -0.037 (0.78)',
      [-0.37, 0.0012, -0.66, 0.022, -0.51, 0.073, -0.43, 0.21, -0.04, 0.78], N, 'label=v10b pooled / v11b / v12a / v13b / v6d RXTE external',
      'source means; 20000 label permutations', 'v9b-v13b primary; v6d descriptive', 'secondary; re-used data; no multiplicity correction; no mass/Eddington control',
      lambda: [round(pick(N, label='v10b pooled RXTE+NICER').D, 2), round(pick(N, label='v10b pooled RXTE+NICER').p, 4),
               round(pick(N, label='v11b NICER new obs').D, 2), round(pick(N, label='v11b NICER new obs').p, 3),
               round(pick(N, label='v12a NICER 3C50-corrected').D, 2), round(pick(N, label='v12a NICER 3C50-corrected').p, 3),
               round(pick(N, label='v13b NICER third set').D, 2), round(pick(N, label='v13b NICER third set').p, 2),
               round(pick(N, label='v6d RXTE external (all states)').D, 2), round(pick(N, label='v6d RXTE external (all states)').p, 2)], dec=4)
claim('C46', '4.5', 'N2 post hoc screen: D -0.46 (p 0.19) after removing c2 > 0.7; N3 GTI-restricted D -0.30 (p 0.41)', [-0.46, 0.19, -0.30, 0.41],
      'results/v11/v11b_post_hoc_screens.csv; results/v13/v13b_nuc.csv', 'both screens row; 3C50-GTI-restricted row', 'hard-like obs', 'post hoc; descriptive', '',
      lambda: [round(rd('results/v11/v11b_post_hoc_screens.csv').D.iloc[3], 2), round(rd('results/v11/v11b_post_hoc_screens.csv').p.iloc[3], 2),
               round(rd('results/v13/v13b_nuc.csv').D.iloc[-1], 2), round(rd('results/v13/v13b_nuc.csv').p.iloc[-1], 2)], dec=2)
claim('C47', 'App. C', 'N3 frozen nu* rule: observation sensitivity 0.79, specificity 0.76; sources 7/8 BH, 13/19 NS', [0.79, 0.76, 7, 13],
      'results/v13/v13_frozen_rule.csv', 'single row', '74 obs; 27 sources', 'descriptive', '',
      lambda: [round(pick('results/v13/v13_frozen_rule.csv', nu_star_Hz=1.3361).obs_sensitivity, 2), round(pick('results/v13/v13_frozen_rule.csv', nu_star_Hz=1.3361).obs_specificity, 2),
               round(pick('results/v13/v13_frozen_rule.csv', nu_star_Hz=1.3361).source_sensitivity * 8), round(pick('results/v13/v13_frozen_rule.csv', nu_star_Hz=1.3361).source_specificity * 19)], dec=2)

# ---------------------------------------------------------------------------------------------- appendix B
claim('C48', 'App. B', 'External sources all states (v6): source AUC 1.000 both; source BA 0.868 -> 0.974 (+0.105 [0.000, +0.237])',
      [0.868, 0.974, 0.105, 0.000, 0.237], 'results/v6/v6_bootstrap.csv', 'name=H_R-LR / H_R+T-LR, metric=source_balanced_accuracy (v6a PRIMARY external E)',
      '23 external sources', 'primary (v6 plan)', 'not detected; AUC saturated',
      lambda: [pick('results/v6/v6_bootstrap.csv', name='H_R-LR', comparison='H_R-LR', metric='source_balanced_accuracy', analysis='v6a PRIMARY external E (frozen, trained on S1)').point,
               pick('results/v6/v6_bootstrap.csv', name='H_R+T-LR', comparison='H_R+T-LR', metric='source_balanced_accuracy', analysis='v6a PRIMARY external E (frozen, trained on S1)').point]
      + triplet('results/v6/v6_bootstrap.csv', name='H_R+T-LR', comparison='H_R+T-LR - H_R-LR', metric='source_balanced_accuracy', analysis='v6a PRIMARY external E (frozen, trained on S1)'))
claim('C49', 'App. B, 5.3', 'MAXI (strict labels): KNN two colours source AUC 0.80; N_H-corrected RF gain +0.377 [+0.160, +0.595]; corrected single-colour RF 0.361',
      [0.80, 0.377, 0.160, 0.595, 0.361], 'results/v7c/v7c2_bootstrap.csv; results/v8d/v8d_bootstrap.csv', 'KNN [C2D] source_AUC; RF [C2D_NH] - RF [C1D_NH]; RF [C1D_NH]',
      '13 BH / 48 NPNS MAXI sources', 'v8d primary; others descriptive', 'different instrument and label set',
      lambda: [round(rd('results/v7c/v7c2_bootstrap.csv').query("name=='KNN [C2D]' and metric=='source_AUC'").point.iloc[0], 2)]
      + triplet('results/v8d/v8d_bootstrap.csv', comparison='RF [C2D_NH] - RF [C1D_NH]', metric='source_AUC')
      + [pick('results/v8d/v8d_bootstrap.csv', comparison='RF [C1D_NH]', metric='source_AUC').point], dec=3)
claim('C50', 'App. B', 'Event-mode IC4 Spearman 0.818 (< 0.90 required)', [0.82], 'results/v8c/ic4_lc_vs_t3.csv', 'first row',
      '148 obs', 'implementation check (failed)', 'all v8c results exploratory', lambda: [round(rd('results/v8c/ic4_lc_vs_t3.csv').spearman.iloc[0], 2)], dec=2)

# ---------------------------------------------------------------------------------------------- manual claims
MANUAL = [
    ('M01', '2.1, abstract', '16 dynamically confirmed BHs among 86 sources in the RXTE+NICER union',
     'reports/decision_log.md (v10 results row: "天體聯集 86 個（16 BH）"); results/v10a/source_identity.csv; reports/preregistration_v11.md sec. 0',
     'checked in the decision log and v11 plan; union file not re-derived here'),
    ('M02', '3.6, Table 2', 'Plan commit hashes and times (v8 a481fa0 ... v13 42fe1d2); N3 data 6867de0, results 3d86930',
     'git log --diff-filter=A -- reports/preregistration_v*.md (run 2026-10-09)', 'checked with git; timestamps are committer clock, not an external registry'),
    ('M03', '3.6, 5.2', 'RF made primary in v12 after RF gains seen in v9-v11; RF fixed before download in v13',
     'reports/preregistration_v12.md sec. 5; reports/preregistration_v13.md sec. 0, 2.4', 'checked'),
    ('M04', '3.6', 'Plans written after all earlier results and self-approved within the project, not externally reviewed',
     'header of every reports/preregistration_v*.md; reports/decision_log.md (v5 stage 0 onwards)', 'checked'),
    ('M05', '3.3', 'State thresholds r > 0.10 hard-like, r < 0.075 soft-like; RXTE 0.1-4 Hz, NICER 0.1-10 Hz',
     'scripts/config.py V7_RMS_HARD, V7_RMS_SOFT, V7_RMS_J, V9_STATE_J; scripts/v7lib.py state_rms; scripts/v9lib.py obs_features', 'checked in code'),
    ('M06', '3.2', 'Timing bands T1 0.016-0.094, T2 0.10-1.0, T3 1.0-4.0 Hz; cross-spectra between detector groups; ratio of means; signed sqrt',
     'scripts/config.py V5_BANDS_J, V9_T_BANDS_J; scripts/v9lib.py obs_features', 'checked in code (j/128 s: 2-12, 13-128, 129-511)'),
    ('M07', '3.4', 'LR C=1 L2 balanced standardised; RF 500 trees sqrt min_samples_leaf=2 balanced',
     'scripts/config.py LR_PARAMS, RF_PARAMS; scripts/v4lib.py V4Model (SCALED set)', 'checked in code'),
    ('M08', '3.5', 'Bootstrap: 2000 class-stratified source draws, seed 42, fixed predictions, stratum applied within draw',
     'scripts/v7lib.py boot_draws; scripts/v8lib.py strat_boot; scripts/config.py SEED, N_BOOT', 'checked in code'),
    ('M09', '3.5, 4.4', 'N3 models trained on corrected N1+N2 excluding the tested source', 'scripts/63_v13_analysis.py predict()', 'checked in code'),
    ('M10', '2.4', '3C50 correction: rms x 1/(1-f), band-wise colour correction, state reassigned, f > 0.20 or failure excluded',
     'scripts/63_v13_analysis.py corrected(); reports/preregistration_v12.md sec. 3', 'checked in code'),
    ('M11', '2.2', '13 eligible bursters missing from the development-sample source rule', 'reports/decision_log.md v4b2 list-verification row', 'checked in log'),
    ('M12', '2.2, App. B', 'MINBAR: 58 of 456 development observations overlap a burst; exclusion leaves conclusions unchanged',
     'reports/decision_log.md v7b1 rows; results/v7b1/exclusion_counts.csv (398 = 456 - 58)', 'checked'),
    ('M13', '4.3', 'External per-source mean scores: GS 1354-64 0.54->0.97; IGR J00291+5934 0.45->0.89; EXO 1745-248 0.32->0.73',
     'reports/decision_log.md v8b results row; results/v8b/v8b_per_source_state.csv', 'checked in log only'),
    ('M14', '1, 5.3, App. D', 'Pattnaik+2021: RXTE 5-25 keV, 61 LMXBs, ~15000 obs, sources held out, 87+-13%, more misclassification in hard/intermediate states and low S/N',
     'search-engine records of arXiv:2012.06934 / MNRAS 501, 3457 (2026-10-09); reports/final_report_zh-TW.md sec. 6', 'metadata verified; method details from secondary records and the project reading; full text not re-read'),
    ('M15', '1, 5.3, App. D', 'Garg+2026: neural networks on RXTE spectra, 90-94%, observation-wise 80:20 split; fit parameters incl. data variance',
     'search-engine records of arXiv:2601.18139 (abstract); reports/final_report_zh-TW.md sec. 6 for the split', 'abstract verified; split NOT verified against full text in this session'),
    ('M16', '1, 5.3', 'de Beurs+2022: MAXI CCI, BH/NPNS/pulsar, GP/kNN/SVM, sources held out; 7 of 12 "BHs" are candidates',
     'search records (APS abstract, Vrtilek bibliography); reports/decision_log.md v7 stage 0 and v7c1 rows', 'partly verified; candidate count from the project check of the public data'),
    ('M17', '1', 'Done & Gierlinski 2003; Sunyaev & Revnivtsev 2000; Gardenier & Uttley 2018; Heil+2015; Wijnands & van der Klis 1999; Klein-Wolt & van der Klis 2008; Burke+2017 statements',
     'search-engine abstract records (2026-10-09)', 'statements limited to what the abstracts state'),
    ('M18', '3.5', 'AUC 0.864 is not 86.4% accuracy', 'definition', 'n/a'),
]


def nums_in_tex(vals):
    missing = []
    for v in vals:
        if isinstance(v, int) or (isinstance(v, float) and float(v).is_integer() and abs(v) > 1.5):
            s = str(int(v))
        else:
            s = f'{abs(v):.3f}'.rstrip('0') if abs(v) < 1 else f'{abs(v):.3f}'
            s = s if s not in ('0.', '0') else '0.000'
            if s.endswith('.'):
                s += '0'
        cand = {s, f'{abs(v):.3f}', f'{abs(v):.2f}', f'{abs(v):.4f}'.rstrip('0')}
        if not any(c in TEXN for c in cand):
            missing.append(v)
    return missing


def main():
    rows = []
    n_ok = n_bad = 0
    for c in CLAIMS:
        vals = c['paper_values']
        try:
            got = [float(x) for x in c['getter']()]
            tol = 0.5 * 10 ** (-c['dec']) + 1e-9
            ok = len(got) == len(vals) and all(abs(round(g, c['dec']) - v) <= tol or abs(g - v) <= tol for g, v in zip(got, vals))
            miss = nums_in_tex(vals)
            status = ('verified against committed file' if ok else f'MISMATCH: file gives {np.round(got, 4).tolist()}')
            status += '; all numbers found in main.tex' if not miss else f'; NOT found in main.tex: {miss}'
            n_ok += ok and not miss; n_bad += (not ok) or bool(miss)
        except Exception as e:
            status = f'ERROR {type(e).__name__}: {e}'; n_bad += 1
        rows.append(dict(claim_id=c['claim_id'], paper_section=c['section'], claim=c['claim'],
                         values_in_paper='; '.join(str(v) for v in vals), source_file=c['source_file'], source_rows=c['source_rows'],
                         sample_and_unit=c['sample_and_unit'], status_of_result=c['role'], required_limitations=c['required_limitations'],
                         verification=status))
    for m in MANUAL:
        rows.append(dict(claim_id=m[0], paper_section=m[1], claim=m[2], values_in_paper='', source_file=m[3], source_rows='',
                         sample_and_unit='', status_of_result='', required_limitations='', verification='manual: ' + m[4]))
    out = ROOT / 'paper_draft/claim_evidence.csv'
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f'{len(CLAIMS)} automatic claims: {n_ok} verified, {n_bad} with problems; {len(MANUAL)} manual rows -> {out}')
    for r in rows:
        if r['verification'].startswith(('MISMATCH', 'ERROR')) or 'NOT found' in r['verification']:
            print(r['claim_id'], r['verification'])


if __name__ == '__main__':
    main()
