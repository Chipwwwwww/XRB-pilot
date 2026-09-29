# 預先固定的分析設定（Pre-registration）

寫於 2026-09-29，**在任何模型訓練或看到分類結果之前**。所有數值參數存於 `scripts/config.py`。
若之後修改，需記錄在 `reports/decision_log.md`，並說明是否在看到結果之後修改。

## 來源選擇原則
- BH：在 BlackCAT（Corral-Santana+2016, arXiv:1510.08869）中具動力學質量證據（mass function）的系統。
  不使用只有X射線行為判斷的 BH candidate。
- NS：Galloway+2008 burst catalogue（arXiv:astro-ph/0608259）中觀測到 type-I X-ray bursts 的系統（燃燒在固體表面上 → 必為NS）。
- 在下述時間窗內須有 ≥30 次合格 RXTE/PCA 指向觀測。
- 選定：BH = GRO J1655-40、GRS 1915+105、XTE J1550-564、4U 1543-47；NS = 4U 1636-53、4U 1608-52、4U 1728-34、Aql X-1。
- 不包含 XTE J1908+094 / 4U 1907+097（Garg+2026 指出原資料集中二者 ObsID 配對錯誤），因此該問題不影響本樣本；
  但本流程仍以「FITS header 的 RA/DEC 與來源座標距離 ≤ 0.1°」檢查每筆觀測的來源配對。

## 觀測選取
- 時間窗：MJD 51677–54094（2000-05-13 至 2006-12-25）= PCA gain epoch 5，且早於 PCU1 失去 propane layer。
  理由：同一增益時期，通道–能量對應與 response 最一致；StdProds 在此期間不含 PCU0。
- 目錄層級條件：EXPOSURE ≥ 1000 s、STD1RATE ≥ 5 c/s/PCU、指向與來源中位座標距離 ≤ 0.1°。
- 每來源 15 次：把合格清單依 MJD 排序、分成 15 個等數量時間區段，各區段以固定亂數（seed = 42 + 來源序號）排列候選，
  依序嘗試，第一個通過品質規則者入選（每區段最多嘗試 6 個）。不看能譜形狀、不看分類結果。

## 下載後品質規則（任何一項不合格即排除並記錄原因，改用同區段下一候選）
- 檔案 s2.pha / b2.pha / rsp 均存在且可讀；129 channels；EBOUNDS 覆蓋 5–25 keV。
- 光譜 EXPOSURE ≥ 1000 s；淨計數 5–25 keV S/N ≥ 10；估計 deadtime fraction ≤ 0.10。
- FITS 內 RA_OBJ/DEC_OBJ 與來源座標距離 ≤ 0.1°；所有特徵值有限（無 NaN/inf）。

## 能量表示
- 共同能量格點：參考觀測 91702-01-66-05 的 EBOUNDS 中介於最接近 5 keV 與 25 keV 的通道邊界之間的所有通道（45 bins, 4.91–25.01 keV）。
  其他觀測以「通道內計數均勻分布」假設、按能量重疊比例重分箱到此格點（誤差以權重平方傳遞）。
- 淨計數率 = DCOR × (源計數/曝光 − 背景模型計數/曝光)，除以 PCU 數與 bin 寬 → count s⁻¹ keV⁻¹ PCU⁻¹。
  這是儀器計數空間，不是物理 flux；未做 response unfolding。
- DCOR = 1/(1−DTF)，DTF 僅以 Std2 good-xenon 計數率 × 1e-5 估計（下限；缺 VLE/propane 項）。
- 非正值：保留原值，不取絕對值、不截斷、不刪除；記錄受影響的 bins 與觀測。
- 表示A（保留亮度）：asinh(rate / 0.1)。asinh 對大值近似 log、對負值有定義。
- 表示B（只看形狀）：rate / F，其中 F = 該譜 5–25 keV 淨計數率（count/s/PCU）；單位 keV⁻¹。F ≤ 0 或 S/N<10 的觀測無法正規化——此類觀測已由品質規則排除，因此 A、B 樣本完全相同。
- 缺值：不做填補；有缺值的觀測依品質規則排除。

## 模型與評估
- DummyClassifier(prior)、LogisticRegression（StandardScaler→LR, C=1, L2, class_weight=balanced）、
  RandomForest（500 trees, max_features=sqrt, min_samples_leaf=2, class_weight=balanced, seed=42, n_jobs=2）。無調參。
- 主評估：leave-one-source-out（8 folds）。A、B 使用相同樣本、相同 folds。
- 觀測層級：混淆矩陣、BH/NS recall、balanced accuracy、各來源正確率及其平均。
- 來源層級：該來源 out-of-fold BH 分數平均 ≥ 0.5 → BH。門檻固定，不在測試結果上調整。
- 次要診斷（事先宣告）：observation-wise stratified 5-fold（同一天體會同時在訓練與測試），僅用來示範資料洩漏造成的高估。
