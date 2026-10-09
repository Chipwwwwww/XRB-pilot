# paper_draft — first research-paper draft (for advisor discussion)

An English research-paper draft that integrates the XRB-pilot analyses around one question. For black hole versus
neutron star classification of sources excluded from training: what do X-ray colours capture, and does low-frequency
variability improve classification within hard-like observations?

**No research analysis was re-run for this draft.** No model was re-fitted, no model search was repeated, no
bootstrap or permutation was recomputed, and no astronomical data were downloaded. The draft only reads committed
results, code, plans and logs. It redraws figures from committed result tables and does simple arithmetic on them
(counts, minima and maxima, one difference of two committed balanced accuracies); each such case is stated in the
figure captions and in `claim_evidence.csv`.

## Provenance

| Item | Value |
|---|---|
| Repository | `Chipwwwwww/XRB-pilot` |
| Commit used | `666c2e0ad6c490a5014d4290f3becc571e07132d` (HEAD of `master` and of `claude/clever-bardeen-222k3u` when the draft was started) |
| Technical report used for context | `report_en/main.pdf`: 205 pages, PDF creation date 2026-10-09 11:31 UTC; last changed in commit `666c2e0` ("report_en: flowcharts …") |
| Main evidence | `results/**.csv`, `data/v*/processed/*.csv`, `scripts/config.py`, `scripts/v*lib.py`, analysis scripts 34, 44, 49, 57, 59, 63, `reports/preregistration_v*.md`, `reports/decision_log.md` |
| Draft date | 2026-10-09 |

## Files

| File | What it is |
|---|---|
| `main.tex` | Paper source: 21 pages, about 5,200 words of main text excluding floats, and a 294-word abstract. |
| `references.bib` | Bibliography; unverified fields are flagged in visible `note` fields (see below) |
| `paper_draft.pdf` | Compiled draft (copy of `main.pdf`) |
| `figures/` | `fig2_colour_ablation.pdf`, `fig3_states.pdf`, `fig4_timing_gain.pdf`, `fig5_v13.pdf`, `figA1_nuc.pdf` (Fig. 1 is TikZ inside `main.tex`) |
| `scripts/make_figures.py` | Redraws Figs. 2–5 and C.1 from committed CSVs |
| `scripts/build_claim_evidence.py` | Builds `claim_evidence.csv`. It re-reads each number from the committed source row, compares it with the value stated in the paper, and checks that the number appears in `main.tex`. |
| `claim_evidence.csv` | Claim–evidence table: 50 automatically checked claims and 18 manual rows. Columns: claim ID, section, claim, values, source file and rows, sample and unit, primary/descriptive/post hoc status, required limitations, verification status. |
| `advisor_questions.md` | Open issues ranked A (must fix), B (analyses that could change the interpretation), C (later), plus decisions for the advisor |

## Build

Requirements: TeX Live with `latexmk`, `natbib`, `tikz`, `booktabs`, `cleveref`, `lineno`; Python 3 with `pandas`,
`numpy`, `matplotlib`.

```bash
# from the repository root
python paper_draft/scripts/make_figures.py          # optional: redraw figures from committed CSVs
python paper_draft/scripts/build_claim_evidence.py  # optional: re-check every number in the paper
cd paper_draft && latexmk -pdf main.tex && cp main.pdf paper_draft.pdf
```

The last build had 0 errors, 0 undefined references or citations, and 0 overfull boxes. The claim check passed 50 of
50 automatic claims.

## Figures and their sources

All data figures were **redrawn** for the paper: presentation only, no statistic recomputed. No repository PNG is
reused.

| Paper figure | Script function | Committed source |
|---|---|---|
| Fig. 1 (design) | TikZ in `main.tex` | counts from Table 1 sources below |
| Fig. 2 colour baseline and ablations | `fig2` | `results/v3/v3a_bootstrap.csv`, `results/v3/v3b_bootstrap.csv`, `results/v4b3/v4b3_bootstrap.csv`, `results/v4/v4a_bootstrap.csv`, `results/v4b1/v4b1_bootstrap.csv` |
| Fig. 3 state dependence | `fig3` | `results/v7a/states.csv`, `results/v7a/state_stratified_metrics.csv`, `data/v12/processed/nicer_corrected_screened.csv`, `results/v9a/v9a_metrics.csv`, `results/v11/v11a_metrics.csv`, `results/v12/v12b_gain.csv`, `results/v13/v13a_gain.csv` |
| Fig. 4 hard-like timing gains | `fig4` | `results/final_timing_gain_across_versions.csv`, `results/v10a/v10a_pooled_gain.csv` (N1 full-file LR row) |
| Fig. 5 N3 test | `fig5` | `results/v13/v13a_gain.csv`, `results/v13/v13a_gti_restricted.csv`, `results/v13/v13a_influence.csv` |
| Fig. C.1 ν_c | `figA1` | `results/final_nuc_difference_across_versions.csv`, `results/v11/v11b_post_hoc_screens.csv`, `results/v12/v12a_nuc.csv`, `results/v13/v13b_nuc.csv` |

Every figure that spans rounds labels its rows with:
- the data status: development, new sources, unseen observations, or re-use;
- the background treatment: none or 3C50;
- the model: LR or RF;
- the role: primary or descriptive;
- when the model was fixed.

These labels keep rounds that share data from looking like independent replications.

The colours were checked with the dataviz palette validator: BH/NS are blue/orange and LR/RF are violet/green, and all
checks passed.

## Literature verification (2026-10-09)

Direct page fetching (arXiv, ADS, publishers) was **blocked in this environment**: `curl` returned 403 from the egress
proxy and WebFetch failed DNS lookups. Bibliographic fields were therefore checked against **search-engine records** of
arXiv, ADS, publisher, institutional and HEASARC pages. Full texts were not re-read in this session.

| Key | Checked | Still open |
|---|---|---|
| Pattnaik+2021 (arXiv:2012.06934) | 8 authors, title, MNRAS 501(3) 3457–3471, DOI 10.1093/mnras/staa3899 | state remark (hard/intermediate misclassified) from secondary record + project reading |
| de Beurs+2022 (arXiv:2204.00346) | authors, title, ApJ 933, 116 (one source: co-author bibliography) | DOI |
| Garg+2026 (arXiv:2601.18139) | 8 authors, title, submission date, abstract content (flux / flux+errors NNs, 90–94 %, fit parameters incl. data variance) | observation-wise 80:20 split (from the project's earlier reading; not visible in abstract); journal status |
| Done & Gierliński 2003 (astro-ph/0211206) | title, MNRAS 342, 1041, DOI 10.1046/j.1365-8711.2003.06614.x | end page 1055 (from repo records) |
| Sunyaev & Revnivtsev 2000 (astro-ph/0003308) | title, authors, A&A, abstract content | volume/pages 358, 617–623 (from repo records) |
| Gardenier & Uttley 2018 (arXiv:1809.06093) | title, MNRAS 481(3) 3761–3781, DOI 10.1093/mnras/sty2524 | — |
| Marcel+2026 (arXiv:2606.19952) | title "Accreting stellar-mass black holes", 6 authors, submission date | venue/status. The technical report's `TODO` for this entry was **not** copied. |
| Remillard+2022 (arXiv:2105.09901) | 14 authors, title, AJ 163, 130 (NICER workshop slides) | DOI |
| Heil+2015; Klein-Wolt & van der Klis 2008; Burke+2017; Galloway+2020; Jahoda+2006; Wijnands & van der Klis 1999; Galloway+2008; Corral-Santana+2016; Remillard & McClintock 2006 | journal, volume, pages (and DOI where given) | end pages of Jahoda+2006 and Wijnands & van der Klis 1999 |

`McHardy2006` and `Gendreau2016` are in `references.bib` but not cited, so they do not appear in the PDF.

## Source inconsistencies found and how they were handled

1. **MAXI single-colour baseline.** An early draft sentence used 0.364, the uncorrected RF model in
   `results/v7c/v7c2_bootstrap.csv`. The N_H-corrected comparison model is 0.361 (`results/v8d/v8d_bootstrap.csv`). The
   paper now uses 0.361.
2. **Pooled versus stand-alone RXTE interval.** The v10a pooled test recomputes the RXTE component on draws over the
   union of sources, giving [+0.044, +0.469] against v8a's [+0.048, +0.455]. The paper uses v8a for the RXTE row and
   v10a only for the pooled row (A8 in `advisor_questions.md`).
3. **ν_c definitions differ** between RXTE (v6: weights divided by the log bin width) and NICER (v9: not divided).
   This is a technical-report `CHECK`, and it is stated in App. C.
4. **Development-sample source rule.** Thirteen eligible bursters were missed (decision log, v4b2). This is disclosed
   in §2.2 and not corrected.
5. **Literature claims.** The technical report and the Chinese reports state Garg's 80:20 observation split and that
   Pattnaik labelled candidates as BHs. These could not be re-verified against the full texts here, so they are flagged
   in the paper (App. D, †) and in A1.
6. **Unchanged report CHECKs.** The technical report's other `% CHECK` items (LMC X-1 eligible count, v9b post hoc
   Mann–Whitney without a committed script, v7c2 docstring, v7b2 file label, MAXI J1820+070 classification) concern
   numbers the paper does not use. They were left unchanged.

## Pending items (visible in the PDF as red placeholders)

- Author names and order, affiliations, corresponding e-mail.
- Acknowledgements, funding, AI-assistance disclosure.
- Repository visibility and archival DOI.
- Journal keywords and target-journal format.

## What was not changed

No file outside `paper_draft/` was modified: analysis code, configs, raw or processed data, result tables,
`report_en/` and `reports/` are untouched. Nothing was pushed, merged or published.
