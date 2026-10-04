# v7 預先設定：能態條件評估、堵漏洞（爆發污染、持續黑洞）、跨儀器（MAXI）

撰寫：2026-10-05，**在看過 v1–v6 全部結果之後**、在下載任何 v7 資料或訓練任何 v7 模型之前。本文件等待使用者核准後才執行。
目的：讓專案從 pilot 走向可發表——(A) 能態條件評估；(B) 堵漏洞：B1 type-I 爆發污染（MINBAR）、B2 納入動力學確認的持續黑洞；(C) 用 MAXI/GSC 先重現 de Beurs et al. 2022，再套用本專案的嚴格流程。
版本：repo 已有 v1–v6，本輪為 **v7**（子分析 v7a＝A、v7b1＝B1、v7b2＝B2、v7c＝C）。輸出 `data/v7*/`、`results/v7*/`、`figures/v7*/`、`logs/v7*/`；分支 `v7-analysis`（自 master `f1bc771`）。
`config.py` 新增 v7 區塊（只在 `XRB_VERSION` 以 v7 開頭時生效；v4／v5／v6 區塊的條件擴充為也對 v7 生效，以便重用 `v4lib`／`v5lib`／`v6lib`；v7 區塊放在最後，覆寫選樣窗為 gain epoch 5）。v1–v6 的所有設定值不變（提交前逐一比對）。

## 0. 與既有版本的關係（避免重做，也避免混淆）
- v4 已用 Standard-1 光變做過 burst 偵測（Galloway+2008 §2 判準＋固定形狀規則）與逐張目視（`results/v4/burst_flags.csv`、`burst_visual.csv`），並發現排除後 v1–v3 結論不變。
  v7b1 新增的是**以 MINBAR 官方爆發表為主**的比對、同一時間分段的**替補**敏感度分析、以及 B-LR／B-RF。v4 的 Standard-1 偵測器與目視結果原樣作為 1c 的獨立交叉檢查（不修改）。
- v5／v6 已有 Standard-1 cospectrum 時間特徵；v7a 只用其中 0.1–4 Hz 的總 rms 定義能態，**不把 rms 當分類特徵**，評估的仍是 v2 既有的 OOF 預測。
- v6 已把 Cyg X-1、LMC X-3 當「外部測試天體」（所有 gain epoch、凍結模型）；v7b2 依使用者要求改為 **v2 規則（epoch 5）納入訓練集**，是不同的問題。

## 1. 共同規則
1. 不修改任何既有版本的資料、fold、程式行為或輸出。
2. 主評估 LOSO；來源層級＝該源 OOF BH 分數平均；門檻固定 0.5（除非該分析明確在內層選門檻）。標題指標：來源層級 balanced accuracy 與 AUC；另報觀測層級。
3. 不確定性：在 BH、NS 內各自有放回抽天體 2000 次（seed 42，與 `09_bootstrap_sources.py` 相同抽樣程序：天體名稱排序、`default_rng(42)`）。配對比較用同一組抽樣。
   **「有差異」＝95% 區間不含 0；否則一律寫「未偵測到」。**
4. 超參數、門檻、模型選擇只能在訓練天體內（巢狀）完成。LR／RF 沿用 v2 固定設定（`LR_PARAMS`、`RF_PARAMS`），不調參。
5. 事實查證見 §2；查不到就記錄並停下來問使用者。
6. 所有變更記入 `reports/decision_log.md`，註明是否在看過 v7 結果之後。
7. 報告繁體中文：做了什麼→結果→解讀（數據直接支持／可能解釋（未驗證）／需要更多資料的假說）→限制→與預先設定的差異；明寫本設定寫於看過 v1–v6 之後。
8. 每個子分析在本文件中只宣告**一個 primary**（下文標 ★），其餘為描述性，避免多重比較；描述性結果不作「有差異」的結論。

## 2. 查證結果（2026-10-05，撰寫本文件時）

| 項目 | 查證內容 | 來源 |
|---|---|---|
| MINBAR | DR1：7083 個爆發、85 個爆發源、118,848 筆觀測，1996-02-08 至 2012-05-03；RXTE/PCA、BeppoSAX/WFC、INTEGRAL/JEM-X。官方發布在 Monash Bridges（CC BY 4.0）：`minbar.txt`（爆發表 v6，2,457,892 bytes，figshare md5 a398e7b9…7da40，DOI 10.26180/5e4ca9f10d173，下載 https://ndownloader.figshare.com/files/23201936）、`minbar-obs.txt`（觀測表 v7，51,941,646 bytes，md5 311b2a0e…2d9a75c，DOI 10.26180/5e4f541ece460，https://ndownloader.figshare.com/files/24131849）。期刊電子版另見 VizieR J/ApJS/249/32（table11＝爆發表 7111 列；欄位 Name、Inst（`XPn`＝RXTE/PCA，n＝開啟 PCU 數）、obsid、Time＝爆發開始 MJD(UT)、dur、sflag 等） | Galloway et al. 2020, ApJS 249, 32；bridges.monash.edu collection 4858818；CDS ReadMe |
| 能態門檻 | Remillard & McClintock (2006, ARA&A 44, 49) Table 2：thermal 態 r < 0.075、hard 態 r > 0.1；r＝0.1–10 Hz 積分的總 rms power，以平均源計數率的分數表示（PCA 約 2–30 keV） | arXiv:astro-ph/0606352 Table 2 與 §4.2 |
| Z 源 | GX 5-1、Cyg X-2、GX 340+0、GX 349+2、GX 17+2、Sco X-1（Hasinger & van der Klis 1989）；v2 樣本中為 **Cyg X-2、GX 17+2** | 二手文獻引述 Hasinger & van der Klis 1989（原文未取得，報告中註明） |
| Cyg X-1 | 動力學確認 BH：M_X = 21.2 ± 2.2 M☉、M₂ = 41 ± 7 M☉、P = 5.60 d、d = 2.2 kpc；伴星 HD 226868，O9.7 Iab（超巨星）；Marcel+2026 Table 1 分界線以上（高質量） | Marcel et al. 2026（arXiv:2606.19952）Table 1；Miller-Jones et al. 2021；SIMBAD（Sota+2011） |
| LMC X-1 | 動力學確認 BH：M_X = 10.9 ± 1.4 M☉、M₂ = 31.8 ± 3.5 M☉、P = 3.90 d；伴星 SIMBAD 光譜型 O8(f)p（**未標示為超巨星**）；Orosz+2009：伴星「幾乎填滿 Roche lobe（~90% 以上）」、X 光調變可用星風中的 Thomson 散射解釋；Marcel+2026 分界線以上（高質量） | Marcel+2026 Table 1；Orosz et al. 2009（arXiv:0810.3447）；SIMBAD（2010AJ 139 1283） |
| LMC X-3 | 動力學確認 BH：M_X = 7.0 ± 0.6 M☉、M₂ = 3.6 ± 0.6 M☉、P = 1.70 d；SIMBAD 光譜型 B2.5 Ve；**Marcel+2026 Table 1 把它放在分界線以下（低質量側）**，SIMBAD 物件類型為 HXB | Marcel+2026；Orosz et al. 2014（arXiv:1402.0085）；SIMBAD |
| de Beurs+2022 | 44 源（12「BH」中 **7 個是 BH candidate**，含 Cyg X-3；20 NPNS；12 脈衝星）；MAXI/GSC on-demand 2–3、3–5、5–12 keV、1 日；SC = (M−L)/(M+L)、HC = (H−L)/(H+L)，再縮放到 0–1；RelInt = (L+M+H) / 該源第 99.99 百分位；3σ（三能段各 √3σ）、剔除偏離平均 ≥10σ、≥100 點；依源大小反比抽 20%、10 個子樣本；LOSO（三類）；每源取觀測平均機率、10 次中位數；KNN k = 24（caret `knn3Train`）：84.1%、BH 50%；SVM C = 0.655、γ = 0.585（e1071 `svm`，預設標準化，Platt 機率）：81.8%、BH 42%（k、C、γ 是在同一個 LOSO 上挑的） | arXiv:2204.00346 §2、§4、Table 1–4、Fig. 9；GitHub zdebeurs/3ML_methods_for_XRB_classification（MIT；含 44 源處理後 CCI 檔與 10 個子樣本） |
| MAXI 取得方式 | 標準產品：每源 `star_data/<J>/<J>_g_lc_1day_all.dat`（約 0.34 MB）、`_1orb_all.dat`；欄位 MJDcenter、2–20、2–4、4–10、10–20 keV（ph/s/cm²）及誤差。On-demand（maxi.riken.jp/mxondem）只有網頁表單、**無程式化介面** | maxi.riken.jp `lc_readme.txt`、mxondem 頁面（實際下載 Cyg X-1 1-day 檔確認格式） |
| 確認 BH 名單（C2） | Marcel+2026 Table 1「Dynamically confirmed black hole X-ray binaries」共 25 個；作者明列 Cyg X-3、4U 1630-47、4U 1957+115、MAXI J1803-298 等為「未確認」 | arXiv:2606.19952 §1.2、Table 1 |

## 3. v7b1：爆發污染（最先做）
1a. 從 Monash Bridges 下載 `minbar.txt`、`minbar-obs.txt`；記錄 URL、bytes、SHA256，並與 figshare md5 核對。
1b. 對 v2 的 456 筆（及 v7b2 新增觀測）：讀 StdProd `s2` 的 STDGTI（MET 秒）→ MJD(TT)（MJDREF）→ UTC（astropy）。
   **受污染**＝任一 MINBAR 爆發（任何儀器、任何發源天體）的區間 [Time, Time + dur] 與能譜 GTI 重疊；dur 缺值時用 300 s。
   另報 obsid 直接比對的結果與一致性。MINBAR 涵蓋到 2012-05-03，RXTE 全期間都在內。
1c. 獨立交叉檢查：v2 觀測直接使用 v4 已凍結的 Standard-1 偵測結果（自動規則與目視）；新觀測以同一程式（`17_v4_burst_detect.py` 的規則）偵測。
   報告與 MINBAR 的一致性表（兩者皆有／只有 MINBAR／只有 Standard-1），所有不一致者與隨機 10 筆一致者出圖到 `figures/v7b1/`。
1d. 主分析：**排除**受污染觀測（不補抽，維持原抽樣凍結）；敏感度：依 v2 候選清單，同一時間分段的下一個合格觀測替補（替補者也要通過 MINBAR 檢查）。
   對 H-LR、H-RF、B-LR、B-RF 重跑 LOSO，與 v2 在共同天體上配對比較。★ primary：**H-LR（排除版）− v2 H-LR** 的來源 BA 與來源 AUC。
1e. 報告獨立一節：v1–v3（以及 v4–v6）的結論是否受爆發污染影響。

## 4. v7a：能態條件評估
2a. 能態指標（與能譜特徵獨立）：Standard-1、128 s 列、能譜 GTI 內，排除 1b／1c 標出的爆發區間（爆發開始前 20 s 至 Time + dur）。
   0.1–4 Hz（Fourier 指數 j = 13–511；受 0.125 s 解析度限制，**與 RM06 的 0.1–10 Hz 不同**，4–10 Hz 的功率沒有計入，rms 會偏低、使「硬態類」判定偏保守）。
   rms 估計量：v6 的**全配對 cospectrum**（不同 PCU 的 Poisson 雜訊與 deadtime 雜訊互不相關，cospectrum 的白雜訊期望值為 0，因此不需要模型化 deadtime 修正的 Poisson 水準；Bachetti et al. 2015、Bachetti & Huppenkothen 2018）；
   分箱修正（van der Klis 1989 Eq. 2.19）；以 StdProd 背景率做 (S+B)/S 修正（rms 以源平均計數率為分母，與 RM06 相同）；每觀測取有效列中位數。
   只用 ≥ 2 個 PCU 開啟的列；有效列 < 3 的觀測能態記為「無法判定」並列出（不用單一 PCU 的自功率估計，因為那需要 deadtime 修正的 Poisson 水準）。
   分類：rms > 0.10＝「變化強（硬態類）」、rms < 0.075＝「變化弱（軟態類）」、其餘＝「中間」。門檻沿用 RM06 Table 2，不依結果調整。
2b. 健全性檢查（出圖：各天體 rms 對硬色）：通過條件（事先寫定）：XTE J1118+480 有能態的觀測中 ≥ 2/3 為「硬態類」；Z 源（Cyg X-2、GX 17+2）合計 ≥ 2/3 為「軟態類」。任一不通過 → 停下來回報，不改門檻。
2c. 主要分析：不重新訓練，使用 v2 的 LOSO OOF（另報 1d 排除後版本），按能態分層計算**觀測層級** AUC 與 balanced accuracy（H-LR、H-RF、B-LR、B-RF）。
   不確定性：重抽天體後在各層重算（同一抽樣）。★ primary：**H-LR 的「軟態類 AUC − 硬態類 AUC」**；其他模型描述性。
2d. 報告每層 BH／NS 的觀測數與天體數、每個 BH 天體在三層中的比例。某層 BH 天體 < 3 → 該層只描述、不檢定（含 primary）。
2e. 描述性：v4 的顏色重疊區（c1 ≥ 0.70 且 c2 ≥ 0.20；**此矩形是在 v4 看過 v2 顏色圖後定的，用分類特徵本身定義，只作描述**）內外的表現。
2f. 探索性（非預先設定的主要分析）：只用「硬態類」觀測重新做 LOSO（H-LR、H-RF、B-LR、B-RF），看硬態內部是否有可測的分離能力。

## 5. v7b2：持續黑洞（下載前停下來回報名單與下載量）
3a. 查證結果見 §2：Cyg X-1、LMC X-1、LMC X-3 都在 Marcel+2026「動力學確認」表中。
3b. v2 完全相同的規則：gain epoch 5（MJD 51677–55931）、StdProd 完整、曝光 ≥ 1000 s、STD1RATE ≥ 5、0.1° 指向、≥ 10 筆合格、15 段時間分層（v2 抽樣演算法、固定 seed）、Standard-1 完整 deadtime、品質規則同 v2；記錄 DTF 分布。
   目錄層級試算（未下載）：Cyg X-1 1205 筆合格（STD1RATE 中位 1058、最大 3839 c/s/PCU → 預估 DTF 數 %）、LMC X-3 830 筆、LMC X-1 見下方**待決事項 1**。
3c. 主分析：v2 的 31 源＋3 個持續黑洞（34 源、10 BH）。敏感度：只加 LMC X-3（32 源）。
   比較：(i) 在原 31 源上配對比較（新訓練集對原 31 源的 OOF vs v2 OOF）；(ii) 在全部 34 源上報告來源層級指標與區間。
   模型 H-LR、H-RF、B-LR、B-RF。★ primary：**(i) H-LR 在原 31 源上的來源 BA 與 AUC 配對差**。
3d. 捷徑檢查：新天體在顏色圖上的位置、它們被保留（LOSO）時的分數，以及「新天體被拿掉後其他天體的分數變化」。
3e. 下載前若查證不符，停下來回報（目前三者皆符合）。

## 6. v7c：MAXI 跨儀器（下載前停下來回報）
4a. 取得方式（§2）：on-demand 無程式化介面 → C1 用 de Beurs 公開的處理後 CCI 檔（他們的確切輸入）；C2／C3 用 MAXI **標準產品**（2–4、4–10、10–20 keV，1 日），能段差異如下表並寫入報告。

| | de Beurs（on-demand） | v7c2（標準產品） |
|---|---|---|
| Low／Medium／High | 2–3／3–5／5–12 keV（counts） | 2–4／4–10／10–20 keV（ph/s/cm²） |
| SC、HC | (M−L)/(M+L)、(H−L)/(H+L)，縮放到 0–1 | 同式，用上列能段；不另縮放（LR／RF 內部標準化） |
| RelInt | (L+M+H)／該源第 99.99 百分位 | 同 |

4b. **C1 忠實重現**：44 源與標籤、`Training_and_Testing/*.asc` 與 10 個 20% 子樣本（D1–D10）原樣使用；三類 LOSO；KNN k = 24（歐氏距離、投票比例，不標準化）；SVM RBF C = 0.655、γ = 0.585（訓練集標準化、Platt 機率、random_state = 42）；
   每源取觀測平均機率 → 10 個子樣本的中位數 → 最大類別。重現成功條件（事先寫定）：整體來源正確率與論文最終值（KNN 84.1%、SVM 81.8%）相差 ≤ 2 個天體，且 BH 正確數與論文（KNN 6/12、SVM 5/12）相差 ≤ 1 個。不成功 → 停下來回報原因，不繼續 C2。
4c. **C2 嚴格流程**（重現成功後）：
   - 標籤（下載前凍結）：BH＝Marcel+2026 Table 1 中有 MAXI 標準產品者；NS＝MINBAR table1 的 115 個爆發源（type-I 爆發）或 Patruno & Watts 2021 Table 1 的脈衝星；名單與每源證據寫入 `data/v7c/sources.csv`。
   - 主要任務：BH vs 非脈衝 NS（LMXB 爆發源）。次要：BH vs 脈衝星（多為 HMXB；系統類型是混淆因子）。
   - 資料篩選同 de Beurs（3σ、10σ 剔除、≥ 100 點）；每個訓練天體最多隨機取 200 點（seed 42）以避免大源主導；測試天體用全部合格點。
   - 模型：LR、RF（repo 設定）＋巢狀 LOSO 調參的 KNN（k ∈ {5, 15, 24, 35}）與 SVM（C ∈ {0.1, 1, 10} × γ ∈ {0.1, 0.585, 3}），內層以來源 AUC 選。
   - 預先設定的配對比較：(i) 3D CCI（SC、HC、RelInt）vs 2D 顏色（SC、HC）——強度是否有增量；
     (ii) 含 2–4 keV 的兩個顏色（SC、HC）vs 只用 ≥ 4 keV 的一個顏色 (H−M)/(H+M)——N_H 指紋效應（維度不同，結果只解讀為「2–4 keV 是否帶來可測增量」）。
     ★ primary：**LR 的 (i) 與 (ii)**（各報來源 BA、AUC）；其他模型描述性。
4d. C3 跨儀器一致性：同時在 RXTE（v2／v4b2／v7b2）與 MAXI C2 樣本中的天體，比較兩儀器的來源層級 BH 分數（Spearman、逐源一致率）；兩者時期與爆發不同，只作描述。

## 7. 待決事項（2026-10-05 07:23 使用者核准：「按照你的直接 continue 到最後」→ 三項皆採下列建議）
1. **LMC X-1 的指向規則**：RXTE 的 LMC X-1 目錄中位指向距 SIMBAD 位置 0.263°。照 v2 字面規則（指向距「目錄中位指向」≤ 0.1°）有 419 筆合格，但這些指向偏離 LMC X-1 約 0.26°（源在視野偏軸、可能混入鄰近源）。
   若要求指向距 **SIMBAD 位置** ≤ 0.1°（v4b2／v6 的位置規則），仍有 **31 筆**合格（≥ 10）。**建議採用後者**（兩種解讀都滿足的子集）。
2. **敏感度分析的理由**：指示寫「排除兩個靠星風吸積的超巨星系統 Cyg X-1、LMC X-1」。查證：Cyg X-1 是 O9.7 Iab 超巨星；LMC X-1 的伴星在 SIMBAD 為 O8(f)p、Orosz+2009 指出它幾乎填滿 Roche lobe。
   **建議**把理由改寫為「排除 Marcel+2026 Table 1 分界線以上的兩個高質量 X 光雙星」（成員相同，描述較準確）。
3. **C1／C2 的資料**：C1 用 de Beurs 公開的處理後檔案（on-demand 無法自動化）；C2 改用標準產品能段（2–4／4–10／10–20 keV），比較 (ii) 變成「含 2–4 keV 的兩色 vs ≥ 4 keV 的一色」。

## 8. 預估下載量與計算時間
| 階段 | 下載 | 計算 |
|---|---|---|
| v7b1 | MINBAR 約 54 MB；替補觀測（依污染數，估 30–60 筆 × 約 0.4 MB）約 10–25 MB | MINBAR 比對數分鐘；LOSO 4 模型 × 2 版本數分鐘 |
| v7a | 無（Standard-1 已在 `data/raw/std1`） | 約 1 分鐘（重用 v6 估計量） |
| v7b2 | 3 源 × 15 筆（Std2 三檔＋Standard-1）約 10–20 MB | 數分鐘 |
| v7c | de Beurs repo（處理後資料約 10 MB）；MAXI 1 日光變約 0.34 MB × 約 60 源 ≈ 20 MB | C1：KNN／SVM × 44 折 × 10 子樣本，16 核約 10–20 分鐘；C2 巢狀 SVM 約 30–60 分鐘 |

## 9. 不做的事
看到結果後改門檻、頻段、名單或模型；把 rms 當主要分類特徵；在測試天體上調門檻；對 MAXI on-demand 做網頁自動化。

## 10. 收尾
`reports/report_v7_zh-TW.md`；README 與 `final_report_zh-TW.md` 新增一節（不改既有數字）；一張總結圖（各能態層 AUC 與區間、持續黑洞加入前後、RXTE vs MAXI）；
所有 OOF、fold、bootstrap 存 CSV；下載檔記錄 URL 與 SHA256；`run_v7.sh`、`run_v7.ps1`。
