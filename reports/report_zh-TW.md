# RXTE X-ray binary BH／NS 能譜分類：小型 pilot 報告

日期：2026-09-29　｜　程式與資料：見 `README.md`　｜　預先固定設定：`reports/preregistration.md`

> 一句話結論：在 4 BH + 4 NS、每源 15 次觀測的 leave-one-source-out 測試中，
> Logistic Regression / Random Forest 的觀測層級 balanced accuracy 約 0.69–0.76，來源層級 6–7/8 分對；
> 但每個模型都有 1–2 個來源大部分分錯，且哪個來源分錯會隨表示法改變。
> 以 8 個天體而言，這只能說「有訊號、但不穩定」，不能推論到整個 XRB 族群。

---

## 1. 問題

單次 RXTE/PCA 觀測的 5–25 keV 能譜，能否辨識「訓練時沒見過的天體」的緻密星是 BH 還是 NS？
關鍵是 **以天體為單位** 做測試：同一天體的多次觀測高度相關，若訓練與測試混用同一天體，準確率會被高估（見 §4.3）。

## 2. 資料

### 2.1 資料來源與和文獻的差異
- Pattnaik+2021（arXiv:2012.06934）與 Garg+2026（arXiv:2601.18139）使用 61 個 LMXB、約 1.5 萬次 RXTE/PCA 觀測，
  以 XSPEC 取得 43 通道、5–25 keV 的背景扣除、deadtime 修正計數率。**兩篇都沒有公開處理後的能譜陣列**
  （Pattnaik 的 Data availability 只指向 HEASARC archive），因此本 pilot 無法直接使用作者資料。
- 本研究改用 HEASARC 官方 **RXTE Standard Products（StdProd）**：每個 ObsID 已由 RXTE GOF 以統一流程產生的
  Standard-2 source spectrum（`xp*_s2.pha`）、pcabackest 背景模型譜（`xp*_b2.pha`）與 response（`xp*.rsp`）。
  優點：不需 HEASoft 即可正確做背景扣除；缺點：篩選條件為 GOF 的通用設定（ELV>10、OFFSET<0.02 等），
  無法依個別觀測最佳化，且未做 deadtime 修正（見 §3.2）。
- Garg+2026 指出原資料集中標為 XTE J1908+094 的 ObsID 實際屬於 NS 4U 1907+097。
  本樣本沒有這兩個來源；但我們對每筆觀測檢查 FITS header 的 RA/DEC 與來源座標距離（最大 0.045°，門檻 0.1°），
  以避免同類配對錯誤。

### 2.2 來源（`data/sources.csv`）

| source_id | 類別 | 分類證據 | 狀態 |
|---|---|---|---|
| GRO J1655-40 | BH | 動力學質量函數（BlackCAT） | confirmed |
| GRS 1915+105 | BH | 動力學質量函數（BlackCAT） | confirmed |
| XTE J1550-564 | BH | 動力學質量函數（BlackCAT） | confirmed |
| 4U 1543-47 | BH | 動力學質量函數（BlackCAT） | confirmed |
| 4U 1636-53 | NS | type-I X-ray bursts（Galloway+2008） | confirmed |
| 4U 1608-52 | NS | type-I bursts | confirmed |
| 4U 1728-34 | NS | type-I bursts | confirmed |
| Aql X-1 | NS | type-I bursts | confirmed |

選擇原則：只用「動力學確認」的 BH（不用僅憑 X 射線行為判斷的 BH candidate）與有 type-I burst 的 NS（burst 需要固體表面）。

### 2.3 觀測選取（`data/observations.csv`）
- 時間窗：2000-05-13 至 2006-12-25（PCA gain epoch 5，StdProd 不含 PCU0，且早於 PCU1 失效）。
- 目錄條件：曝光 ≥1000 s、Std1 計數率 ≥5 c/s/PCU、指向與來源座標距離 ≤0.1°。
  篩選流失見 `results/attrition_catalog.csv`（例：XTE J1550-564 從 414 筆 → 時間窗 138 → 合格 63）。
- 每來源 15 筆：依 MJD 分成 15 個等數量時間區段，每區段以固定亂數抽一筆；若不通過品質規則就改抽同區段的下一筆。
- 3 筆 ObsID 帶 `G` 字尾（70132-01-01-02G、50030-03-07-00G、80403-01-01-00G）；這是 archive 中的 ObsID 變體（字尾含義本次未查證），已確認在樣本中唯一、且 header 座標與來源相符。
- 結果：**120 筆全部由第一順位候選通過**，沒有任何排除或替換。總曝光約 402 ks；N_PCU 分布 1:59、2:42、3:14、4:5。
- 注意：4U 1543-47 所有觀測都在 2002 年那次爆發（MJD 52443–52492），GRO J1655-40 都在 2005 年爆發；
  其他來源橫跨多年。

## 3. 方法

### 3.1 FITS 檢查結果（`reports/step2_fits_check.md`）
- source 與 background 檔都是 `HDUCLAS2=TOTAL, HDUCLAS3=COUNT`，欄位 `COUNTS` 單位為 **count**（不是 rate、更不是 flux）。
- `POISSERR=F`，`STAT_ERR` 已給；`SYS_ERR=0`（**沒有附系統誤差**）。背景的 `STAT_ERR` = √(模型計數)，
  但背景是模型預測值，真正的不確定度主要來自模型本身；本 pilot 沒有加入背景模型的系統誤差（大小未在本次查證）。
- source/background 曝光相同，`BACKSCAL = AREASCAL = 1`。
- 使用的 PCU 由 `ROWIDn` 關鍵字給出；response 的有效面積隨 PCU 數線性增加（6 keV 約 1070 cm²/PCU），
  所以除以 N_PCU 得到每 PCU 的計數率是合理的。
- 129 個 Std2 通道，gain epoch 5 下 5–25 keV 約對應 45 個通道（Pattnaik 使用 43 個）。

### 3.2 能譜處理（`scripts/spectra.py`, `scripts/04_fetch_process.py`）
1. **背景扣除**（OGIP／XSPEC 定義）：r_net = C_s/t_s − (BACKSCAL_s/BACKSCAL_b)·C_b/t_b，逐通道。
   這是正確的做法，因為背景檔就是同通道、同 PCU、同 GTI 的背景模型預測。
2. **Deadtime**：StdProd 未修正 deadtime。完整修正需要 Standard-1 的 VLE／propane 計數率（需另外下載原始資料）。
   本 pilot 只用 Std2 good-xenon 計數率估計 DTF = rate/PCU × 1e-5（官方公式中的一項），套用 DCOR = 1/(1−DTF) 到淨計數率。
   這是 **下限修正**：中位數 DTF = 0.3%，最大 6%（GRS 1915+105 等亮源）。缺少的 VLE 項會讓亮源仍有少量低估。
3. **共同能量格點**：以參考觀測 91702-01-66-05 的 EBOUNDS 在 4.91–25.01 keV 的 45 個通道為格點；
   每筆觀測依自己的 EBOUNDS 以能量重疊比例重分箱。epoch 5 內的 gain 漂移最大 0.85 通道（中位 0.17）。
4. **單位**：count s⁻¹ keV⁻¹ PCU⁻¹。這是 **儀器計數空間**，沒有做 response unfolding，所以不是物理 flux。
5. **Response 差異檢查**：把固定的 Γ=2 冪律折疊過每筆觀測的 response，比較預期計數。
   觀測之間中位差異 3.7%，最大 11%，主要由 **PCU 組合** 決定（例：PCU 2+3 在 25 keV 端比中位高約 9%，PCU 2+4 低約 7%）。
   BH 與 NS 的 PCU 組合分布相近（平均傾斜 2.0% vs 2.4%），因此這比較像是雜訊，而不是明顯的「類別捷徑」。
   但它是本表示法最大的已知儀器系統誤差。
6. **非正值**：120×45 = 5400 個 bin 中有 7 個 ≤ 0（3 筆觀測：GRO J1655-40 兩筆、GRS 1915+105 一筆，都在 >21 keV，這些是高能端很陡的軟譜）。
   保留原值，不取絕對值、不截斷、不刪除。
7. **誤差**：source Poisson + 背景模型統計誤差，平方和開根號後依重分箱權重傳遞。
   誤差不作為分類特徵，只用於品質篩選（S/N ≥ 10；本樣本最小 S/N = 34.9）與作圖。

### 3.3 兩種表示法
- **A（保留亮度）**：asinh(rate / 0.1)。asinh 在大值時近似 log、在 0 附近是線性、對負值也有定義，
  因此不必為了取 log 而改動非正值。它保留了絕對計數率。
- **B（只看形狀）**：rate / F，F = 同一譜在 5–25 keV 的淨計數率（count/s/PCU），單位 keV⁻¹。
  每一筆譜各自除以自己的總量，因此抹掉亮度、只剩形狀。F ≤ 0 的譜無法這樣正規化；本樣本最小 F = 3.15，沒有這種情況。
- 區分兩件事：B 的「逐譜正規化」是每筆觀測內部的處理，不需從資料學習；
  Logistic Regression 前的 `StandardScaler` 是「訓練集特徵標準化」，每個特徵的平均與標準差 **只在該 fold 的訓練集上 fit**。

### 3.4 模型與評估（`scripts/07_train_eval.py`）
- DummyClassifier(prior)、Logistic Regression（StandardScaler→LR, C=1, L2, class_weight=balanced）、
  Random Forest（500 樹, max_features=sqrt, min_samples_leaf=2, class_weight=balanced, random_state=42, n_jobs=2）。沒有調參。
- **Leave-one-source-out（LOSO）**：8 folds，每 fold 保留一個完整天體。程式對每 fold 檢查：
  訓練與測試天體完全不重疊、訓練集同時含 BH 與 NS（每 fold 訓練 105 筆：45/60 或 60/45）
  → `results/fold_checks.csv` 全部 True。A、B 使用完全相同的 120 筆與相同的 folds（`results/folds_loso.csv`）。
- class_weight=balanced：權重 = n_samples / (2 × 該類樣本數)，抵銷每 fold 45:60 的不平衡。每源觀測數相同，因此沒有另外加來源權重。
- 來源層級：該天體所有 out-of-fold BH 分數取平均，≥0.5 判為 BH（門檻事先固定）。
  BH 分數是模型輸出的排序分數，**不是校準過的物理機率**；同一天體的多次觀測也不當作獨立證據相乘。

## 4. 結果

### 4.1 觀測層級（LOSO，`results/metrics_observation_level.csv`）

| 表示 | 模型 | BH recall | NS recall | balanced acc. | 每源正確率平均 | 最差來源 |
|---|---|---|---|---|---|---|
| A | Dummy | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| A | LogReg | 0.62 | 0.78 | **0.70** | 0.70 | 0.27 |
| A | RandomForest | 0.57 | 0.82 | **0.69** | 0.69 | 0.27 |
| B | LogReg | 0.72 | 0.80 | **0.76** | 0.76 | 0.13 |
| B | RandomForest | 0.72 | 0.77 | **0.74** | 0.74 | 0.13 |

混淆矩陣（列 = 真實, 行 = 預測 [BH, NS]）：
A-LogReg [[37, 23], [13, 47]]；A-RF [[34, 26], [11, 49]]；B-LogReg [[43, 17], [12, 48]]；B-RF [[43, 17], [14, 46]]。

**為什麼 Dummy 是 0 而不是 0.5？** 在 LOSO 中，拿掉一個 BH 天體後，訓練集是 45 BH : 60 NS，
prior 策略就預測 NS，於是被保留的 BH 全錯；拿掉 NS 時剛好相反。這是「留一組」評估的已知現象。
它提醒我們：這裡的「隨機水準」不是固定 0.5，而且只有 8 個天體時，結果對組成非常敏感。

### 4.2 來源層級（`results/metrics_source_level.csv`, `results/per_source_results.csv`）

| 表示 | 模型 | 分對來源 | BH | NS | 分錯的來源 |
|---|---|---|---|---|---|
| A | LogReg | 6/8 | 2/4 | 4/4 | GRS 1915+105, XTE J1550-564 |
| A | RandomForest | 7/8 | 3/4 | 4/4 | 4U 1543-47 |
| B | LogReg | 6/8 | 3/4 | 3/4 | GRS 1915+105, Aql X-1 |
| B | RandomForest | 6/8 | 3/4 | 3/4 | GRS 1915+105, Aql X-1 |

各源觀測正確率（LOSO）：

| 來源 | A-LR | B-LR | A-RF | B-RF |
|---|---|---|---|---|
| GRO J1655-40 (BH) | 0.67 | 1.00 | 0.80 | 1.00 |
| GRS 1915+105 (BH) | 0.67 | **0.13** | 0.87 | **0.13** |
| XTE J1550-564 (BH) | **0.27** | 0.73 | **0.33** | 0.73 |
| 4U 1543-47 (BH) | 0.87 | 1.00 | **0.27** | 1.00 |
| 4U 1636-53 (NS) | 1.00 | 1.00 | 1.00 | 1.00 |
| 4U 1608-52 (NS) | 0.80 | 0.73 | 0.87 | 0.93 |
| 4U 1728-34 (NS) | 0.87 | 1.00 | 0.87 | 0.73 |
| Aql X-1 (NS) | 0.47 | 0.47 | 0.53 | 0.40 |

圖：`figures/step4_loso_scores.png`（各源分數分布）、`figures/step5_per_source_A_vs_B.png`。

### 4.3 對照：若不按天體分組（事先宣告的次要診斷）
Observation-wise stratified 5-fold（同一天體同時在訓練與測試）：balanced accuracy
A-LR 0.80、A-RF 0.89、B-LR 0.83、B-RF 0.89（`results/secondary_observation_split.csv`）。
比 LOSO 高 0.05–0.20，**這個差距就是「認得同一天體」造成的高估**，也是本研究以 LOSO 為主評估的原因。

### 4.4 錯誤分析（`results/error_analysis.md`, `figures/step5_*.png`）
**數據直接支持的觀察：**
1. **沒有單一來源主宰平均值**：任拿掉一個來源，每源平均正確率只在 0.65–0.85 之間變動。
   但每個模型都有 1–2 個來源多數分錯，而 **哪些來源分錯會隨表示法改變**：
   A 下錯的是 XTE J1550-564（及 RF 的 4U 1543-47），B 下錯的是 GRS 1915+105 和 Aql X-1。
2. **A vs B 不是「一個全面比另一個好」**：B 的觀測層級指標略高（0.74–0.76 vs 0.69–0.70），
   但來源層級差不多（6/8 vs 6–7/8）。逐筆比較（RF）：兩者都對 59、只有 A 對 24、只有 B 對 30、都錯 7。
   在只有 8 個天體時，差一兩個天體不能當成顯著差異。
3. **錯誤與亮度、硬度有關**（hardness–intensity 圖 `figures/step5_hid_errors_*.png`）：
   - 表示 A：分錯的 BH 多是 **較暗且較硬** 的觀測（XTE J1550-564 的 5–25 keV 淨率只有 3–200 c/s/PCU，
     計數比 (10–25)/(5–10) 為 0.52–0.81）；A-LR 的錯誤觀測淨率中位數 75 c/s/PCU，正確者為 225。
   - 表示 B：GRS 1915+105 的形狀被判為 NS（15 筆有 13 筆錯）；Aql X-1 的較硬觀測被判為 BH。
   - LR 在真實 NS 內，BH 分數與硬度正相關（Spearman ρ = +0.67（A）與 +0.37（B）），也就是「越硬越像 BH」。
4. **與曝光、背景比例、N_PCU、deadtime 的關係不明顯**：正確與錯誤觀測的中位數差異小且方向不一致
   （描述性比較；觀測在天體內聚集，不做顯著性檢定）。
5. **狀態（hard/soft state）**：本樣本沒有整理可查證的逐 ObsID 狀態標籤，因此不做狀態分析；
   上面的計數比只是儀器空間的硬度指標，不是狀態標籤。

**可能的解釋（未驗證）：**
- 在 5–25 keV，BH 的 hard state 與 NS 的 hard（island）state 都是類冪律譜；BH soft state 與 NS 的 soft 譜
  （盤＋邊界層）也都有熱成分。模型可能主要學到「硬度／曲率」，而這在兩類之間本來就重疊。
- 表示 A 在訓練集裡「BH 通常比較亮」（GRS 1915+105、GRO J1655-40 很亮），因此暗的 BH（XTE J1550-564 的衰減期）
  容易被判為 NS——這是亮度資訊可能帶來的捷徑。
  但觀測到的計數率同時受距離、吸收和吸積率影響，不是天體本身的性質。
- GRS 1915+105 很特殊（長期接近 Eddington 亮度、變化劇烈），它的形狀可能更像 NS 的 soft 譜。
  在 B 中拿掉亮度資訊後，它就失去了「很亮」這個在 A 中幫它被判為 BH 的線索。
- Aql X-1 有明顯的 hard state 觀測，形狀接近 BH 的 hard state。

**需要更大樣本才能檢驗的假說：**
- 「只看形狀」的泛化是否真的優於「保留亮度」——需要數十個天體才能分辨差異。
- 加入狀態資訊（或在同一狀態內比較）是否能分開 BH 與 NS。
- 若改用 response-unfolded 或擬合後的物理量（本次刻意不做），PCU 組合造成的約 ±10% 儀器傾斜是否會影響結論。

## 5. 限制
1. **只有 8 個天體**：LOSO 的有效樣本數是 8，不是 120。任何指標都有很大不確定性；結果不能推論到整個 XRB 族群。
2. 只用 gain epoch 5（2000–2006）；4U 1543-47 與 GRO J1655-40 各只有一次爆發，時間覆蓋有限。
3. 特徵在儀器計數空間：未 unfolding；不同 PCU 組合的 response 差異約 ±10%（高能端），只能部分透過每 PCU 正規化抵銷。
4. Deadtime 只做 good-xenon 下限修正；背景模型系統誤差沒有納入誤差；StdProd 的 GTI 篩選是通用設定。
5. 每源 15 筆以時間分層抽樣，可能沒有完整代表各源的狀態分布；沒有狀態標籤。
6. 沒有做完整的 Pattnaik／Garg 重現（例如 43 通道 XSPEC 產物、61 個天體）；本 pilot 的數字不能直接與原文比較。
7. scikit-learn 1.8 對 `penalty='l2'` 發出 FutureWarning（目前行為相同，未來版本需改寫參數）。

## 6. 建議的下一步（本次未執行）
- 擴充到數十個天體（仍用 LOSO 或 group k-fold），並計算來源層級指標的 bootstrap（以天體為單位）區間。
- 下載 Standard-1 做完整 deadtime 修正；或在 WSL/HEASoft 環境以 XSPEC 產生與原文一致的產物。
- 整理文獻中的狀態標籤，檢查模型是否只學到「硬度」。

## 附：檔案對照
- 原始 FITS：`data/raw/spectra/<ObsID>/`（URL、SHA256：`logs/downloads.jsonl`；對應關係：`data/observations.csv` 的 `url_base`, `path_*`）
- 處理後：`data/processed/features.npz`、`data/processed/feature_definitions.csv`
- 檢查：`results/data_checks.md`、`results/attrition_*.csv`
- 預測：`results/oof_predictions_loso.csv`（每筆：representation, model, fold, source_id, obs_id, true_label, BH_score, predicted_label）
- 圖：`figures/step2_two_sources.png`、`figures/step3_*.png`、`figures/step4_loso_scores.png`、`figures/step5_*.png`
- 紀錄：`logs/*.log`、`reports/decision_log.md`、`reports/progress.json`
