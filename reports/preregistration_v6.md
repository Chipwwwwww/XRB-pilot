# v6 預先設定：確認時間訊號，並用新方法把它變成可信的分類

撰寫：2026-10-01（約 03:00），**在看過 v1–v5 全部結果之後**、在下載任何 v6 資料或計算任何 v6 特徵之前。
依據：使用者要求「deep think and come up with some innovations … make it v6」「come up with new algorithms or methods to do some innovative work」
「before v6 the deep thinking is important, you can do some combination or improvement of those algorithms or even come up with something new」。
本設定由我自行設計並核准（沿用 v5 的授權方式），除非遇到重大問題不停下。v1–v5 的資料、fold、程式行為與輸出都不改；
v6 以 `XRB_VERSION=v6` 切換，輸出在 `data/v6/`、`results/v6/`、`figures/v6/`、`logs/v6/`，分支 `v6-analysis`（自 `v5-analysis` 分出）。

## 0. 設計思路（為什麼是這些方法）
v1–v5 的證據決定了方向：
1. 5–25 keV 能譜的資訊幾乎都在兩個顏色裡；**加彈性沒有用**：v4a 巢狀自動選擇的內層 AUC 0.96–1.00、外層 0.75，31 個天體上挑模型本身就過度樂觀。
2. 錯誤集中在顏色重疊的硬態；v5 顯示缺的是**時間資訊**：同樣顏色下 BH 在 0.016–0.1 Hz 的變異較強（探索性，primary 依嚴格規則未偵測到，且描述性比較共用天體）。
3. 所以 v6 不加模型彈性，而是加**結構**（物理歸納偏誤）、**更好的估計量**、**正確的推論**與**真正沒見過的天體**：
   - 最需要的是**確認**：在訓練時沒用過的天體上，以凍結（不重新訓練）的模型檢驗 v5 的主張 → primary。
   - 時間特徵的估計可以更準：用**所有 PCU 配對**的 cospectrum（封閉式），而不是單一 A/B 切分；單一 PCU 的觀測改用已驗證的自功率估計補上。
   - 物理假說「BH 的特徵頻率較低」需要一個直接的量：**νPν 質心頻率 ν_c**。
   - 線性 LR 把「rms 越高越像 BH」套到所有顏色，但資訊只在硬態。新的**顏色條件時間概似比分類器（CCTLR）**：
     判別式的 H-LR 對數勝算 ＋ 生成式的 log p(T | H, BH) / p(T | H, NS)，天生只在兩類時間分布不同的顏色區域起作用；缺值時間特徵＝零證據，不需要補值。
   - 「同顏色下時間不同」應該有**正確的假設檢定**：觀測在天體內相關，因此以**天體為單位的標籤置換**，搭配不使用標籤的顏色殘差化。
   - 分類要能用：**天體層級 conformal 預測集**（{BH}／{NS}／{無法判斷}，有覆蓋保證）與**觀測數預算曲線**（新天體需要幾次指向）。
   - AUC 會碰到天花板（v5 的區間下限剛好 0），另報不會飽和的**天體層級 proper scoring rule**（log loss、Brier）。

## 1. 共同規則（沿用 v4／v5）
LOSO；天體分數＝OOF BH 機率平均；門檻 0.5；頭條指標：來源 balanced accuracy、來源 AUC；觀測 BA 另報；
分 BH／NS 各自重抽天體的配對 bootstrap（2000 次、seed 42）；「有提升」＝配對差 95% 區間完全 > 0，否則「未偵測到」。
所有模型用 v2 固定超參數，沒有選擇步驟。每個變更寫入 `decision_log.md` 並註明是否在看到 v6 結果之後。

## 2. v6a（PRIMARY）：凍結模型的外部驗證
- **訓練**：S1（v2 的 456 筆、31 個天體），表示 H_R（v4b2 的冪律正規化顏色，橋接檢查 ρ = 0.994，可跨 gain epoch）與 v5 的 T1–T3（v5 估計量、v5 補值規則，補值中位數取自 S1）。
  兩個模型各訓練一次後凍結：基準 H_R-LR、主張 H_R+T-LR（LR_PARAMS，balanced）。
- **外部天體集 E**（所有 v1–v5 訓練都沒用過）：
  1. v4b2 新增的 15 個天體（BH：XTE J1859+226、V4641 Sgr；NS：13 個 Galloway+2008 burster），使用 v4b2 已處理的 221 筆。
  2. 新增 BH：Casares & Jonker (2014, SSRv 183, 223) §3／Table 2 的高質量 X 光雙星動力學 BH：Cyg X-1、LMC X-1、LMC X-3、M33 X-7。
  3. 新增 NS：Patruno & Watts (2021, arXiv:1206.2727) Table 1 的 AMXP（以脈衝確認的 NS），扣除已在 S1 或 v4b2 的天體與 RXTE 結束後才發現者：
     XTE J1751-305、XTE J0929-314、XTE J1807-294、IGR J00291+5934、Swift J1756.9-2508、NGC 6440 X-2、IGR J17511-3057、Swift J1749.4-2807、IGR J17498-2921、IGR J18245-2452。
  - 位置以 CDS Sesame 取得；RXTE MissionLongData 目錄中位指向 ≤ 0.1°；與 v2／v4b2 任一天體位置相距 ≤ 0.1°（同一視野，例如球狀星團）者排除。
  - 合格：與 v4b2 相同（曝光 ≥ 1000 s、STD1RATE ≥ 5、指向 ≤ 0.1°、MJD < 55931、全部 gain epoch）；合格指向 ≥ 10 才納入；每源 15 筆時間分層（v2 演算法），品質規則同 v2。
- **主要比較**：E 上 H_R+T-LR vs H_R-LR（同一批觀測），來源 AUC 與來源 BA 的配對 bootstrap（在 E 的天體上重抽）。
- 若 E 的 BH 天體 < 3 個，primary 不作判讀，只報描述。
- **透明聲明**：E 中 v4b2 的 15 個天體從未用來訓練凍結模型，但我在 v4b2／v5 看過其他模型在它們上的結果（例如 H-LR 把 4U 2127+119、XTE J1710-281 判錯）。
  因此另報只含 v6 新天體（E_new：新 BH＋AMXP）的敏感度分析；E_new 是 v1–v6 中我完全沒看過任何結果的天體。
- **壓力測試（描述性，不進 primary）**：Patruno & Watts Table 1 的慢速脈衝星（2A 1822-371、4U 1626-67、GRO J1744-28、Her X-1）——自轉頻率 0.13–2.1 Hz 落在 T 的頻段內，檢驗相干脈衝是否被誤當成 BH 的寬頻變異。

## 3. v6b：新的時間估計量
1. **全配對 cospectrum**：n 個開啟 PCU 的 FFT X_i，Σ_{i<j} Re(X_i X_j*) = (|Σ_i X_i|² − Σ_i |X_i|²)/2；
   分數變異 f = (2/N²) Σ_{j∈band} [(|ΣX|² − Σ|X_i|²)/2] / sinc²(πj/N) ÷ Σ_{i<j} s_i s_j（s_i＝PCU i 的源平均計數/bin）。其餘（列規則、背景、中位數、頻段、≥ 3 列）同 v5。
2. **混合估計**：只有 1 個 PCU 開啟的列，若總計數率 ≤ 500 counts/s/PCU，改用自功率減 Poisson 水準（v5 的交叉檢查範圍）；否則該列無效。
   T*＝每觀測中位數（全配對列與單 PCU 列一起取中位數）。
3. **νPν 質心頻率 ν_c**：以 1/128–4 Hz 的 9 個對數等寬頻段計算全配對 cospectrum 變異（每頻段取列中位數）P_b；
   w_b = max(P_b, 0)/Δln ν_b；ln ν_c = Σ w_b ln ν_b / Σ w_b（ν_b 為頻段幾何中心）。T*_total < 0.05 或 Σ w_b ≤ 0 時缺值。
4. 驗證（計算真實特徵前）：合成資料中 3、4、5 個 PCU 的純 Poisson 變異比 A/B 切分降低 ≥ 25%；正弦 rms 0.2 的恢復誤差 < 10%；
   ν_c 對 0.05／0.5／3 Hz 正弦的恢復在 ±1 個對數頻段內。真實資料（S1）報告奇數列 vs 偶數列的 split-half Spearman（T* vs v5 T）。

## 4. v6c：顏色條件時間概似比分類器（CCTLR，新方法）
- 對數勝算 ℓ = ℓ_H(H) + Λ(T | H)。ℓ_H＝H-LR（LR_PARAMS，balanced）的 logit。
- Λ = Σ_k [log t₄(T_k; μ_BH,k(H), σ_BH,k) − log t₄(T_k; μ_NS,k(H), σ_NS,k)]，k ∈ {T1, T2, T3}；t₄＝自由度 4 的 Student-t（對 burst、dip 等離群值穩健）。
  μ_c,k(H) = β_c,k · [1, h₁, h₂]（h＝訓練集標準化的兩個顏色），以類內**天體等權重**的加權最小平方估計；σ_c,k＝加權殘差標準差（下限 0.01）。
- 分數＝sigmoid(ℓ)；時間特徵缺值的觀測 Λ = 0（只用顏色）。沒有任何需要選擇的超參數。
- 評估（描述性）：S1 LOSO（使用 v5 T，與 H-LR、H+T-LR 比較）、S2、S3（天體等權重版本：ℓ_H 用天體等權重 LR）、E（凍結，H_R 版本）。

## 5. v6d：顏色條件的天體置換檢定（新推論）
- H0：給定顏色，時間特徵的分布與類別無關。特徵：T1*、T2*、T3*、log ν_c（4 個檢定，Holm 校正，α = 0.05）。
- 殘差：以 H_R（標準化）上的 kNN 迴歸（k = 25，等權）預測特徵，**留一天體**擬合（不使用標籤）；r = 特徵 − 預測。
- 統計量 D = BH 天體的平均天體殘差 − NS 天體的平均天體殘差（天體等權重）。
- 虛無分布：在天體層級隨機重排標籤（保持 BH 數），20,000 次（seed 42）；雙尾 p = (1 + #{|D_perm| ≥ |D|}) / (1 + 20,000)。
- 樣本：S1（主要）；E（獨立複製，kNN 以 S1 的全部觀測擬合、套用到 E，只在 E 的天體之間重排）。

## 6. v6e–v6h：可用性與穩健性（描述性）
- **v6e 天體層級 conformal 預測集**：以 LOSO OOF 天體分數為校準（類別條件，Mondrian）；不一致度：BH 為 1 − s、NS 為 s；
  p_y = (1 + #{同類校準天體 α ≥ α_test}) / (1 + n_y)；預測集 = {y : p_y > ε}，ε ∈ {0.1, 0.2}。報告各類覆蓋率、平均集合大小、哪些天體「無法判斷」。
  E 上以 S1 的 LOSO OOF 為校準、凍結模型分數為測試（split conformal）。模型：H-LR、H+T-LR、CCTLR。
- **v6f 觀測數預算曲線**：S3（每源全部觀測）的 OOF，k ∈ {1, 2, 3, 5, 8, 13, 21} 筆隨機觀測／源，500 次（seed 42），報告來源 BA、AUC 的中位數與 2.5–97.5 百分位。模型：H-LR［天體等權重］、H+T-LR［天體等權重］、CCTLR［天體等權重］。
- **v6g proper scoring rule**：天體層級類別平衡 log loss 與 Brier（機率截在 [0.01, 0.99]），與 bootstrap 使用相同重抽；所有比較都報告。
- **v6h 穩健性**：(1) 干擾變數控制：H+N vs H+N+T（N＝log 淨計數率/PCU、開啟 PCU 數、背景比例、觀測年份）；(2) 頻段消融：H+T1、H+T2、H+T3；(3) 以 T* 取代 T 的 H+T*-LR。皆在 S1。

## 7. 實作檢查（不通過就停止並回報）
v6b 第 4 點的合成檢查；E 的每個新天體的標籤證據與位置比對表（`data/v6/source_verification.csv`）；
凍結模型在 S1 的訓練資料上重現 v5 H+T-LR 的係數方向（T1 係數 > 0）只作回報。

## 8. 計算量與下載
新下載：新 BH 與 AMXP、慢速脈衝星合格者 × 15 筆（估計 ≤ 250 筆，Std2 標準產品＋Standard-1，約 100–200 MB，10–20 分鐘）；特徵與分析數分鐘。

## 9. 不做的事
看到結果後改變天體名單、頻段、估計量或模型；在測試天體上調門檻；把 gain epoch、觀測日期、計數率當作 primary 的特徵；event mode 資料；XSPEC 物理參數。

## 10. 報告
`reports/report_v6_zh-TW.md`：做了什麼 → 結果 → 解讀（數據直接支持／可能解釋（未驗證）／需要更多資料的假說）→ 限制 → 與預先設定的差異；
`README.md` 與 `final_report_zh-TW.md` 新增 v6 一節（不改既有數字）；`run_v6.ps1`、`run_v6.sh`。
