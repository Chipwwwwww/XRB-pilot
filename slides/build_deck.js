// Builds slides/XRB_ML_to_GW_localization.pptx
// Numbers come from paper_draft/main.tex (committed results); nothing is re-computed here.
// Run: NODE_PATH=<dir with pptxgenjs, react, react-dom, react-icons, sharp> node slides/build_deck.js
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const OUT = path.join(__dirname, "XRB_ML_to_GW_localization.pptx");
const IMG_CC = path.join(__dirname, "assets", "rxte_colour_planes.png");

const THEME = {
  name: "XRB to GW",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0B1426", lt1: "FFFFFF", dk2: "3A4660", lt2: "EEF2F7",
    accent1: "E8811E", // X-ray amber (highlight / NS)
    accent2: "2F6FD0", // BH blue
    accent3: "6E56CF", // violet (LR)
    accent4: "1E8E5E", // green (RF / detected)
    accent5: "8A94A6", // neutral grey
    accent6: "C9483B", // red (caveat)
    hlink: "2F6FD0", folHlink: "6E56CF",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "From X-ray binaries to GW sky localization";
pres.author = "Cheng-Yen Lin";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ---------- layouts ----------
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.0, w: 11.7, h: 1.9, fontSize: 44, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.15, w: 11.0, h: 1.0, fontSize: 20, color: "C9D3E6", valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "meta", type: "body", x: 0.8, y: 6.2, w: 11.0, h: 0.6, fontSize: 14, color: "9AA6BD", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "SECTION_DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.3, w: 11.7, h: 1.6, fontSize: 40, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.1, w: 11.0, h: 1.0, fontSize: 20, color: "C9D3E6", valign: "top", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.3, y: 6.95, w: 0.6, h: 0.3, fontSize: 10, color: "9AA6BD", align: "right" },
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.95, fontSize: 30, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "XRB pilot  →  ML for GW sky localization   ·   Cheng-Yen Lin   ·   ML project discussion", options: { x: 0.6, y: 6.95, w: 9.0, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.3, y: 6.95, w: 0.6, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
});

// ---------- helpers ----------
async function iconData(Comp, hex, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + hex, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
async function iconCircle(slide, Comp, x, y, d, fill, name) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: name + " circle" });
  const pad = d * 0.25;
  slide.addImage({ data: await iconData(Comp, "FFFFFF"), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, altText: name, objectName: name + " icon" });
}
function card(slide, x, y, w, h, fill, name) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: name });
}
const txt = (slide, text, opts) => slide.addText(text, Object.assign({ isTextBox: true, margin: 0, valign: "top", color: C.text1 }, opts));
const chip = (slide, text, x, y, w, fill, name) => {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.32, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: name + " chip" });
  txt(slide, text, { x, y, w, h: 0.32, fontSize: 12, bold: true, color: C.background1, align: "center", valign: "middle" });
};
const CHART_FONT = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt", legendFontFace: "+mn-lt" };
const chartBase = () => Object.assign({
  catAxisLabelColor: HEX.dk2, valAxisLabelColor: HEX.dk2, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  dataLabelFontSize: 12, dataLabelColor: HEX.dk1, titleFontSize: 14, titleColor: HEX.dk1, legendFontSize: 12,
  valGridLine: { color: "DDE3EC", size: 0.75 }, catGridLine: { style: "none" },
}, CHART_FONT);

(async () => {
  // =============== 1. Title ===============
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
  s.addText("Black hole or neutron star? ML on X-ray binaries — and what's next", { placeholder: "title" });
  s.addText("Key results from the XRB pilot, and a proposed next project: machine learning for gravitational-wave sky localization", { placeholder: "body" });
  s.addText("Cheng-Yen Lin   ·   NTHU Institute of Astronomy   ·   ML project discussion with Albert Kong & Surojit Saha", { placeholder: "meta" });
  await iconCircle(s, fa.FaSatelliteDish, 0.8, 0.8, 0.9, C.accent1, "X-ray");
  await iconCircle(s, fa.FaWaveSquare, 1.9, 0.8, 0.9, C.accent2, "GW");
  s.addNotes("Albert asked for a few slides with key results from the X-ray binary experiment. Part 1 (slides 2-8) is the XRB pilot; part 2 (slides 9-13) is what I would like to do next: ML for GW sky localization.");

  // =============== 2. One-slide summary ===============
  pres.addSection({ title: "XRB pilot" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "XRB pilot" });
  s.addText("The XRB pilot in one slide", { placeholder: "title" });
  const sumCards = [
    [fa.FaPalette, C.accent2, "Two colours carry the spectral signal", "Two hardness ratios reach source-level AUC 0.92. Full spectra, more energy bands, 17× more data and an 8-algorithm search add nothing detectable."],
    [fa.FaAdjust, C.accent6, "Colours fail in hard-like states", "Colour-only AUC is 0.95 in soft-like but 0.65 in hard-like RXTE observations. NICER shows the same pattern."],
    [fa.FaChartLine, C.accent4, "Low-frequency timing fills the gap", "Adding rms in 3 bands (0.016–4 Hz) raises hard-like AUC. Confirmed on 198 unseen NICER observations with a frozen pipeline: +0.18."],
    [fa.FaCrosshairs, C.accent1, "Next: ML for GW sky localization", "Fast, calibrated skymaps for EM follow-up — tested with the same held-out, pre-specified discipline."],
  ];
  for (let i = 0; i < 4; i++) {
    const [Ic, col, head, body] = sumCards[i];
    const x = 0.6 + (i % 2) * 6.15, y = 1.55 + Math.floor(i / 2) * 2.65;
    card(s, x, y, 5.95, 2.4, i === 3 ? "FDF0E3" : HEX.lt2, "summary card " + (i + 1));
    await iconCircle(s, Ic, x + 0.3, y + 0.3, 0.75, col, head);
    txt(s, head, { x: x + 1.3, y: y + 0.3, w: 4.4, h: 0.75, fontSize: 20, bold: true, valign: "middle", fontFace: "Arial" });
    txt(s, body, { x: x + 1.3, y: y + 1.15, w: 4.4, h: 1.1, fontSize: 15, color: C.text2 });
  }
  s.addNotes("Three findings, then the proposal. AUC numbers are observation-level unless stated; all intervals are 95% source-bootstrap intervals of fixed out-of-sample predictions.");

  // =============== 3. Setup ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "XRB pilot" });
  s.addText("Question: BH or NS, for a source the model has never seen?", { placeholder: "title" });
  const stats = [["86", "X-ray binaries (RXTE + NICER)"], ["16", "dynamically confirmed BHs"], ["~1,750", "observations analysed"], ["13", "analysis rounds, each with a plan committed before its data"]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + (i % 2) * 2.95, y = 1.6 + Math.floor(i / 2) * 2.45;
    card(s, x, y, 2.75, 2.2, HEX.lt2, "stat card " + (i + 1));
    txt(s, stats[i][0], { x: x + 0.25, y: y + 0.25, w: 2.3, h: 0.95, fontSize: 48, bold: true, color: i === 1 ? C.accent2 : C.accent1, fontFace: "Arial" });
    txt(s, stats[i][1], { x: x + 0.25, y: y + 1.25, w: 2.3, h: 0.8, fontSize: 14, color: C.text2 });
  }
  const steps = [
    [fa.FaTags, "Labels", "BH: dynamical mass only. NS: type-I bursts or pulsations. Candidates never used for training."],
    [fa.FaSlidersH, "Features", "2 hardness ratios (colours) + fractional rms in 0.016–0.094, 0.1–1, 1–4 Hz."],
    [fa.FaProjectDiagram, "Models", "Logistic regression and random forest, hyperparameters fixed in advance."],
    [fa.FaBalanceScale, "Evaluation", "Leave-one-source-out; frozen models on unseen observations; 95% CIs by bootstrapping sources."],
  ];
  for (let i = 0; i < 4; i++) {
    const y = 1.6 + i * 1.2;
    await iconCircle(s, steps[i][0], 6.75, y + 0.05, 0.7, C.text2, steps[i][1]);
    txt(s, steps[i][1], { x: 7.65, y: y, w: 5.0, h: 0.35, fontSize: 17, bold: true, fontFace: "Arial" });
    txt(s, steps[i][2], { x: 7.65, y: y + 0.38, w: 5.05, h: 0.75, fontSize: 14, color: C.text2 });
  }
  s.addNotes("Instruments: RXTE/PCA (1996-2012) and NICER/XTI (2017+). The 16 confirmed BHs are nearly all of the 25 in Marcel et al. 2026 with usable timing data. Every test source is excluded from training, so the question is generalisation to new objects, not to new observations of known objects.");

  // =============== 4. Finding 1 ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "XRB pilot" });
  s.addText("Finding 1 · Two hardness ratios carry the spectral signal", { placeholder: "title" });
  card(s, 0.6, 1.6, 4.1, 4.9, HEX.lt2, "baseline stat card");
  txt(s, "0.923", { x: 0.9, y: 1.9, w: 3.6, h: 1.1, fontSize: 60, bold: true, color: C.accent2, fontFace: "Arial" });
  txt(s, "source-level AUC from two colours + logistic regression", { x: 0.9, y: 3.0, w: 3.6, h: 0.7, fontSize: 16, bold: true });
  txt(s, "95% CI [0.80, 0.99] · 31 RXTE sources (7 BH, 24 NS), 456 obs, leave-one-source-out", { x: 0.9, y: 3.75, w: 3.6, h: 0.8, fontSize: 13, color: C.text2 });
  txt(s, [
    { text: "Lesson: ", options: { bold: true, color: C.accent6 } },
    { text: "splitting by observation instead of by source inflated balanced accuracy by +0.04 to +0.16.", options: {} },
  ], { x: 0.9, y: 4.8, w: 3.6, h: 1.4, fontSize: 14, color: C.text1 });
  s.addChart(pres.charts.BAR, [{
    name: "ΔAUC vs two colours",
    labels: ["Full 5–25 keV shape  [−0.18, +0.05]", "Add 3–5 keV  [−0.07, 0.00]", "Add HEXTE 25–60 keV  [−0.18, +0.02]", "17× more observations  [−0.05, +0.04]", "Nested 8-algorithm search  [−0.40, +0.01]"],
    values: [-0.048, -0.018, -0.048, 0.0, -0.173],
  }], Object.assign(chartBase(), {
    x: 5.0, y: 1.5, w: 7.75, h: 5.1, barDir: "bar", catAxisOrientation: "maxMin",
    valAxisMinVal: -0.2, valAxisMaxVal: 0.05, valAxisMajorUnit: 0.05, valAxisLabelFormatCode: "0.00",
    chartColors: [HEX.accent5], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "+0.000;-0.000;0.000",
    showTitle: true, title: "Change in source-level AUC vs two colours (LR) — none detected", showLegend: false, barGapWidthPct: 60,
    catAxisLabelPos: "low", objectName: "ablation chart",
  }));
  s.addNotes("Every ablation's 95% interval includes zero. This does not prove equivalence: the intervals allow losses up to ~0.18 and gains up to ~0.05. The nested search compares an automatically chosen model with H-LR. Splitting by observation leaks source identity, which is why published observation-split accuracies are not comparable.");

  // =============== 5. Finding 2 ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "XRB pilot" });
  s.addText("Finding 2 · Colours work only in soft-like states", { placeholder: "title" });
  s.addImage({ path: IMG_CC, x: 0.6, y: 1.6, w: 5.7, h: 4.0, altText: "RXTE colour-colour planes, soft-like vs hard-like: BHs (blue) and NSs (orange) separate when soft and overlap when hard", objectName: "colour planes" });
  txt(s, "RXTE development sample. BH blue, NS orange. Soft-like: rms < 7.5%; hard-like: rms > 10% (0.1–4 Hz).", { x: 0.6, y: 5.7, w: 5.7, h: 0.6, fontSize: 12, color: C.accent5, italic: true });
  s.addChart(pres.charts.BAR, [
    { name: "Soft-like", labels: ["RXTE dev, LR", "RXTE dev, RF", "NICER N1, LR", "NICER N1+N2 3C50, RF", "NICER N3 (unseen), RF"], values: [0.954, 0.95, 0.89, 0.95, 0.938] },
    { name: "Hard-like", labels: ["RXTE dev, LR", "RXTE dev, RF", "NICER N1, LR", "NICER N1+N2 3C50, RF", "NICER N3 (unseen), RF"], values: [0.646, 0.69, 0.68, 0.75, 0.68] },
  ], Object.assign(chartBase(), {
    x: 6.6, y: 1.5, w: 6.15, h: 4.3, barDir: "bar", catAxisOrientation: "maxMin", barGrouping: "clustered",
    valAxisMinVal: 0, valAxisMaxVal: 1, valAxisMajorUnit: 0.25, valAxisLabelFormatCode: "0.00",
    chartColors: [HEX.accent5, HEX.accent1], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00",
    showTitle: true, title: "Colour-only observation-level AUC", showLegend: true, legendPos: "b", barGapWidthPct: 50,
    objectName: "state AUC chart",
  }));
  txt(s, [
    { text: "Soft − hard (RXTE, primary test): ", options: { bold: true } },
    { text: "+0.31 [+0.10, +0.51]. All 7 RXTE BHs spend time in hard-like states, so this is the case every BH poses.", options: {} },
  ], { x: 6.6, y: 5.95, w: 6.15, h: 0.8, fontSize: 14 });
  s.addNotes("States here are operational, defined only from fractional rms (Remillard & McClintock thresholds), not full spectral states. The NICER rows are descriptive. Hard-like overlap agrees with Burke et al. 2017: hard-state differences are in Comptonization parameters that 2-25 keV colours sample weakly.");

  // =============== 6. Finding 3 ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "XRB pilot" });
  s.addText("Finding 3 · Timing adds information in hard-like states", { placeholder: "title" });
  const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: HEX.dk1 }, fontFace: "Arial" } });
  const verdict = (t, kind) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: kind === "yes" ? HEX.accent4 : kind === "reuse" ? "7FBFA3" : HEX.accent5 }, align: "center" } });
  const rows = [
    ["RXTE development (31 src)", "development", "LR", "+0.264  [+0.048, +0.455]", ["Detected", "yes"]],
    ["RXTE external (new sources)", "new sources", "LR, frozen", "+0.064  [−0.185, +0.367]", ["Not detected", "no"]],
    ["NICER N1 (new instrument)", "development", "LR", "+0.112  [−0.004, +0.229]", ["Not detected", "no"]],
    ["Pooled RXTE + NICER", "re-use", "LR", "+0.145  [+0.028, +0.257]", ["Detected (re-use)", "reuse"]],
    ["NICER N2 (unseen obs)", "new observations", "LR, frozen", "+0.066  [−0.095, +0.180]", ["Not detected", "no"]],
    ["NICER N1+N2, 3C50 background", "re-use", "RF", "+0.174  [+0.071, +0.300]", ["Detected (re-use)", "reuse"]],
    ["NICER N3 (unseen obs)", "new observations", "RF, frozen", "+0.184  [+0.049, +0.337]", ["Detected", "yes"]],
  ];
  const tableRows = [[hdr("Primary test"), hdr("Data status"), hdr("Model"), hdr("Hard-like ΔAUC  [95% CI]"), hdr("Verdict")]];
  rows.forEach((r, i) => {
    const f = i % 2 ? { fill: { color: HEX.lt2 } } : {};
    tableRows.push([
      { text: r[0], options: Object.assign({ bold: i === 6 }, f) }, { text: r[1], options: f }, { text: r[2], options: f },
      { text: r[3], options: Object.assign({ fontFace: "Calibri", bold: i === 6 }, f) }, verdict(r[4][0], r[4][1]),
    ]);
  });
  s.addTable(tableRows, { x: 0.6, y: 1.55, w: 12.1, colW: [3.5, 2.1, 1.6, 3.0, 1.9], rowH: 0.5, fontSize: 14, color: C.text1, valign: "middle", border: { type: "solid", pt: 0.75, color: "D5DCE6" }, objectName: "timing gain table" });
  card(s, 0.6, 5.75, 12.1, 0.95, HEX.lt2, "takeaway panel");
  txt(s, [
    { text: "Every point estimate is positive; RF gains are consistently +0.17 to +0.25. ", options: { bold: true } },
    { text: "No gain in soft-like states (+0.005), so timing complements colours rather than replacing them. ΔAUC = (colours + 3 rms bands) − (colours only), same model.", options: { color: C.text2 } },
  ], { x: 0.85, y: 5.85, w: 11.6, h: 0.8, fontSize: 14, valign: "middle" });
  s.addNotes("Rows marked re-use analyse data already seen and are robustness checks, not replications. The model class changed during the project: LR was primary through N2; RF became primary after its gains were seen; RF was fixed before download only for N3. The informative band differs by instrument (T1 for RXTE, T2/T3 for NICER), so I don't attribute the gain to a specific power-spectral component.");

  // =============== 7. Prospective test ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "XRB pilot" });
  s.addText("Prospective test · Confirmed on 198 unseen NICER obs", { placeholder: "title" });
  s.addChart(pres.charts.BAR, [
    { name: "Colours only", labels: ["Obs. AUC, RF (primary)", "Obs. AUC, LR", "Source AUC, RF"], values: [0.680, 0.503, 0.717] },
    { name: "Colours + timing", labels: ["Obs. AUC, RF (primary)", "Obs. AUC, LR", "Source AUC, RF"], values: [0.864, 0.685, 0.842] },
  ], Object.assign(chartBase(), {
    x: 0.6, y: 1.5, w: 6.9, h: 5.2, barDir: "col", barGrouping: "clustered",
    valAxisMinVal: 0, valAxisMaxVal: 1, valAxisMajorUnit: 0.25, valAxisLabelFormatCode: "0.00",
    chartColors: [HEX.accent5, HEX.accent4], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000",
    showTitle: true, title: "NICER N3, hard-like observations (74 obs; 8 BH, 19 NS sources)", showLegend: true, legendPos: "b", barGapWidthPct: 70,
    objectName: "N3 chart",
  }));
  card(s, 7.85, 1.6, 4.85, 2.6, "E6F3EC", "primary result card");
  txt(s, "+0.184", { x: 8.15, y: 1.8, w: 4.3, h: 0.95, fontSize: 52, bold: true, color: C.accent4, fontFace: "Arial" });
  txt(s, "hard-like AUC gain, RF  ·  [+0.049, +0.337]", { x: 8.15, y: 2.75, w: 4.3, h: 0.4, fontSize: 15, bold: true });
  txt(s, "Pipeline, 3C50 background, thresholds and RF model all frozen before download.", { x: 8.15, y: 3.2, w: 4.3, h: 0.85, fontSize: 14, color: C.text2 });
  card(s, 7.85, 4.4, 4.85, 2.3, "FBEAE8", "caveat card");
  txt(s, "But at source level…", { x: 8.15, y: 4.6, w: 4.3, h: 0.4, fontSize: 16, bold: true, color: C.accent6 });
  txt(s, "AUC gain +0.125 [−0.053, +0.303] is not detected (27 sources). N3 = new observations of known sources, not new sources.", { x: 8.15, y: 5.05, w: 4.3, h: 1.5, fontSize: 14, color: C.text2 });
  s.addNotes("Robustness on N3: removing one BH at a time leaves gains of +0.146 to +0.212; recomputing timing within 3C50 good-time intervals gives +0.190 [+0.065, +0.330]; observation-level balanced accuracy at the frozen threshold rises by +0.137. Cyg X-1 contributes 7 of 29 BH observations.");

  // =============== 8. Limits & lessons ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "XRB pilot" });
  s.addText("What is still unproven, and what carries over", { placeholder: "title" });
  card(s, 0.6, 1.55, 5.95, 5.15, "FBEAE8", "unproven panel");
  card(s, 6.75, 1.55, 5.95, 5.15, "E6F3EC", "lessons panel");
  txt(s, "Still unproven", { x: 0.9, y: 1.75, w: 5.4, h: 0.45, fontSize: 20, bold: true, color: C.accent6, fontFace: "Arial" });
  txt(s, "Lessons I will reuse", { x: 7.05, y: 1.75, w: 5.4, h: 0.45, fontSize: 20, bold: true, color: C.accent4, fontFace: "Arial" });
  const unproven = [
    ["New sources: ", "unseen observations, but no new BH yet — needs future transients"],
    ["Small sample: ", "only 16 confirmed BHs with usable timing"],
    ["Model choice: ", "RF fixed before data in only one test (N3)"],
    ["Confounders: ", "Eddington ratio, inclination, NS subclass not controlled"],
  ];
  const lessons = [
    ["Split by the unit you generalise to: ", "source, not observation"],
    ["Freeze before you look: ", "pipeline, thresholds and model fixed before new data"],
    ["Honest intervals: ", "bootstrap the independent units (sources)"],
    ["Simple baseline first: ", "2 colours beat an 8-algorithm search"],
  ];
  const bullets = (arr) => arr.flatMap((r, i) => [
    { text: r[0], options: { bold: true, bullet: true } }, { text: r[1], options: { breakLine: i < arr.length - 1 } },
  ]);
  txt(s, bullets(unproven), { x: 0.9, y: 2.4, w: 5.4, h: 4.1, fontSize: 15, paraSpaceAfter: 12 });
  txt(s, bullets(lessons), { x: 7.05, y: 2.4, w: 5.4, h: 4.1, fontSize: 15, paraSpaceAfter: 12 });
  s.addNotes("Also: the hard-like class is defined by an rms threshold that overlaps T2/T3 in frequency, so the result is conditional on an rms-defined subset. Bootstrap intervals cover source sampling only, not training variability or multiplicity across 13 rounds. Paper draft and full report are in the repo (paper_draft/, report_en/).");

  // =============== 9. Section divider ===============
  pres.addSection({ title: "Next: GW sky localization" });
  s = pres.addSlide({ masterName: "SECTION_DARK", sectionTitle: "Next: GW sky localization" });
  s.addText("Next: machine learning for GW sky localization", { placeholder: "title" });
  s.addText("Where should telescopes point within seconds of a merger — and how far can we trust the map?", { placeholder: "body" });
  await iconCircle(s, fa.FaCrosshairs, 0.8, 0.8, 0.9, C.accent1, "Localization");

  // =============== Bridge: practice -> project ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Next: GW sky localization" });
  s.addText("From practice to project: XRB → GW", { placeholder: "title" });
  const bridge = [
    [0.6, HEX.lt2, fa.FaTools, C.text2, "XRB pilot: practice", "Done", C.accent5, [
      "Purpose: get familiar with an end-to-end ML workflow",
      "Data → features → model → held-out evaluation → report",
      "What I keep: the evaluation habits, not the topic"]],
    [7.1, "FDF0E3", fa.FaGraduationCap, C.accent1, "GW sky localization: the project", "Next", C.accent1, [
      "I want to treat this as my postgraduate research project",
      "I need to understand and be able to defend every step",
      "Big direction from Albert and Saha"]],
  ];
  for (const b of bridge) {
    card(s, b[0], 1.55, 5.6, 3.15, b[1], b[4] + " card");
    await iconCircle(s, b[2], b[0] + 0.3, 1.85, 0.75, b[3], b[4]);
    txt(s, b[4], { x: b[0] + 1.25, y: 1.85, w: 3.1, h: 0.75, fontSize: 19, bold: true, fontFace: "Arial", valign: "middle" });
    chip(s, b[5], b[0] + 4.5, 2.06, 0.85, b[6], b[4]);
    txt(s, b[7].map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < 2 } })), { x: b[0] + 0.3, y: 2.9, w: 5.05, h: 1.7, fontSize: 15, color: C.text2, paraSpaceAfter: 8 });
  }
  s.addShape(pres.shapes.CHEVRON, { x: 6.45, y: 2.85, w: 0.4, h: 0.55, fill: { color: C.accent5 }, line: { color: C.accent5 }, objectName: "bridge arrow" });
  txt(s, [
    { text: "Step 0, before I start: ", options: { bold: true, color: C.accent1 } },
    { text: "review the GW Open Data Workshop (GWODW) material — I have forgotten parts of it", options: { bold: true } },
  ], { x: 0.6, y: 5.0, w: 12.1, h: 0.4, fontSize: 17, fontFace: "Arial", valign: "middle" });
  const odw = [
    [fa.FaDatabase, "Open data", "GWOSC strain and event catalogues"],
    [fa.FaWaveSquare, "Signal processing", "PSD, whitening, time–frequency maps"],
    [fa.FaFilter, "Matched filtering", "Waveforms, SNR, detection"],
    [fa.FaMapMarkedAlt, "Parameter estimation", "Posteriors and skymaps"],
  ];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + i * 3.06;
    await iconCircle(s, odw[i][0], x, 5.65, 0.6, C.accent2, odw[i][1]);
    txt(s, odw[i][1], { x: x + 0.75, y: 5.6, w: 2.2, h: 0.35, fontSize: 15, bold: true });
    txt(s, odw[i][2], { x: x + 0.75, y: 5.97, w: 2.2, h: 0.7, fontSize: 13, color: C.text2 });
  }
  s.addNotes("The XRB work was mainly a way to get familiar with an ML workflow from data to report. GW sky localization is what I want to treat as my postgraduate research project. Before starting, I will go back through the GW Open Data Workshop (GWODW) material, because I have forgotten parts of it. The four topics listed are the usual workshop blocks; I will adjust them to the edition I attended.");

  // =============== 10. Why ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Next: GW sky localization" });
  s.addText("Why: follow-up needs fast and trustworthy skymaps", { placeholder: "title" });
  txt(s, "Time to a sky localization (schematic, log scale)", { x: 0.6, y: 1.6, w: 6.6, h: 0.4, fontSize: 15, bold: true });
  const lat = [
    ["Full Bayesian PE", "hours – days", 5.0, C.accent5],
    ["BAYESTAR (LVK rapid)", "seconds", 2.9, C.text2],
    ["DINGO-BNS (NPE)", "~1 s, all 17 params", 2.2, C.accent2],
    ["CBC-SkyNet / GW-SkyLocator", "milliseconds (GPU)", 0.9, C.accent1],
  ];
  lat.forEach((r, i) => {
    const y = 2.2 + i * 1.05;
    txt(s, r[0], { x: 0.6, y, w: 6.6, h: 0.35, fontSize: 14, bold: true });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: y + 0.4, w: r[2], h: 0.4, rectRadius: 0.06, fill: { color: r[3] }, line: { color: r[3] }, objectName: "latency bar " + (i + 1) });
    txt(s, r[1], { x: 0.75 + r[2], y: y + 0.4, w: 6.6 - r[2], h: 0.4, fontSize: 13, color: C.text2, valign: "middle" });
  });
  txt(s, "Bars are illustrative orders of magnitude, not benchmarks.", { x: 0.6, y: 6.45, w: 6.6, h: 0.35, fontSize: 11, italic: true, color: C.accent5 });
  const why = [
    [fa.FaStopwatch, C.accent1, "Speed", "Kilonovae fade in days; prompt X-ray / optical emission fades much faster. Pre-merger alerts would catch the earliest light."],
    [fa.FaExpand, C.accent2, "Area", "GW 90% regions span ~10 to 1000+ deg²; X-ray and optical fields of view are far smaller, so every deg² costs telescope time."],
    [fa.FaCheckDouble, C.accent4, "Calibration", "A 90% region must contain the source 90% of the time, or tiling plans are wasted. Speed is useless without coverage."],
  ];
  for (let i = 0; i < 3; i++) {
    const y = 1.6 + i * 1.65;
    await iconCircle(s, why[i][0], 7.6, y, 0.7, why[i][1], why[i][2]);
    txt(s, why[i][2], { x: 8.5, y, w: 4.2, h: 0.4, fontSize: 18, bold: true, fontFace: "Arial" });
    txt(s, why[i][3], { x: 8.5, y: y + 0.42, w: 4.2, h: 1.1, fontSize: 14, color: C.text2 });
  }
  s.addNotes("Context: GW170817 had a ~28 deg^2 90% region and the optical counterpart was found ~11 h after merger. O4 ended 18 Nov 2025. Per the LVK observing-plan page (April 2026), a ~6-month Intermediate Run (IR1) was planned to start late Oct / mid-Nov 2026, with O5 timing under reassessment — to be checked before relying on dates.");

  // =============== 11. Landscape ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Next: GW sky localization" });
  s.addText("Prior work: fast already, trust is the open question", { placeholder: "title" });
  const prior = [
    ["BAYESTAR", "Singer & Price 2016", "LVK rapid localization from matched-filter triggers. The baseline to beat."],
    ["VItamin", "Gabbard et al. 2022, Nat. Phys.", "Conditional VAE: full BBH posteriors in under a second."],
    ["CBC-SkyNet / GW-SkyLocator", "Chatterjee et al. 2022, 2023", "ResNet + normalizing flow; ms sky maps; pre-merger BNS areas comparable to BAYESTAR."],
    ["DINGO-BNS", "Dax et al. 2025, Nature", "Neural posterior estimation; ~1 s for all BNS parameters; authors report ~30% smaller sky areas."],
  ];
  prior.forEach((p, i) => {
    const x = 0.6 + i * 3.06;
    card(s, x, 1.55, 2.9, 2.75, HEX.lt2, "prior work " + (i + 1));
    txt(s, p[0], { x: x + 0.2, y: 1.7, w: 2.5, h: 0.65, fontSize: 16, bold: true, fontFace: "Arial", valign: "middle" });
    txt(s, p[1], { x: x + 0.2, y: 2.35, w: 2.5, h: 0.35, fontSize: 12, italic: true, color: C.accent2 });
    txt(s, p[2], { x: x + 0.2, y: 2.75, w: 2.5, h: 1.45, fontSize: 13, color: C.text2 });
  });
  txt(s, "Open questions where an XRB-style evaluation can help", { x: 0.6, y: 4.6, w: 12.1, h: 0.4, fontSize: 18, bold: true, fontFace: "Arial" });
  const gaps = [
    [fa.FaRandom, "Real noise", "Non-Gaussian noise and glitches unlike training data"],
    [fa.FaNetworkWired, "Changing networks", "Detector sets and PSDs drift between runs"],
    [fa.FaBullseye, "Coverage", "Are 90% regions really 90% on real events?"],
    [fa.FaLock, "Held-out tests", "Evaluation on events and noise never used in training"],
  ];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + i * 3.06;
    await iconCircle(s, gaps[i][0], x, 5.2, 0.6, C.accent1, gaps[i][1]);
    txt(s, gaps[i][1], { x: x + 0.75, y: 5.15, w: 2.2, h: 0.35, fontSize: 15, bold: true });
    txt(s, gaps[i][2], { x: x + 0.75, y: 5.52, w: 2.2, h: 0.95, fontSize: 13, color: C.text2 });
  }
  s.addNotes("This is a quick literature scan, not a full review; I still need to check 2025-2026 work (e.g. O4 follow-up papers and any LVK use of ML localization in low latency). The DINGO-BNS 30% figure is the authors' own comparison.");

  // =============== Pipeline: train on simulations, apply to real events ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Next: GW sky localization" });
  s.addText("Pipeline: train on simulations, apply to real events", { placeholder: "title" });
  const lanes = [
    ["Training · simulated signals, done once, slow", 1.5, [
      ["Draw parameters", "Masses, spins, RA, Dec, distance. These are the answer"],
      ["Simulate signal", "Waveform model, then projection onto each detector"],
      ["Add noise", "Gaussian noise from the PSD first, then real noise segments"],
      ["Preprocess", "Whiten and crop around the merger: strain or SNR time series"],
      ["Train network", "Embedding + normalizing flow. Loss = −log q(true | data)"]]],
    ["Use · a real event, about a second", 3.6, [
      ["Event detected", "A search pipeline finds the event and its merger time"],
      ["Get data", "Strain around the trigger from each detector"],
      ["Preprocess", "Exactly the same steps as in training"],
      ["Trained network", "Draw thousands of (RA, Dec, distance) samples"],
      ["Skymap", "HEALPix map and 90% region, sent to telescopes"]]],
  ];
  lanes.forEach((lane, li) => {
    txt(s, lane[0], { x: 0.6, y: lane[1], w: 12.1, h: 0.35, fontSize: 15, bold: true, color: li === 0 ? C.accent2 : C.accent4, valign: "middle" });
    lane[2].forEach((b, i) => {
      const x = 0.6 + i * 2.475, y = lane[1] + 0.45;
      const isNet = b[0].includes("network");
      card(s, x, y, 2.2, 1.45, isNet ? "FDF0E3" : HEX.lt2, "lane " + (li + 1) + " box " + (i + 1));
      txt(s, [{ text: (i + 1) + "  ", options: { color: li === 0 ? C.accent2 : C.accent4 } }, { text: b[0], options: {} }], { x: x + 0.15, y: y + 0.12, w: 1.95, h: 0.35, fontSize: 14, bold: true, fontFace: "Arial", valign: "middle" });
      txt(s, b[1], { x: x + 0.15, y: y + 0.52, w: 1.9, h: 0.85, fontSize: 13, color: C.text2 });
      if (i < 4) s.addShape(pres.shapes.CHEVRON, { x: x + 2.26, y: y + 0.57, w: 0.15, h: 0.3, fill: { color: C.accent5 }, line: { color: C.accent5 }, objectName: "lane " + (li + 1) + " arrow " + (i + 1) });
    });
  });
  card(s, 0.6, 5.7, 12.1, 1.0, HEX.lt2, "sky information panel");
  txt(s, [
    { text: "Where the sky information comes from: ", options: { bold: true } },
    { text: "differences in arrival time (up to ~10 ms between Hanford and Livingston), amplitude and phase between detectors. Two detectors give a ring on the sky; a third shrinks it.", options: { color: C.text2 } },
  ], { x: 0.85, y: 5.8, w: 11.6, h: 0.8, fontSize: 14, valign: "middle" });
  s.addNotes("Two lines. Training uses only simulated signals, so every example has a known answer: the parameters I drew in step 1. Minimising -log q(true | data) over many simulations makes the network's distribution approach the Bayesian posterior (neural posterior estimation); no Bilby runs are needed for training. Use: the same preprocessing and the same network (the two highlighted boxes) on a real event. Open choices to ask Saha: whitened strain or matched-filter SNR time series as input, and whether to practise on BBH (signals of a few seconds) before BNS (about 160 s from 20 Hz). Paper-specific details here are from memory and need checking.");

  // =============== Ground truth and checks ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Next: GW sky localization" });
  s.addText("Where the answer comes from, and how we check it", { placeholder: "title" });
  txt(s, "The answer comes from the simulation", { x: 0.6, y: 1.5, w: 5.9, h: 0.4, fontSize: 17, bold: true, fontFace: "Arial", valign: "middle" });
  txt(s, "Four checks", { x: 6.9, y: 1.5, w: 5.8, h: 0.4, fontSize: 17, bold: true, fontFace: "Arial", valign: "middle" });
  const roles = [
    [fa.FaQuestion, C.text2, "Question", "Detector data with a signal in it", "Simulated signal + noise"],
    [fa.FaKey, C.accent1, "Answer", "The parameters I chose when injecting", "e.g. RA = 197°, Dec = −23°"],
    [fa.FaPencilAlt, C.accent2, "Solver", "A method that infers position from data", "BAYESTAR, Bilby, the ML model"],
  ];
  for (let i = 0; i < 3; i++) {
    const y = 2.0 + i * 1.25;
    card(s, 0.6, y, 5.9, 1.1, i === 1 ? "FDF0E3" : HEX.lt2, "role card " + roles[i][2]);
    await iconCircle(s, roles[i][0], 0.8, y + 0.2, 0.7, roles[i][1], roles[i][2]);
    txt(s, roles[i][2], { x: 1.75, y: y + 0.1, w: 4.6, h: 0.3, fontSize: 15, bold: true, color: roles[i][1], valign: "middle" });
    txt(s, roles[i][3], { x: 1.75, y: y + 0.4, w: 4.6, h: 0.3, fontSize: 14, valign: "middle" });
    txt(s, roles[i][4], { x: 1.75, y: y + 0.7, w: 4.6, h: 0.3, fontSize: 13, italic: true, color: C.text2, valign: "middle" });
  }
  const checks = [
    [fa.FaBullseye, "Calibration (P–P plot)", "Thousands of injections: does the 90% region contain the true position about 90% of the time?"],
    [fa.FaRulerCombined, "Precision", "90% area and searched area on the same injections, against BAYESTAR and Bilby"],
    [fa.FaRandom, "Real noise", "Injections into real noise segments never used in training"],
    [fa.FaStar, "Real events", "Compare with LVK skymaps; for GW170817, is NGC 4993 inside?"],
  ];
  for (let i = 0; i < 4; i++) {
    const y = 2.0 + i * 0.92;
    await iconCircle(s, checks[i][0], 6.9, y + 0.05, 0.6, C.accent4, checks[i][1]);
    txt(s, checks[i][1], { x: 7.7, y, w: 5.0, h: 0.3, fontSize: 15, bold: true, valign: "middle" });
    txt(s, checks[i][2], { x: 7.7, y: y + 0.32, w: 5.0, h: 0.5, fontSize: 13, color: C.text2 });
  }
  txt(s, [
    { text: "Past GW data is used in two ways: ", options: { bold: true, color: C.accent6 } },
    { text: "signal-free segments as realistic noise, and real events as the final test. Real events cannot be the training set: there are too few, and only GW170817 has a confirmed position.", options: {} },
  ], { x: 0.6, y: 5.95, w: 12.1, h: 0.75, fontSize: 14, valign: "middle" });
  s.addNotes("BAYESTAR and Bilby are solvers, not the answer: all three methods are marked against the injected parameters. Bilby has two roles: it can also be the tool that makes the injections. On real events there is no answer, so agreement with the LVK analysis only shows consistency with the reference method. That only GW170817 has a confirmed electromagnetic counterpart is my current understanding; to confirm with Saha for O4.");

  // =============== 12. Proposal ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Next: GW sky localization" });
  s.addText("Proposal: a calibrated neural sky localizer", { placeholder: "title" });
  const plan = [
    ["1", "Baseline & data", ["Public GWOSC strain + simulated BNS / NSBH injections", "BAYESTAR skymaps as baseline", "Metrics: 90% area, searched area, P–P coverage"]],
    ["2", "Model", ["Normalizing-flow posterior over sky position (+ distance)", "Start from open-source code (e.g. DINGO)", "HL, HLV, HLVK detector networks"]],
    ["3", "Stress test", ["Held-out real-noise periods and glitches; PSD drift", "Frozen test on public O4 events vs LVK maps", "Follow-up value: probability covered by telescope tiling"]],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.55, 3.8, 3.55, HEX.lt2, "plan step " + plan[i][0]);
    s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: 1.8, w: 0.65, h: 0.65, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "step number " + plan[i][0] });
    txt(s, plan[i][0], { x: x + 0.25, y: 1.8, w: 0.65, h: 0.65, fontSize: 22, bold: true, color: C.background1, align: "center", valign: "middle" });
    txt(s, plan[i][1], { x: x + 1.05, y: 1.8, w: 2.6, h: 0.65, fontSize: 19, bold: true, fontFace: "Arial", valign: "middle" });
    txt(s, plan[i][2].map((b, j) => ({ text: b, options: { bullet: true, breakLine: j < 2 } })), { x: x + 0.25, y: 2.65, w: 3.35, h: 2.35, fontSize: 14, color: C.text2, paraSpaceAfter: 8 });
    if (i < 2) s.addShape(pres.shapes.CHEVRON, { x: x + 3.86, y: 3.15, w: 0.18, h: 0.36, fill: { color: C.accent5 }, line: { color: C.accent5 }, objectName: "step arrow " + (i + 1) });
  }
  card(s, 0.6, 5.35, 12.1, 1.35, "FDF0E3", "carry-over panel");
  txt(s, "Carried over from the XRB pilot", { x: 0.85, y: 5.45, w: 11.6, h: 0.4, fontSize: 16, bold: true, color: C.accent1, fontFace: "Arial" });
  txt(s, "Hold out by event and noise period (like holding out sources)  ·  Commit the plan and freeze the pipeline before each test  ·  Report coverage with event-bootstrap intervals, not just median area  ·  Beat BAYESTAR before adding complexity", { x: 0.85, y: 5.9, w: 11.6, h: 0.7, fontSize: 14 });
  s.addNotes("Scope is deliberately narrow: sky position (and distance) for EM-bright systems, where localization matters most for follow-up. The key deliverable is not a faster number but a calibration study: when do neural skymaps under-cover on real noise, and can that be fixed (e.g. by training on real-noise segments or recalibrating)?");

  // =============== 13. Who decides what ===============
  pres.addSection({ title: "How I plan to work" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "How I plan to work" });
  s.addText("How I plan to work: who decides what", { placeholder: "title" });
  const layers = [
    [fa.FaUserTie, C.accent1, "Albert & Saha", "Big direction · every ~2 weeks", [
      "Science question and scope", "What counts as success", "Priorities, and when to stop",
      "I bring one page: decided, done, stuck, decisions needed"]],
    [fa.FaRobot, C.accent3, "AI assistant", "Small direction · daily", [
      "Technical choices inside the agreed scope", "Libraries, priors, architecture, debugging",
      "Papers and numbers from AI are marked \"to verify\""]],
    [fa.FaUserGraduate, C.accent2, "Me", "Every step", [
      "Understand each step well enough to explain it to Saha", "Write the evaluation code myself",
      "Check AI claims against papers and data"]],
  ];
  for (let i = 0; i < 3; i++) {
    const [Ic, col, name, cadence, items] = layers[i];
    const x = 0.6 + i * 4.1;
    card(s, x, 1.55, 3.9, 3.95, HEX.lt2, "layer card " + (i + 1));
    await iconCircle(s, Ic, x + 0.3, 1.85, 0.75, col, name);
    txt(s, name, { x: x + 1.25, y: 1.85, w: 2.45, h: 0.4, fontSize: 19, bold: true, fontFace: "Arial", valign: "middle" });
    txt(s, cadence, { x: x + 1.25, y: 2.27, w: 2.45, h: 0.35, fontSize: 13, bold: true, color: col, valign: "middle" });
    txt(s, items.map((b, j) => ({ text: b, options: { bullet: true, breakLine: j < items.length - 1 } })), { x: x + 0.3, y: 2.95, w: 3.35, h: 2.4, fontSize: 14, color: C.text2, paraSpaceAfter: 8 });
  }
  card(s, 0.6, 5.7, 12.1, 1.0, "FDF0E3", "decision log panel");
  txt(s, [
    { text: "Decision log: ", options: { bold: true, color: C.accent1 } },
    { text: "every choice is recorded with who made it (Albert, Saha, me, or an AI suggestion). Anything that changes the science question, the test set or the success criteria goes to the meeting, not to the AI.", options: {} },
  ], { x: 0.85, y: 5.8, w: 11.6, h: 0.8, fontSize: 14, valign: "middle" });
  s.addNotes("Big direction with Albert and Saha, small direction with AI. The XRB pilot already kept a decision log (reports/decision_log.md); the new part is recording who made each decision. In the XRB paper draft several literature claims supplied by AI could not be re-verified, which is why AI-supplied papers and numbers start as 'to verify'.");

  // =============== Idea-to-result workflow ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "How I plan to work" });
  s.addText("From idea to result: seven stages, each with a check", { placeholder: "title" });
  const wfHdr = (t, fill) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: fill }, fontFace: "Arial" } });
  const wf = [
    ["1  Idea", "Suggests ideas and related work", ["", "Propose ideas; choose one worth testing"], "A one-paragraph question"],
    ["2  Feasibility", "Searches papers, data and existing code", ["Double check: ", "read the key papers myself"], "Feasible? If not, revise or drop"],
    ["3  Plan", "Challenges the plan, offers options", ["", "Set scope, test set and success criteria"], "Plan agreed with Albert and Saha"],
    ["4  Method", "Proposes a method and alternatives", ["", "Be able to explain why this method"], "Method fixed before coding"],
    ["5  Code", "Writes it step by step (mode 2)", ["Double check: ", "explain, test, modify it"], "Known-answer test passes"],
    ["6  Run", "Helps run and debug", ["", "Run with the pipeline frozen; log it"], "Results saved with code version"],
    ["7  Interpret", "Challenges my reading, suggests checks", ["", "Interpret first, in my own words"], "Discussed with Albert and Saha"],
  ];
  const wfRows = [[wfHdr("Stage", HEX.dk1), wfHdr("AI", HEX.accent3), wfHdr("Me", HEX.accent2), wfHdr("Before moving on", HEX.accent1)]];
  wf.forEach((r, i) => {
    const f = i % 2 ? { fill: { color: HEX.lt2 } } : {};
    wfRows.push([
      { text: r[0], options: Object.assign({ bold: true, fontFace: "Arial" }, f) },
      { text: r[1], options: f },
      { text: [{ text: r[2][0], options: { bold: true, color: HEX.accent2 } }, { text: r[2][1], options: {} }], options: f },
      { text: r[3], options: f },
    ]);
  });
  s.addTable(wfRows, { x: 0.6, y: 1.55, w: 12.1, colW: [1.9, 3.5, 3.7, 3.0], rowH: 0.5, fontSize: 14, color: C.text1, valign: "middle", border: { type: "solid", pt: 0.75, color: "D5DCE6" }, objectName: "workflow table" });
  card(s, 0.6, 5.75, 12.1, 0.95, "FDF0E3", "XRB example panel");
  txt(s, [
    { text: "Stage 2 in the XRB pilot: ", options: { bold: true, color: C.accent1 } },
    { text: "the AI's list of 16 black-hole candidates was logged as \"not verified\". Each one was checked against the BlackCAT catalogue, with sources recorded, before any data were downloaded.", options: {} },
  ], { x: 0.85, y: 5.83, w: 11.6, h: 0.8, fontSize: 14, valign: "middle" });
  s.addNotes("Ideas come from me and from AI. AI checks feasibility in the literature and I double-check by reading the key papers myself. If it is feasible, I make a plan with AI and agree it with Albert and Saha. Then the method, then the code (AI writes, I double-check), then run and interpret. Each stage has a condition before moving on, and each decision goes in the decision log with who made it. The XRB example is in reports/decision_log.md (v3c) and reports/v3c_candidate_verification.md: 16 candidates checked, all kept, frozen before any v3c data were downloaded.");

  // =============== 14. Three coding modes ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "How I plan to work" });
  s.addText("Three ways to write the code — I prefer mode 2", { placeholder: "title" });
  [["Mode", 1.75], ["Trade-off", 5.0], ["Where I would use it", 8.9]].forEach((h) => txt(s, h[0], { x: h[1], y: 1.5, w: 3.6, h: 0.3, fontSize: 12, bold: true, color: C.accent5 }));
  const modes = [
    ["1", "AI writes everything", "Black box: I only check the output", "Fastest, but I cannot explain or defend the code.", "Plots, downloads, format conversion, boilerplate: errors are obvious and do not change conclusions.", false],
    ["2", "AI writes step by step", "I explain, test and modify each step before moving on", "Slower, but I can explain every number.", "Data processing, signal injection, the model, the training loop.", true],
    ["3", "I write it by hand", "AI only reviews", "Slowest, deepest understanding.", "Evaluation metrics (90% area, P–P coverage), the test-set split, and learning the basics.", false],
  ];
  modes.forEach((m, i) => {
    const y = 1.85 + i * 1.35;
    card(s, 0.6, y, 12.1, 1.2, m[5] ? "FDF0E3" : HEX.lt2, "mode band " + m[0]);
    s.addShape(pres.shapes.OVAL, { x: 0.85, y: y + 0.27, w: 0.65, h: 0.65, fill: { color: m[5] ? C.accent1 : C.text2 }, line: { color: m[5] ? C.accent1 : C.text2 }, objectName: "mode number " + m[0] });
    txt(s, m[0], { x: 0.85, y: y + 0.27, w: 0.65, h: 0.65, fontSize: 22, bold: true, color: C.background1, align: "center", valign: "middle" });
    txt(s, m[1], { x: 1.75, y: y + 0.15, w: 3.0, h: 0.4, fontSize: 16, bold: true, fontFace: "Arial", valign: "middle" });
    txt(s, m[2], { x: 1.75, y: y + 0.57, w: 3.0, h: 0.55, fontSize: 13, color: C.text2 });
    txt(s, m[3], { x: 5.0, y: y + 0.15, w: 3.6, h: 0.9, fontSize: 14, valign: "middle" });
    txt(s, m[4], { x: 8.9, y: y + 0.15, w: 3.6, h: 0.9, fontSize: 14, color: C.text2, valign: "middle" });
  });
  txt(s, [
    { text: "Rule for choosing: ", options: { bold: true, color: C.accent6 } },
    { text: "if this code were wrong, would the conclusion be wrong? The more it would, the more of it I write and check myself. A wrong metric usually looks like a good result.", options: {} },
  ], { x: 0.6, y: 5.95, w: 12.1, h: 0.75, fontSize: 14, valign: "middle" });
  s.addNotes("Mode 2 is the main mode. The XRB pilot was closer to mode 1: the reports are complete, but I could not explain every part on the spot. This time the goal is that I can explain every number. Evaluation metrics go in mode 3 because an error there is the hardest to notice.");

  // =============== 15. Mode 2 loop ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "How I plan to work" });
  s.addText("Mode 2 in practice: one small step at a time", { placeholder: "title" });
  const loop = [
    ["1", "I say it first", "Me", "I write down the input, the output and how to check it. AI challenges the plan."],
    ["2", "AI writes one step", "AI", "About 50–150 lines or one function, with a short explanation and a sanity check."],
    ["3", "I explain it back", "Me", "Array shapes, assumptions, where it could break. AI corrects me."],
    ["4", "Verify", "Both", "Test on a case with a known answer, such as a signal injected at a known sky position."],
    ["5", "I modify it", "Me", "A parameter, a plot or a condition. If I can modify it, I understand it."],
    ["6", "Commit and log", "Me", "My own commit message, plus what I learned and what to ask Saha."],
  ];
  const who = { Me: C.accent2, AI: C.accent3, Both: C.accent4 };
  loop.forEach((st, i) => {
    const x = 0.6 + (i % 3) * 4.1, y = 1.55 + Math.floor(i / 3) * 2.05;
    card(s, x, y, 3.9, 1.85, HEX.lt2, "loop step " + st[0]);
    s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: y + 0.22, w: 0.55, h: 0.55, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "loop number " + st[0] });
    txt(s, st[0], { x: x + 0.25, y: y + 0.22, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle" });
    txt(s, st[1], { x: x + 0.95, y: y + 0.22, w: 1.95, h: 0.55, fontSize: 16, bold: true, fontFace: "Arial", valign: "middle" });
    chip(s, st[2], x + 2.95, y + 0.33, 0.7, who[st[2]], "step " + st[0] + " owner");
    txt(s, st[3], { x: x + 0.25, y: y + 0.92, w: 3.4, h: 0.85, fontSize: 14, color: C.text2 });
  });
  card(s, 0.6, 5.7, 12.1, 1.0, "FBEAE8", "gate panel");
  txt(s, [
    { text: "Gate: ", options: { bold: true, color: C.accent6 } },
    { text: "if I cannot explain the step (3) or the known-answer test fails (4), we do not move to the next step.", options: {} },
  ], { x: 0.85, y: 5.8, w: 11.6, h: 0.8, fontSize: 15, valign: "middle" });
  s.addNotes("Each step is one small testable unit. Steps 3 and 5 are what make this different from mode 1: I have to explain the code back and change it myself. The log entry from step 6 feeds the one-page update for the meeting.");

  // =============== 16. Order of work ===============
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "How I plan to work" });
  s.addText("Order of work: evaluation before model", { placeholder: "title" });
  const phases = [
    ["A", "Foundations", "Mode 3 · by hand", C.accent2, ["Step 0: review the GWODW material", "GW150914 / GW170817 strain: PSD, whitening", "Project a waveform onto each detector; see how time delays localize", "Run BAYESTAR; read a skymap; compute the 90% area"]],
    ["B", "Evaluation tools", "Mode 3 · by hand", C.accent2, ["Injection set, metrics, P–P plot", "Freeze the test set before any model exists"]],
    ["C", "Model", "Mode 2 · step by step", C.accent1, ["2D toy flow", "Sky position only, Gaussian noise", "Then real noise", "Simple library first (e.g. sbi), DINGO as reference"]],
    ["D", "Stress tests", "Mode 2 · step by step", C.accent1, ["Plan written before each test", "Held-out real-noise periods, glitches, PSD drift", "Public O4 events vs LVK skymaps"]],
  ];
  s.addShape(pres.shapes.LINE, { x: 0.9 + 0.3, y: 1.9, w: 3 * 3.06, h: 0, line: { color: HEX.accent5, width: 1.5 }, objectName: "timeline" });
  phases.forEach((p, i) => {
    const x = 0.6 + i * 3.06;
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: 1.6, w: 0.6, h: 0.6, fill: { color: C.text1 }, line: { color: C.text1 }, objectName: "phase node " + p[0] });
    txt(s, p[0], { x: x + 0.3, y: 1.6, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle" });
    card(s, x, 2.45, 2.9, 4.25, HEX.lt2, "phase card " + p[0]);
    txt(s, p[1], { x: x + 0.2, y: 2.6, w: 2.5, h: 0.4, fontSize: 17, bold: true, fontFace: "Arial", valign: "middle" });
    chip(s, p[2], x + 0.2, 3.08, 2.0, p[3], "phase " + p[0] + " mode");
    txt(s, p[4].map((b, j) => ({ text: b, options: { bullet: true, breakLine: j < p[4].length - 1 } })), { x: x + 0.2, y: 3.6, w: 2.55, h: 3.0, fontSize: 14, color: C.text2, paraSpaceAfter: 8 });
  });
  s.addNotes("A and B come before any model so that the test set and metrics are fixed first, the same 'freeze before you look' rule as in the XRB pilot. Phase A starts by reviewing the GWODW material and then repeats the basics by hand. Phase C starts with a toy problem with a known answer before touching GW data. The library names are suggestions to check with Saha.");

  // =============== 17. Discussion ===============
  pres.addSection({ title: "Discussion" });
  s = pres.addSlide({ masterName: "SECTION_DARK", sectionTitle: "Discussion" });
  s.addText("For discussion", { placeholder: "title" });
  txt(s, [
    { text: "Scope: BNS / NSBH only, or all CBCs? Include pre-merger?", options: { bullet: true, breakLine: true } },
    { text: "Science hook: link to the X-ray / optical follow-up our group does?", options: { bullet: true, breakLine: true } },
    { text: "Compute: GPU access for training normalizing flows", options: { bullet: true, breakLine: true } },
    { text: "Working with AI: is this workflow acceptable, and how should a paper disclose it?", options: { bullet: true, breakLine: true } },
    { text: "Cadence and roles: a regular meeting; could Saha advise on GW data analysis (~30 min a week)?", options: { bullet: true } },
  ], { x: 0.8, y: 4.1, w: 11.7, h: 2.6, fontSize: 18, color: "DCE3F0", paraSpaceAfter: 9 });
  await iconCircle(s, fa.FaComments, 0.8, 0.8, 0.9, C.accent1, "Discussion");
  s.addNotes("Also worth asking: should the XRB paper draft be finished first (new BH transients would be the decisive test), or run in parallel? The AI-assistance disclosure in the XRB paper draft is still a placeholder. First milestone to agree for the next meeting.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
