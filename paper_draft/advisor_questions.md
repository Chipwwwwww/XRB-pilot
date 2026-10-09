# Paper draft: open issues and decisions for advisor discussion

Draft: `paper_draft/paper_draft.pdf` (from `main.tex`), built from repository commit `666c2e0`.
No analysis was re-run for the draft. Every item marked **not answered** below would need new work. Any new
inferential analysis should first get its own time-stamped plan, as in earlier rounds.

---

## The three decisions that matter most

1. **Is the main claim ready to submit, or should we wait for a new-source test?**
   - **What the draft claims.** A pre-specified, frozen RF test on 198 unseen NICER observations shows that low-frequency
     variability adds hard-like information beyond two colours: observation-level ΔAUC = +0.184 [+0.049, +0.337].
   - **The limits.** The same test at source level (+0.125 [−0.053, +0.303]) is not detected. All new observations come from
     sources already in the sample.
   - **Option (a):** submit now, framed as "confirmed on unseen observations of known sources; new-source confirmation
     pending". This is the current framing.
   - **Option (b):** first apply the frozen pipeline to BH/NS transients never used here (NICER data after the archive
     cut-off, or another mission), then submit with a source-level test.
2. **Should the two cheap re-analyses (B1, B3 below) be run before submission?** Both use existing data and could change
   the interpretation:
   - whether total rms alone explains the gain;
   - whether the gain survives equal weighting of sources and blocking by outburst.

   Each needs a new written plan before it is run.
3. **How should we describe the pre-specification and the AI assistance?**
   - The plans (`reports/preregistration_v*.md`) were drafted and self-approved by the analysis agent under the
     student's standing instructions. They were committed before each data download and never reviewed externally.
   - The draft calls them "time-stamped, internally pre-specified analysis plans". The disclosure of AI assistance is
     left as a visible placeholder in the Acknowledgements.
   - Decide the wording, whether to name the tooling, and whether to register the plan for any new-source test
     externally (e.g. OSF) before the data are seen.

---

## A. Must fix before submission (facts, methods, numbers)

| ID | Issue | Where | Proposed action |
|---|---|---|---|
| A1 | Full texts of the cited papers could not be opened from the writing environment (arXiv/ADS/publisher fetches blocked), so metadata were checked against search records only. **Not re-verified against full text:** the observation-wise 80:20 split of Garg+2026, and Pattnaik+2021's remark that hard/intermediate states are misclassified more often. Both are flagged with † in App. D. | §1, §5.3, App. D, `references.bib` | Read both papers and fix the wording if needed. |
| A2 | Bibliographic gaps, each shown as a visible `note` in the bibliography: no DOI for de Beurs+2022 and Remillard+2022; end pages for Wijnands & van der Klis 1999 and Jahoda+2006; volume/pages for Sunyaev & Revnivtsev 2000; publication status of Garg+2026 and Marcel+2026. | References | Complete from ADS, then delete the notes. |
| A3 | Authors, affiliations, corresponding author, acknowledgements, funding and AI-use statement are red placeholders. | Title page, Acknowledgements | Supply them. |
| A4 | Repository visibility and archival DOI are unconfirmed. | Data availability | Make the repository public or archive it (e.g. Zenodo) and cite the DOI. |
| A5 | The development-sample source rule missed 13 eligible bursters (found in v4b2). The draft discloses this in §2.2 but does not correct it. | §2.2 | Decide: disclose only, or re-run (that would be a new analysis). |
| A6 | ν_c is defined differently for RXTE (weights divided by the log bin width) and NICER (not divided), so the pooled test mixes definitions. | §4.5, App. C | Keep the caveat, or present only single-instrument ν_c tests. |
| A7 | The hard-like class uses 0.1–4 Hz and all PCA channels for RXTE, but 0.1–10 Hz and 2–10 keV for NICER. The classes are therefore not identical across instruments. | §3.3 | Already stated; decide whether a footnote quantifying the difference is needed. |
| A8 | The pooled test (v10a) recomputes the RXTE component on bootstrap draws over the union of sources, so its interval ([+0.044, +0.469]) differs slightly from the stand-alone v8a interval ([+0.048, +0.455]). The draft quotes v8a for the RXTE row. | Fig. 4, Table 2 | No change needed; mention in the response to referees if asked. |
| A9 | "16 confirmed BHs is nearly all with usable timing data" rests on the project's TAP queries (v8, v11 plans), not a published statement. | §2.1 | Keep the wording cautious, or list the 9 unused BHs and the reason each is unusable. |
| A10 | Target journal not chosen. The abstract is 294 words, above typical 250-word limits, and the format is generic `article`. | — | Choose the journal (MNRAS, ApJ or RASTI) and convert. |

## B. Re-analyses that could change the main scientific interpretation (none were run for this draft)

| ID | Question | Do committed results answer it? | Status |
|---|---|---|---|
| B1 | **Colours + total rms versus colours + T1, T2, T3.** Is the gain carried by the amount of variability or by its spectral shape? This is critical because hard-like itself is defined by r > 0.10. | No model with total rms as a single input exists. Only partial evidence: single-band ablations (RXTE: H+T1 0.926, H+T2 0.874, H+T3 0.654 hard-like AUC; NICER N1 gains T1 +0.048, T2 +0.143, T3 +0.115) and a brightness proxy (H+R+T − H+R = +0.069 [−0.013, +0.161]). | **Not answered** |
| B2 | **Background and timing-GTI consistency.** 3C50 drops high-background intervals from its own GTIs, but the timing features use all GTIs. | Checked for N3 only: the RF gain with GTI-restricted timing was +0.190 [+0.065, +0.330], and ν_c D fell from −0.43 to −0.30 (p = 0.41). Not checked for N1+N2. Background time variability was never modelled. | Partly answered |
| B3 | **Source-equal weighting and outburst correlation.** | Source-level metrics exist. RXTE: AUC +0.185 [+0.008, +0.403]. N1+N2: AUC +0.074 [−0.033, +0.206], balanced accuracy +0.173 [+0.004, +0.357]. N3: AUC +0.125 [−0.053, +0.303], balanced accuracy +0.099 [−0.053, +0.286]. N2 (LR): −0.013. Leave-one-BH-out ranges also exist (N3 RF +0.146 to +0.212). No observation-level AUC with 1/n_s weights, and no bootstrap blocked by outburst. | Partly answered |
| B4 | **Fair comparison with published models on identical data and splits.** | Only the de Beurs+2022 MAXI results were reproduced (v7c1), and the leakage size of observation-wise splits was measured in our own data (+0.04 to +0.16 balanced accuracy). Neither the Pattnaik nor the Garg model was re-implemented, because their processed spectra are not public. | **Not answered** |
| B5 | **New-source test** of the frozen N3 pipeline and RF. This is the decisive missing evidence. | — | Not done |
| B6 | **Stratum defined without timing**, e.g. a spectral hard-state criterion, so the result is not conditional on an rms selection. | — | Not done |
| B7 | **Physical controls:** Eddington ratio (needs distances), inclination, NS subclass (atoll / Z / AMXP). | Only a log-count-rate proxy was tried. | Not done |
| B8 | **Joint summary of all hard-like gains that accounts for shared data** (instead of listing them in Fig. 4). | — | Not done |

## C. Extensions that can wait for later papers

- C1 ν_c and mass scaling. This needs masses, distances and an Eddington-ratio control. It is currently a secondary lead only.
- C2 High-frequency (event-mode) timing with a passing implementation check. The v8c results are exploratory.
- C3 MAXI and cross-instrument transfer of a single model. None has been attempted, and similar behaviour across
  instruments is not transfer.
- C4 Calibrated or conformal prediction sets for a usable classifier (some work exists in v6).
- C5 Recovering the 2017–2018 NICER observations lost to 3C50 failures (reprocessing, or the SCORPEON background model).
- C6 Applying the classifier to BH candidates (v3c was descriptive only).

## Further questions for the advisor

1. Is Fig. 4, with every round on one axis plus annotation columns, the right way to show the timing gain? Or should the
   main text show only the N3 test (Fig. 5) and move Fig. 4 to an appendix?
2. Should the ν_c secondary result stay in the main text (§4.5) or move entirely to Appendix C?
3. Should the MAXI and high-frequency summaries (Appendix B) be cut to reduce length?
