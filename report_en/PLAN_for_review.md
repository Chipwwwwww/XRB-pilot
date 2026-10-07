# XRB-pilot English technical report — plan for review (before writing)

Repo state read: `master` @ `d9730c9` (Merge v14 wrap-up). All reports, pre-registrations, decision log, `config.py`,
`common.py`, `spectra.py`, `v3lib`–`v11lib`, scripts 01–64 and unit tests were read; committed `.npz`/`.csv` files were opened
with Python (read only) to obtain real shapes. Nothing was re-run and no raw data were downloaded.

Conventions proposed for the whole report
- Document class `report` (11 pt, A4, 1 in margins), so the phases are chapters; main file `report_en/main.tex`,
  one file per chapter in `report_en/sections/`.
- Status tags on every result: **[Primary]**, **[Secondary]**, **[Exploratory]**, **[Post hoc]** (macros, colour-coded).
- Verdict wording follows the repo rule: "detected (95% CI excludes 0)" / "not detected under the pre-registered criterion".
- Common methods are defined once in Ch. 2–5; phase chapters only `\cref` them and state differences.
- Author/advisor were not filled in → `\author{TODO: author}`, `TODO: advisor`.

---------------------------------------------------------------------------------------------------------------------

## 1. Full outline

**Front matter**: title page (title, TODO author/advisor, date, repo URL + commit hash) · Abstract · Executive summary
(1–2 pp.: three tiers of conclusions + Table ES1 cross-phase summary) · Notation (symbol table) · Contents / List of figures / List of tables.

**Ch. 1 Introduction**
1.1 The scientific question (BH vs NS from a single X-ray observation; physical motivation: surface vs horizon, disc/boundary layer, variability time-scales)
1.2 Why test on sources never seen in training (the source is the unit of generalisation; within-source correlation)
1.3 Data leakage: definition, how observation-wise splits leak, the size of the leak measured here (v1/v2: +0.04 to +0.16 BA); comparison with Pattnaik+2021 / Garg+2026
1.4 Labels: dynamically confirmed BHs only (BlackCAT → Casares & Jonker 2014 → Marcel+2026), NS by type-I bursts / pulsations; candidates only as sensitivity
1.5 Design principles: pre-registration, one primary per sub-analysis, strict CI rule, nested selection, decision log — and the explicit caveat that every pre-registration was written **after** the previous versions' results
1.6 Reading guide (phase map v1–v14, status tags)

**Ch. 2 Data sources and physical feature extraction** (every quantity: formula, unit, code function, handling of non-positive / missing values)
2.1 Instruments, data modes and catalogues (overview table)
2.2 Source labelling rules by version (BlackCAT Table 4, Galloway+2008, Casares & Jonker 2014, Patruno & Watts 2021, Marcel+2026, MINBAR, Liu+2006/2007)
2.3 Observation eligibility and time-stratified sampling (algorithm; RXTE and NICER variants; seeds)
2.4 RXTE/PCA Standard-2 spectra: FITS content; background subtraction (EXPOSURE, BACKSCAL, AREASCAL); deadtime (v1 good-xenon lower bound, v2+ GOF Standard-1 recipe); common energy grid (45 bins 4.908–25.008 keV, edges tabulated; 50-bin 2.883–25.008 keV grid for v3b); per-PCU per-keV rates; error propagation; F, S/N and quality rules; response check (Γ=2 folded power law, `pl2`); XSPEC cross-check
2.5 Spectral representations A, B, H, HI, H+B, HI+A, B3, H3, R, H_R (exact bin index ranges of the four colour bands)
2.6 HEXTE cluster-B high-energy colours X1, X2 (v4b3)
2.7 Type-I burst handling: Standard-1 1-s detector (v4), MINBAR matching (GTI→UTC, field-of-view rule; v7b1), NICER burst rule (v9)
2.8 Standard-1 timing: rows and PCU-on rule; two-group cospectrum (v5); all-pairs estimator + single-PCU auto-power hybrid (v6); binning (sinc²) correction; background; median over rows; signed square root; bands T1–T3; νPν centroid ν_c (9 log bins); state index (0.1–4 Hz rms, RM06 thresholds; v7a)
2.9 RXTE event mode 4–1024 Hz (v8c): event rule, 16-s segments, ratio of means and delta-method SE, null band, post hoc null subtraction
2.10 NICER/XTI (v9–v13): streaming/prefix/full reading; good intervals; 128-s segments; MPU all-pairs cospectrum (ratio of means); colours c1, c2; T bands; 0.1–10 Hz state; ν_c (13 octave bins); background proxy (12–15 keV ratio, v10); 3C50 background, correction and screening (v12/v13); 3C50-GTI restriction (v13); Lorentzian fits (v11c)
2.11 MAXI/GSC (v7c, v8d, v9c): cuts, SC, HC, RelInt, C4; HI4PI N_H and tbabs transmission correction
2.12 Feature summary table (all features, units, code function, missing-value rule)

**Ch. 3 Data model and ML interface**
3.1 Notation: X ∈ ℝ^{n×p}, y ∈ {0,1}^n (1 = BH), g ∈ {1..S}^n, observation IDs, sample weights w, fold map, OOF vector ŝ ∈ [0,1]^n, source score s̄_k, threshold rule
3.2 From files to matrices (general recipe as pseudo-code; joins by `obs_id`; `fill_missing`)
3.3 Array catalogue (each stored array once: file, key/column, shape, dtype, unit, meaning)
3.4 TikZ: design matrix with LOSO split (rows grouped by source; y, g columns; held-out block; scaler fitted on training rows only)
3.5 TikZ: end-to-end data flow with script numbers (01–64)
3.6 Worked example: first rows of the real v2 design matrices (H, HI, a few A/B bins) and of the NICER feature table, read from the repo files
3.7 Leakage controls implemented in code (fold assertions, train-only scaling/imputation, label-free residualisation, nested threshold)
(Per-version array tables are placed in each phase chapter, Section "Data structure in this phase", and reference 3.3.)

**Ch. 4 Machine-learning methods** (each: role/versions; decision function and probability; training objective as implemented in scikit-learn 1.8.0 with the repo settings; weights; pre-processing; score output; pseudo-code; hyper-parameter table with `config.py` names, inner vs outer; assumptions/limitations; implementation fixes)
4.1 Shared components: StandardScaler, class-balanced weights, source-equal weights (`v4lib.source_equal_weights`, incl. the 2026-10-01 scale fix), score conventions
4.2 DummyClassifier · 4.3 Logistic Regression · 4.4 Random Forest · 4.5 ExtraTrees · 4.6 HistGradientBoosting · 4.7 RBF SVM (sigmoid of decision function; Platt variant for v7c1) · 4.8 kNN classifier (prior correction; raw-feature variant for v7c1) · 4.9 QDA · 4.10 MLP (seed ensemble, weighted loss, early stopping)
4.11 CCTLR (v6) · 4.12 kNN regression for label-free colour residualisation · 4.13 Three-class reproduction of de Beurs+2022 (v7c1) · 4.14 Frozen threshold rule ν* (v11, v13) · 4.15 Not used: PCA (never used; "PCA" in the code is the RXTE instrument), 1D-CNN (pre-declared, skipped: no torch)

**Ch. 5 Evaluation and statistical inference** (formula + pseudo-code for each)
5.1 Leave-one-source-out: folds, OOF scores, fold checks
5.2 Source-level aggregation and threshold; `choose_threshold`; score shift raw − t + 0.5
5.3 Metrics: balanced accuracy; ROC AUC (Mann–Whitney with ties; weighted version); observation- vs source-level; state-stratified observation-level AUC; Brier and log loss (class-balanced, clipped)
5.4 Nested LOSO (v4a 1d/1e; v7c2 KNN inner LOSO, SVM inner grouped 5-fold) + TikZ figure
5.5 Source bootstrap: class-stratified draws (2000, seed 42, sorted names), percentile CI, paired differences, the "CI excludes 0" rule, vectorised implementation; stratified variant (v7a/v8); pooled multi-component bootstrap (v10) + TikZ figure
5.6 Permutation tests: colour-conditional source permutation (residuals, D, p, Holm); pooled permutation with instrument-membership strata (v10)
5.7 Mondrian conformal prediction at source level (LOSO and split) + TikZ figure
5.8 Observation-budget curves
5.9 Leaky observation-wise split (secondary diagnostic); agreement statistics; bridge check
5.10 Prospective (frozen) protocol: what was frozen, when (commit hashes), out-of-source models, ν* rule
5.11 Implementation checks (IC) and reproduction checks; multiple-comparison policy

**Ch. 6–11 Phase chapters** — each with the same 10 sections:
(1) Phase at a glance (tcolorbox) · (2) Motivation · (3) Pre-registration (per version: primary/secondary, decision rule, when written) · (4) Data (instrument/mode, band, epoch, catalogues, BH/NS counts, observations, exposure, attrition table, source list) · (5) Data structure in this phase (per-version array tables with real n×p) · (6) Models in this phase (table) · (7) Results (per version/sub-analysis; booktabs tables with CI; per-source tables; status tags) · (8) Interpretation · (9) Deviations & caveats · (10) Takeaway
- **Ch. 6 Phase 1 (v1–v3): spectral baselines** — results subsections v1 (8 sources), v2 (31 sources, bootstrap, hardness baselines, XSPEC), v3a, v3b, v3c, colour–colour wrap-up
- **Ch. 7 Phase 2 (v4): is the spectral information saturated?** — v4a (1a–1e), burst contamination, v4b3 HEXTE, v4b2 earlier epochs (+ v2 source-rule error), v4b1 all observations
- **Ch. 8 Phase 3 (v5–v6): low-frequency timing and frozen external validation** — v5 (S1/S2/S3), v6a primary, v6b estimator, v6c CCTLR, v6d permutation, v6e conformal, v6f budget, v6g proper scores, v6h robustness
- **Ch. 9 Phase 4 (v7–v8): state conditioning — the problem is the hard state** — v7a, v7b1 (MINBAR), v7b2 (persistent BHs), v7c1/v7c2/v7c3 (de Beurs, MAXI), v8a, v8b, v8c (exploratory), v8d
- **Ch. 10 Phase 5 (v9–v10): NICER and cross-instrument pooling** — v9a, v9b, v9c, v10c, v10a, v10b (explicitly "overall evidence, not independent confirmation")
- **Ch. 11 Phase 6 (v11–v13): prospective tests on new NICER observations and 3C50** — v11a–d, v12a–b, v13a–b (explicit: same sources; v12 RF post hoc, v13 RF pre-specified)

**Ch. 12 Synthesis across phases (v14)**: all primaries v1–v13 in one table; timing-gain table and ν_c table from `results/final_*.csv`; `figures/final/summary_across_versions.png`; the three evidence tiers; independence ladder (what is and is not independent).
**Ch. 13 Limitations** · **Ch. 14 Future work** · **Ch. 15 Open questions for discussion** (5 questions, see §4 below)
**References** (`references.bib`, natbib author–year; uncertain bibliographic fields get `note = {TODO: verify}`)
**Appendices**: A hyper-parameters (every model, every version) · B reproduction (run scripts, script→output map, data locations, `downloads.jsonl` SHA256 records: 50,773 lines, environment: Python 3.12, numpy 2.4.4, pandas 2.3.3, scipy 1.17.1, scikit-learn 1.8.0, astropy 7.2.0, matplotlib 3.10.9, HEASoft 6.37.1) · C pre-registration summary table (v1–v13: written when, after which results, approval, primary, verdict) · D decision-log summary (post hoc flags) · E glossary (zh-TW → EN terms as specified)

---------------------------------------------------------------------------------------------------------------------

## 2. Figure / table → section map

### 2a. Repository figures (copied unchanged to `report_en/figures/<same sub-path>`)
| Repo figure | Section |
|---|---|
| `figures/step2_two_sources.png` | 2.4 (FITS/background illustration) and 6.4 |
| `figures/step3_dataset_diagnostics.png` + `figures/v2/step3_dataset_diagnostics.png` (subfigure pair) | 6.4 Data |
| `figures/step3_spectra_by_source.png` + `figures/v2/step3_spectra_by_source.png` | 6.4 Data / 2.5 |
| `figures/step3_response_variation.png` + `figures/v2/step3_response_variation.png` | 2.4 response check |
| `figures/v3c/step3_dataset_diagnostics.png`, `v3c/step3_spectra_by_source.png`, `v3c/step3_response_variation.png` | 6.4 (v3c candidates) |
| `figures/step4_loso_scores.png` + `figures/v2/step4_loso_scores.png` | 6.7 v1 / v2 results |
| `figures/step5_hid_errors_LogReg.png`, `step5_hid_errors_RandomForest.png` (+ v2 versions) | 6.7 error analysis |
| `figures/step5_per_source_A_vs_B.png`, `step5_score_vs_rate.png` (+ v2 versions) | 6.7 error analysis |
| `figures/v3/v3a_H_vs_HplusB_source_scores.png` | 6.7 v3a |
| `figures/v3/v3b_soft_colour_by_source.png` | 6.7 v3b |
| `figures/v3/v3c_candidate_scores.png` | 6.7 v3c |
| `figures/final/colour_colour_decision_boundary.png` | 6.7 wrap-up / 6.8 |
| `figures/v4/v4a_forest_source_auc.png`, `v4a_colour_boundaries.png` | 7.7 v4a |
| burst grid (6 panels): `v4/burst_candidates/4U1636-53_50030-02-04-00.png` (true burst), `4U1728-34_50030-03-05-03.png` (true burst), `GRS1915+105_50703-01-11-00.png` (auto false positive, heartbeat), `XTEJ1118+480_50407-01-09-00.png` (auto false positive, hard-state flare), `KS1731-260_50031-02-03-01.png` (missed by auto, burst by eye), `GROJ1655-40_90428-01-01-07.png` (rejected noise candidate) | 7.7 burst; 2.7 |
| `figures/v4b3/v4b3_hexte_colours.png` | 7.7 v4b3 / 2.6 |
| `figures/v4b2/v4b2_scores_by_epoch.png` | 7.7 v4b2 |
| `figures/v4b1/v4b1_source_scores.png` | 7.7 v4b1 |
| `figures/v5/v5_timing_vs_colour.png` | 8.7 v5 |
| `figures/v6/v6a_external_sources.png`, `v6c_timing_evidence_map.png`, `v6f_budget_curves.png` | 8.7 v6a / v6c / v6f |
| `figures/v7/v7_summary.png` | 9.7 overview |
| `figures/v7a/v7a_rms_vs_colour_by_source.png`, `v7a_auc_by_state.png` | 9.7 v7a; 2.8 state index |
| v7b1 grid (6 panels): 4 `disagree_*` + `agree_4U1728-34_50030-03-05-03.png`, `agree_GS1826-238_91017-01-02-03.png` (folder has 14 files, not hundreds) | 9.7 v7b1 |
| `figures/v7b2/v7b2_colour_positions.png` | 9.7 v7b2 |
| `figures/v7c/v7c3_rxte_vs_maxi.png` | 9.7 v7c3 |
| `figures/v8/v8_summary.png`, `figures/v8d/v8d_nh_control.png` | 9.7 v8a–d |
| `figures/v9/v9_nicer.png`, `v9_summary.png`, `v9c_maxi_c4_strata.png` | 10.7 v9 |
| `figures/v10/v10_pooled.png` | 10.7 v10 |
| `figures/v11/v11_prospective.png` | 11.7 v11 |
| `figures/v12/v12_background.png` | 11.7 v12 |
| `figures/v13/v13_prospective.png` | 11.7 v13 |
| `figures/final/summary_across_versions.png` | 12 Synthesis |

### 2b. TikZ method diagrams (drawn in LaTeX)
| Diagram | Section |
|---|---|
| T1 End-to-end data flow (HEASARC / MAXI / NICER / catalogues → scripts → npz/CSV → (X, y, g) → LOSO → OOF → source scores → bootstrap/permutation → metrics/figures), script numbers on boxes | 3.5 |
| T2 Design matrix and LOSO split (rows grouped by source, y and g columns, held-out block, train-only scaler) | 3.4 |
| T3 Nested LOSO (outer fold → inner LOSO over 30 sources → selection → refit → outer prediction) | 5.4 |
| T4 Class-stratified source bootstrap and paired differences | 5.5 |
| T5 Timing-feature pipeline (light curve → rows/segments → PCU/MPU FFTs → all-pairs cospectrum → band rms → νPν → ν_c) | 2.8 |
| T6 Source-level Mondrian conformal prediction sets | 5.7 |
| T7 Pre-registration / data / freeze timeline v1–v13 (independence ladder) | 1.5 and 12 |

### 2c. New data figures (only where the repo has none; matplotlib, read-only from committed files; saved in `report_en/figures/generated/`, script `make_figures.py`, caption "Generated for this report from …")
| New figure | Source file(s) | Section |
|---|---|---|
| G1 Sample sizes per version (sources BH/NS, observations) | `data/*/sources.csv`, `data/*/observations.csv`, npz | 1.6 / 12 |
| G2 Mean count-space spectra (BH vs NS, A and B) with the four colour bands shaded | `data/v2/processed/features.npz` | 2.5 |
| G3 Real design matrix heat-map (v2, 456×45 B-shape, rows grouped by source, y/g strips) | `data/v2/processed/features.npz` | 3.4 / 3.6 |
| G4 Leakage: LOSO vs observation-wise 5-fold BA for every representation/model (v1, v2) | `results/*secondary_observation_split.csv`, `results/*metrics_observation_level.csv` | 1.3 / 6.7 |
| G5 Phase 1–2 forest plot of paired differences vs H-LR (v3a, v3b, v4a 1e, v4b3, v4b2, v4b1) | `results/v3/*_bootstrap.csv`, `results/v4*/…bootstrap.csv` | 7.8 |

### 2d. Tables (booktabs; long ones as longtable)
| Table | Section | Source |
|---|---|---|
| ES1 Cross-phase summary of primaries | Exec. summary | reports + results CSVs |
| N1 Notation | Notation | — |
| 2.1 Instruments/modes/catalogues; 2.2 labelling rules by version; 2.3 energy grid edges (45 and 50 bins); 2.4 colour band → bin indices; 2.5 timing bands (Fourier index ↔ Hz, RXTE Std1 / event / NICER); 2.6 ν_c bins (v6 9 bins, NICER 13 bins); 2.7 feature summary | Ch. 2 | `config.py`, npz, code |
| 3.1 Array catalogue; 3.2 example rows (v2 H/HI/A/B); 3.3 example rows (NICER features) | Ch. 3 | npz/CSV |
| 4.x one hyper-parameter table per model (+ Appendix A master table) | Ch. 4 | `config.py`, `v4lib.py`, `v7lib.py` |
| 5.1 Procedures summary (statistic, null/resampling unit, seed, n) | Ch. 5 | code |
| Per phase: at-a-glance box; pre-registration table; data summary; attrition table (`results/*/attrition_*.csv`); source list with labels/evidence and n_obs; per-version array tables (real n×p); models table; results tables with CIs; per-source result tables; deviations table | Ch. 6–11 | results CSVs, data CSVs, decision_log |
| 12.1 all primaries; 12.2 timing gains (`results/final_timing_gain_across_versions.csv`); 12.3 ν_c differences (`results/final_nuc_difference_across_versions.csv`) | Ch. 12 | final CSVs |
| A.1 master hyper-parameter table; B.1 run scripts; B.2 script → output map; B.3 data locations; B.4 environment; C.1 pre-registrations; D.1 decision-log summary; E.1 glossary | Appendices | — |

---------------------------------------------------------------------------------------------------------------------

## 3. Inventory of ML models and statistical procedures actually used

### 3a. Classifiers / estimators
| Model | Versions | File : function / class | Role |
|---|---|---|---|
| DummyClassifier(strategy='prior') | v1, v2 | `07_train_eval.py` (`MODELS['Dummy']`) | baseline |
| Logistic Regression (StandardScaler → LR, L2, C=1, lbfgs, balanced) | v1–v13 | `07_train_eval.py`; `v3lib.MODELS`; `v4lib.V4Model` ('LogReg'); `v6lib.CCTLR.lr`; `v7lib.C2Model`; `39_v7c2_analysis.M` | primary model v1–v11 (H-LR baseline from v4) |
| Random Forest (500 trees, sqrt, min leaf 2, balanced; inner 200 trees) | v1–v13 | `07`; `v3lib.MODELS`; `v4lib.V4Model`; `v7lib.C2Model` | secondary; primary in v8d, v12b (post hoc choice), v13a (pre-specified) |
| ExtraTrees | v4a | `v4lib.V4Model` | exploratory |
| HistGradientBoosting | v4a | `v4lib.V4Model` | exploratory |
| RBF SVM (balanced, score = sigmoid(decision function)) | v4a; v7c2 | `v4lib.V4Model`; `v7lib.C2Model` | exploratory / descriptive |
| RBF SVM with Platt probabilities, 3-class | v7c1 | `37_v7c1_repro.fold` | reproduction of de Beurs+2022 |
| kNN classifier (scaled, prior-corrected) | v4a; v7c2; v8d | `v4lib.V4Model`; `v7lib.C2Model` | exploratory / descriptive |
| kNN classifier k=24 on raw features, 3-class vote fractions | v7c1 | `37_v7c1_repro.fold` | reproduction |
| QDA (reg 0.1, equal priors) | v4a | `v4lib.V4Model` | exploratory |
| MLP (32,) seed ensemble (5 outer / 3 inner seeds) | v4a | `v4lib.V4Model` | exploratory |
| Nested automatic selection (8 algorithms × 4 representations × grid, inner LOSO, threshold) | v4a 1d/1e | `v4lib.nested_fold`, `16_v4a_algorithms.py` | v4 primary |
| CCTLR (H-LR logit + Student-t timing log-likelihood ratio) | v6c | `v6lib.CCTLR`, `cctlr_loso` | new method, descriptive |
| kNN regression (k=25, label-free colour residualisation) | v6d, v9b, v10b, v11b, v12a, v13b | `v6lib.source_residuals` | inside the permutation tests |
| Frozen ν* rule (hard-like and ν_c < ν* → BH) | v11, v13 | `57_v11_analysis.py`, `63_v13_analysis.py` | descriptive |
| Zero-centred Lorentzian WLS fits (1 vs 2 components, BIC) | v11c | `v11lib.fit_lorentz` | descriptive feature |
| Not used: PCA (principal components) — never used; 1D-CNN — skipped (no torch) | — | — | — |

### 3b. Evaluation / inference procedures
| Procedure | Versions | File : function |
|---|---|---|
| Leave-one-source-out folds + checks | all | `07_train_eval.py`; `v3lib.run_loso`; `v4lib.loso_scores`; `sklearn LeaveOneGroupOut` |
| Leaky observation-wise stratified 5-fold (diagnostic) | v1, v2 | `07_train_eval.py` |
| Source mean score, fixed 0.5 threshold | all | `v3lib.per_source`; `v4lib.src_table` |
| Nested threshold (max inner source BA, ties → closest to 0.5) + score shift | v4a | `v4lib.choose_threshold`, `to_oof` |
| Inner selection by source AUC (KNN inner LOSO, SVM inner GroupKFold(5)) | v7c2, v8d | `v7lib.c2_outer`, `39_v7c2_analysis.outer` |
| Balanced accuracy, ROC AUC (Mann–Whitney, ties ½), weighted AUC | all | `v3lib.metric_triplet`; `v4lib._boot_metrics`; `v7lib.auc_ba` |
| Class-stratified source bootstrap (2000, seed 42) + paired differences | v1–v13 | `09_bootstrap_sources.py`; `v3lib.bootstrap`; `v4lib.paired_bootstrap`; `v7lib.boot_draws`; `v8lib.src_boot` |
| State-stratified observation-level bootstrap | v7a, v8a–c, v9a, v10a, v11a, v12b, v13a | `34_v7a_states.strat_eval`; `v8lib.strat_boot`, `summarize`, `verdict` |
| Pooled multi-component bootstrap | v10a | `v10lib.pooled_boot` |
| Proper scoring rules (class-balanced source log loss, Brier) with bootstrap | v6g | `v6lib.proper_score_bootstrap` |
| Colour-conditional source permutation test + Holm | v6d, v9b, v10b, v11b, v12a, v13b | `v6lib.source_residuals`, `perm_test`, `holm` |
| Pooled permutation with instrument-membership strata | v10b, v12a (pooled with RXTE) | `v10lib.pooled_perm` |
| Mondrian conformal prediction (source level, LOSO and split) | v6e | `v6lib.conformal_sets`, `conformal_loso` |
| Observation-budget curves | v6f | `v6lib.budget_curves` |
| Agreement (Spearman of OOF scores, label agreement) | v3a, v4 | `v3lib.agreement`; `v4lib.agreement_vs` |
| Bridge check (H_R vs H) | v4b2 | `22_v4b2_analysis.py` |
| Split-half reliability (odd/even rows/segments, Spearman–Brown) | v6, v8c, v10c | `29_v6_features.py`, `43_v8c_events.py`, `52_v10_nicer_full.py`, `v10lib.half_features` |
| Implementation checks (synthetic signals, reproduction to 1e-9) | v4–v13 | `test_v4lib.py` … `test_v11lib.py`; IC blocks in analysis scripts |
| Ratio-of-means estimator with delta-method SE | v8c, v9–v13 | `v8lib.hf_summary`; `v9lib.obs_features`; `v11lib.lb_se` |

---------------------------------------------------------------------------------------------------------------------

## 4. Proposed "Open questions for discussion" (Ch. 15)
1. Is an observation-level prospective confirmation on the same 16 BHs enough to claim the timing gain, and what minimum source-level test (new transients) would the advisor accept?
2. Should the ν_c result be framed as mass scaling, given no Eddington-ratio/distance control — and is collecting distances for ~60 sources worth it?
3. Is the label-free kNN residualisation too conservative when BHs cluster in colour (v9 observation), and would a pre-registered alternative (e.g. colour-window or matched design) be preferable?
4. RF vs LR: the timing gain is stable only for RF — report RF as the headline model despite RF being chosen post hoc in v12?
5. Which external data (Insight-HXMT, AstroSat, future NICER/XRISM transients) are realistic for a source-level test?

## 5. Discrepancies already found (will be marked `% CHECK:` in the LaTeX; CSV/code take precedence)
1. v2 report says the v1 good-xenon deadtime median was 0.15 %; `data/observations.csv` (v1) gives 0.31 % (matches the v1 report); 0.146 % is the median of `dtf_xe` in the **v2** sample.
2. LMC X-1 eligible pointings under the catalogue-median rule: pre-registration v7 says 419, report v7 says 450; `results/v7b2/attrition_catalog.csv` records 450 before the pointing cut (the catalogue-median count itself is not stored).
3. v9b post hoc colour-window Mann–Whitney p = 0.013, AUC 0.81: no committed script produces these numbers (only per-source values in `results/v9b/v9b_nuc_colour_window_post_hoc.csv`).
4. v9 pre-registration says ν_c uses "the v6 definition", but `v9lib.obs_features` weights the 13 octave bins by max(P_b, 0) without dividing by Δln ν (v6 divides by Δln ν); equivalent except for the lowest bin.
5. `38_v7c2_select.py` docstring still says matching within 0.35° on J-name positions; the code (and decision log) use Sesame positions within 0.1° (0.3° fallback).
(More will be collected while writing; all will be listed in the delivery summary.)
