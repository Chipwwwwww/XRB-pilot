# v5 預先設定：Standard-1 低頻時間變異能否在兩個顏色之外提供 BH／NS 資訊？

撰寫：2026-10-01，**在看過 v1–v4 全部結果之後**、在計算任何 v5 特徵或訓練任何 v5 模型之前。
核准：使用者於 2026-10-01 指示「if v4 is finish, come up with v5 and run it yourself」，因此本設定由我自行核准後直接執行（沒有另外請使用者審閱）；除非遇到重大問題不停下。
v1–v4 的資料、fold、程式行為與輸出都不改。v5 以 `XRB_VERSION=v5` 切換（`config.py` 的 v4 區塊條件放寬為 v4／v5 開頭，v4 行為不變），輸出在 `data/v5/`、`results/v5/`、`figures/v5/`、`logs/v5/`，分支 `v5-analysis`（自 `v4-analysis` 分出）。

## 0. 共同規則（沿用 v4）
- 主要評估：LOSO；天體分數＝該天體 OOF BH 分數平均；門檻固定 0.5。
- 指標：來源 balanced accuracy、來源 AUC（頭條）；觀測 balanced accuracy 另報。
- 不確定性：與 v2／v3／v4 相同的分類別天體 bootstrap（2000 次、seed 42），配對比較，固定 OOF 預測。
- 「有提升」：與基準的配對差 95% 區間**完全大於 0**（每個指標各自判讀）；否則寫「未偵測到」。
- 本版所有模型都用 v2 的固定超參數（LR：`LR_PARAMS`；RF：`RF_PARAMS`），不做超參數、門檻或模型選擇，因此不需要巢狀。
- 每個設定變更記在 `reports/decision_log.md`，並註明是否在看到 v5 結果之後。

## 1. 問題與背景（已查證的部分）
v1–v4 顯示：5–25 keV 的能譜資訊幾乎都在兩個硬度比裡；換演算法、加 HEXTE、加觀測都沒有勝過 H-LR。v5 改問一個**新的資訊軸**：時間變異。
- Standard-1 模式：每 128 s 一列、每列 1024 個 0.125 s 的計數直方圖，五個 PCU 各一欄（`XeCntPcu0`–`XeCntPcu4`），256 個能道合併、沒有能量解析
  （HEASARC ABC Guide, Standard-1 configuration；本機檔案 `TIMEDEL = 128` 已確認）。可用頻率 1/128 Hz 至 Nyquist 4 Hz。
- PCA deadtime 每個 good event 約 10 µs（HEASARC RXTE Cookbook, PCA deadtime）。
- 不同偵測器的 Poisson 雜訊互不相關，因此兩組偵測器光變曲線的 cross spectrum（實部，cospectrum）白雜訊期望值為 0，不需要模型化 Poisson 水準與 deadtime
  （Bachetti et al. 2015, ApJ 800, 109；Bachetti & Huppenkothen 2018, ApJL 853, L21）。
- 時間分箱使 Fourier 振幅乘上 sin(πν δt)/(πν δt)（van der Klis 1989, Fourier Techniques in X-ray Timing, Eq. 2.19），功率乘其平方；本版除以此因子。
- 文獻：NS 在 ~500 Hz 以上仍有顯著功率而 BH 在 10–50 Hz 以上衰減（Sunyaev & Revnivtsev 2000, A&A 358, 617）——這個頻段 Standard-1 **無法**取得。
  BH 暫現源的 rms 隨能態改變（硬態高、軟態低；Muñoz-Darias, Motta & Belloni 2011, MNRAS 410, 679）。
  **低頻（< 4 Hz）是否帶有超過顏色的 BH／NS 資訊，沒有查到明確的文獻結論**；這是探索性問題，「未偵測到」是合理的預期結果之一。

## 2. 樣本（不需要新下載；Standard-1 檔案在 v2／v4b2／v4b1 處理時已下載並記錄 SHA256）
- **S1（主要）**：v2 的 456 筆、31 個天體（7 BH、24 NS），fold 與 v2 相同。
- **S2（次要）**：v4b2 擴充樣本 677 筆、46 個天體（9 BH、37 NS）。
- **S3（次要）**：v4b1 的 7,949 筆、31 個天體（每源全部合格觀測）。
Standard-1 路徑：`data/raw/std1/<ObsID>/FS46_*.gz`，找不到時用 `XRB_EXTERNAL_RAW`（預設 `~/xrb-pilot-data/raw`）下的同名路徑。

## 3. 時間特徵 T 的定義（固定，看到結果後不改）
1. 只用能譜 GTI（能譜檔 `STDGTI`）**完整涵蓋**的 Standard-1 列（128 s、N = 1024、δt = 0.125 s）。
2. 某列中某 PCU 視為開啟：該列 8 個 128-bin 區塊的計數都 > 0。開啟的 PCU 依編號排序，偶數位置為 A 組、奇數位置為 B 組；少於 2 個開啟 → 該列無效。
3. x_k、y_k＝A、B 組每個 0.125 s bin 的計數和；X_j、Y_j 為其 FFT。頻段變異（計數²/bin²）：
   V_band = (2/N²) Σ_{j∈band} Re(X_j Y_j*) / sinc²(π j/N)。
4. 背景：每個 PCU 的背景率 b＝Standard-2 背景譜（b2）**全部能道**的計數 ÷ 曝光 ÷ 能譜 PCU 數（假設各 PCU 相同）。
   組的源平均計數 s_x = mean(x) − n_x·b·δt；s_x 或 s_y ≤ 0 → 該列無效。列的分數變異 f = V_band / (s_x·s_y)。
5. 每個觀測取有效列的**中位數**（對 type-I burst 等少數列的突發較穩健）；有效列 < 3 → 該觀測時間特徵缺值。
6. 三個頻段：T1：j = 2–12（0.016–0.094 Hz）；T2：j = 13–128（0.102–1.00 Hz）；T3：j = 129–511（1.01–3.99 Hz）。
   特徵值為 sign(f)·√|f|（分數 rms；雜訊可使 f 略小於 0）。
7. 缺值：以訓練 fold 的中位數補值，並加一個 0/1「時間特徵缺值」指標（與 v4b3 相同規則）。

## 4. 實作檢查（在任何建模之前；不通過就停止並回報）
a. 合成資料單元測試：兩組 Poisson 光變曲線含共同正弦（分數 rms 0.2，頻率 0.05、0.5、3 Hz）→ 對應頻段的 T 與真值相差 < 10%；純 Poisson（無訊號）→ 多列中位數 |T| < 0.02。
b. 實際資料交叉檢查（S1）：對 ≥ 2 個 PCU 開啟、源計數率 20–500 counts/s/PCU 的觀測，另算傳統自功率譜減去 Poisson 水準（rms 正規化 2/⟨rate⟩，不含 deadtime）的 T2；
   與 cospectrum 版 T2 的 Spearman ≥ 0.90。
c. 合理性（回報，非檢定）：在每個 BH 天體內，T1+T2+T3 的總 rms 與硬色 F(16–25)/F(10–16) 的 Spearman；預期多數為正（硬態 rms 較高）。
   若 7 個 BH 的中位數 < 0，視為實作可能有誤，停止並檢查。

## 5. 模型與比較
- **Primary（S1）**：H+T 的 LR（兩個顏色＋T1–T3＋缺值指標，balanced）vs v2 H-LR OOF。判讀來源 BA 與來源 AUC（各自），觀測 BA 另報。
- 描述性（不作結論）：
  1. S1：T-LR、T-RF（只用時間特徵）；H+T-RF vs v2 H-RF；H+T vs H 在 v4 的顏色重疊區（c1 ≥ 0.70、c2 ≥ 0.20；只含 ≥ 3 筆重疊區觀測的天體）；
     排除 v4 自動規則判定含 burst 的 61 筆後 H+T vs H（同一批保留觀測）。
  2. S2：H+T 的 LR、RF vs 同樣本 H-LR（`results/v4b2/v4b2_oof_predictions.csv` 的 `H_count_space|LogReg`）。
  3. S3：H+T 的 LR、RF（天體等權重）vs v2 H-LR，以及 vs 同樣本 H-LR［天體等權重］（`results/v4b1/`）。
- 比較數：primary 1 組（2 個頭條指標）；描述性約 12 組 × 3 指標，預期偶然有 1 個左右區間 > 0，不作結論。

## 6. 計算量
約 8,600 筆觀測的 Standard-1 讀取與 FFT：16 個平行工作約 15–30 分鐘；建模數分鐘。無新下載。

## 7. 不做的事
Standard-1 以外的時間資料（event mode、> 4 Hz）；XSPEC 物理參數特徵（列為之後的 v5b 候選，本版不做）；看到結果後改變頻段、列規則或補值規則；在測試天體上調門檻。

## 8. 報告
`reports/report_v5_zh-TW.md`：做了什麼 → 結果 → 解讀（數據直接支持／可能解釋（未驗證）／需要更多資料的假說）→ 限制 → 與預先設定的差異；
`README.md` 與 `final_report_zh-TW.md` 新增 v5 一節（不改既有數字）；`run_v5.ps1`、`run_v5.sh`。
