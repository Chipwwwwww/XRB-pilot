# v8 預先設定：硬態內的時間資訊（低頻與高頻）、更多硬態黑洞、MAXI 的 N_H 控制

撰寫：2026-10-05 約 21:30，**在看過 v1–v7 全部結果之後**，在下載任何 v8 資料、計算任何 v8 特徵或訓練任何 v8 模型之前。
起因：v7 報告「下一步」列了三項，使用者回覆「直接進行下一步」。依先前授權（v5／v6／v7 相同），本設定由我撰寫並自行核准，**不另外停下等待審閱**。
版本：repo 已有 v1–v7，本輪為 **v8**。子分析：
- v8a：S1 硬態類內的低頻時間特徵；
- v8b：外部天體的硬態類，以及新增的動力學確認黑洞；
- v8c：高頻（event mode，4–1024 Hz）時間特徵；
- v8d：MAXI 的 N_H 控制。

輸出放在 `data/v8*/`、`results/v8*/`、`figures/v8*/`、`logs/v8*/`。分支 `v8-analysis`（自 `v7-analysis` `68ca4a7`；v7 尚未合併到 master）。
`config.py`：v4／v5／v6／v7 區塊的條件擴充為也對 v8 生效；新增的 v8 區塊放在最後。v1–v7 的設定值不變（提交前逐一比對）。

## 0. 動機（v7 的結果）
- v7a 用 RM06 門檻把觀測分成軟態類與硬態類。H-LR 的觀測層級 AUC：軟態類 0.954、硬態類 0.646，差 +0.31 [+0.10, +0.51]。兩個顏色在硬態幾乎分不開。
- v5／v6 的 Standard-1 時間特徵（0.016–4 Hz）在 v2 天體上的改善**集中在顏色重疊的硬態區**（v5：重疊區來源 AUC 0.73 → 0.92）。因此 v8a 預期為正，這是**事先已知的方向**，不是盲測。
- 經典文獻（Sunyaev & Revnivtsev 2000）指出：低／硬態的 NS 在約 500 Hz 以上有顯著寬頻雜訊，BH 在 10–50 Hz 以上明顯衰減。Standard-1 只到 4 Hz，取不到這個資訊。v8c 首次在本專案的嚴格流程（LOSO、天體 bootstrap、動力學確認標籤）下檢驗它。
- v7c2 在 MAXI 上，含 2–4 keV 的顏色只在非線性模型有增益（RF +0.41、KNN +0.37、SVM +0.30，區間皆 > 0），可能只是星際吸收 N_H 的差異。v8d 檢驗這一點。

## 1. 共同規則（同 v7）
1. 不修改任何既有版本的資料、fold、程式行為或輸出。
2. 主評估 LOSO。來源層級分數＝該源 OOF BH 分數平均，門檻固定 0.5。
3. 不確定性：在 BH、NS 內各自有放回抽天體 2000 次。抽樣程序與 v7a 相同：`v7lib.boot_draws`（天體名稱排序、`default_rng(42)`）。配對比較用同一組抽樣。
   **「有差異」＝95% 區間不含 0；否則一律寫「未偵測到」。**
4. 超參數、門檻、模型選擇只在訓練天體內做。LR／RF 沿用 v2 固定設定。
5. 事實查證見 §2。查不到就記錄並停下。
6. 所有變更記入 `reports/decision_log.md`，註明是否在看過 v8 結果之後。
7. 報告用繁體中文：做了什麼 → 結果 → 解讀（數據直接支持／可能解釋（未驗證）／需要更多資料的假說）→ 限制 → 與預先設定的差異。報告中明寫本設定寫於看過 v1–v7 之後。
8. 每個子分析只宣告**一個 primary**（標 ★），其餘為描述性。
9. 能態分層（「硬態類」等）一律用 v7a 已凍結的規則與門檻（0.1–4 Hz 全配對 cospectrum rms > 0.10），不重新調整。S1 直接用 `results/v7a/states.csv`。
10. **分層內的觀測層級指標**（v8a–v8c 的 ★）沿用 v7a 的計算方式：
    - 每次重抽在「整個樣本的天體」中抽（S1＝31 源，外部集＝全部外部天體）；
    - 再取被抽中天體在該層的觀測，算觀測層級 AUC；
    - 某次重抽若該層缺一類，記為 NaN，百分位數忽略 NaN（報告有效次數）。

    來源層級指標另用 `v4lib.paired_bootstrap`，對限制在該層的 OOF 計算（描述性）。

## 2. 查證結果（2026-10-05，撰寫本文件時）

| 項目 | 查證內容 | 來源 |
|---|---|---|
| SR2000 | 9 NS、9 BH，皆在低／硬態。NS 在 500–1000 Hz 有顯著寬頻雜訊，BH 在 10–50 Hz 以上急降。提議：在 ~500 Hz 以上有顯著雜訊的暫現源應視為 NS。使用約 244 µs（2⁻¹² s）光變、Standard-1 補低頻；只用 5 個 PCU 全開的資料，忽略 PCA 道 0–7；Poisson 水準以 deadtime 修正公式扣除（Vikhlinin+1994、Zhang+1995）。他們的樣本與本專案重疊：NS 有 4U 1728-34、4U 1608-52、SAX J1808.4-3658、4U 1724-307、GS 1826-238、4U 1705-44、SLX 1735-269、KS 1731-260；BH 有 GX 339-4、GRS 1915+105、GRO J1655-40、Cyg X-1、GS 1354-64。**因此 v8c 不是與 SR2000 獨立的天體樣本**；觀測不同（本專案主要是 2000–2011 的 gain epoch 5）。 | arXiv:astro-ph/0003308（A&A 358, 617） |
| RXTE 事件檔 | 每個 ObsID 的 `pca/` 目錄有 2012 年歸檔處理的 `SE*_*.evt.gz`，已解碼：欄位 TIME、PCUID、ANODEID、PHA。實際下載 50407-01-07-01 確認：DATAMODE `E_125us_64M_0_1s`、TDDES2 `D[0~4] & E[X1L^X1R^X2L^X2R^X3L^X3R] & C[0~249]`、TIMEDEL 2⁻¹³ s、另有 GTI 延伸。以 HTTP range 讀檔頭盤點 S1 的 180 筆硬態類觀測：148 筆有全能道、全層、≤ 122 µs、含 PCUID 的事件檔（約 0.98 GB）；GRS 1915+105 的 6 筆硬態類觀測都沒有（亮源，只有 binned mode）；另有 16 筆完全沒有 SE 檔。 | HEASARC 檔案實測（`hdrpeek`／盤點表在 scratchpad，正式盤點由 `43_v8c_events.py` 重做並輸出） |
| 全配對 cospectrum | 不同 PCU 的 Poisson 與 deadtime 雜訊互不相關 → 白雜訊期望值 0。v6／v7 已用於 Standard-1；v8c 以 2⁻¹² s 分箱延伸到 2048 Hz，並用 1536–2048 Hz 當空白對照。 | Bachetti et al. 2015 (ApJ 800, 109)；Bachetti & Huppenkothen 2018 |
| 新的動力學確認 BH | 以 HEASARC TAP（`xtemaster`，0.1°）查 Marcel+2026 Table 1 中**尚未用過**的 BH。有 RXTE 指向的：SS 433（239 筆執行，曝光 ≥ 1000 s 的 108 筆，其中 epoch 5 67 筆）、GS 1354-64（12 筆執行、≥ 1000 s 的 8 筆，全在 1997–98 的 gain epoch 3；不在 MissionLongData）、GRO J0422+32（4 筆，寧靜態）、GS 2023+338（2 筆 ≥ 1000 s）。其餘（M33 X-7、Swift J1727.8-1613、MAXI J1820+070、V616 Mon、MAXI J1305-704、GRS 1009-45 等）沒有 RXTE 指向，或只有曝光 < 1000 s。**RXTE 時代可新增的動力學確認 BH 幾乎已用完。** | HEASARC TAP `https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync`；arXiv:2606.19952 Table 1 |
| HI4PI N_H | HEASoft（WSL，conda `henv`）的 `nh` 工具，預設地圖 `refdata/h1_nh_HI4PI.fits`（HI4PI Collaboration 2016, A&A 594, A116）；參數 disio = 0.1° 時輸出加權平均 `avwnh`。 | `plist nh` 實測 |
| 吸收截面 | XSPEC `tbabs`（Wilms, Allen & McCray 2000）＋`abund wilm`、`xsect vern`，在 WSL 的 HEASoft 中計算。 | XSPEC 手冊 |

## 3. v8a：S1 硬態類內的低頻時間特徵（不重新訓練）
- 資料：
  - v2 的 456 筆、31 源（S1）；
  - 能態取自 `results/v7a/states.csv`（硬態類 180 筆、24 源：7 BH、17 NS）；
  - 預測為既有 OOF：v2 H-LR、v5 H+T-LR（`results/v5/v5_oof_predictions.csv`，S1、`H+T|LogReg`）、v6 的 H+T*-LR 與 H+N+T／H+N（`results/v6/v6_oof_predictions.csv`）。
- ★ **primary**：硬態類觀測層級 AUC，**v5 H+T-LR − v2 H-LR**。
- 描述性：
  1. H+T-RF − H-RF；
  2. H+T*-LR（v6 全配對）− H-LR；
  3. H+N+T-LR − H+N-LR（控制亮度、PCU 數、背景比例、年份）；
  4. 頻段消融：H+T1、H+T2、H+T3 − H-LR；
  5. 差中差：(H+T-LR 的軟態類 − 硬態類 AUC) − (H-LR 的軟態類 − 硬態類 AUC)，回答「時間特徵是否縮小能態差距」；
  6. 硬態類內的來源層級 BA／AUC（限制在硬態類 OOF 的 `paired_bootstrap`）；
  7. 排除爆發後的 v5 OOF（`S1 burst-excluded`：`H+T|LogReg` vs `H|LogReg`）在硬態類內的比較；
  8. 只用硬態類觀測重新做 LOSO（H-LR vs H+T-LR；T 缺值以訓練 fold 中位數補值並加指標，同 v5）。
- 解讀注意：能態指標（0.1–4 Hz rms）與 T2／T3 頻段重疊。在硬態類內，T 的分布已被截斷，但仍可能帶有 rms 大小的資訊；這是條件化的評估，不是循環論證。報告會說明。

## 4. v8b：外部天體的硬態類，以及新增的動力學確認 BH
- 新天體選樣（**v8 新規則，寫於下載前**）：
  - 範圍：Marcel+2026 Table 1 中尚未用於任何 RXTE 樣本（v2、v4b1、v4b2、v6、v7b2）的 BH。
  - 指向：位置取自 SIMBAD（Sesame，已在 `data/v7c/sesame_positions.csv`），距離 ≤ 0.1°。
  - 曝光：目錄曝光 ≥ 1000 s；目錄曝光缺值者保留為候選，下載後以能譜曝光規則判定。
  - 計數率：有 MissionLongData 的天體用 STD1RATE ≥ 5；沒有的，只靠下載後的 v2 品質規則。
  - 不限 gain epoch（同 v4b2／v6）。
  - 合格 ≥ 3 筆即納入，不要求 ≥ 10，因為目的是盡量納入新的 BH；這是對 v2 規則的明確放寬。
  - 抽樣：最多 15 筆，用 03 的時間分層演算法（`default_rng(SEED + 位置)`）。
  - 後續處理用 `21_v4b2_fetch_process.py`（XRB_VERSION=v8b，程式不改）。品質規則與 deadtime 同 v2。
  - 依 §2 的查證，預期為 **GS 1354-64** 與 **SS 433**。
- 外部集 X：
  - v6 的外部集 E（23 源：v4b2 的 15 源＋v6 的 8 源；不含 4 個慢速脈衝星壓力測試源）；
  - v7b2 的 LMC X-1（15 筆）；
  - v8b 新天體。
- 新觀測的處理：
  - 時間特徵：v5 估計量（`v5lib.obs_timing`），補值用 S1 訓練中位數（同 v6）。
  - 能態：v7a 規則（`v7lib.state_rms`）。爆發區間只用 MINBAR（v7b1 視野規則）；v4 的 Standard-1 目視只涵蓋 v2 樣本，這點列為限制。
- 模型：v6 凍結模型 H_R-LR、H_R+T-LR，在 S1 上重新擬合（決定性）。實作檢查：E 上的分數必須與 `results/v6/v6a_external_scores.csv` 一致，最大差 < 1e-9。
- ★ **primary**：X 的硬態類觀測層級 AUC，**凍結 H_R+T-LR − 凍結 H_R-LR**。
  - 可檢定條件：X 的硬態類中 BH 與 NS 天體各 ≥ 3；否則只描述。
- 描述性：
  - X 全部能態、軟態類的同一比較；
  - 新 BH 各觀測的能態與分數；
  - 硬態類內的來源層級指標；
  - SS 433 另外列出（噴流主導的特殊系統，見限制）。

## 5. v8c：高頻時間特徵（event mode）
- 樣本 S1-HF：S1 硬態類中有合格事件檔、且通過品質檢查的觀測。外部 X 的硬態類觀測用同一規則（X-HF）。
- 事件檔規則（依檔頭判定，寫於下載前）：
  - DATAMODE 符合 `^E_\d+us_\d+M_0_\d+s$`（event mode、道數自 0 起、不分層的全能段）；
  - TDDES2 含六個 anode chain（`X1L^X1R^X2L^X2R^X3L^X3R`）；
  - TIMEDEL ≤ 2⁻¹² s；
  - 有 PCUID 欄位。
  - 同一觀測若有多個合格模式，取檔案總大小最大的模式，並用該模式的全部檔案。
- 估計量（`v8lib.hf_features`）：
  - 事件以 2⁻¹² s 分箱（Nyquist 2048 Hz），16 s 一段（N = 65536）。
  - 段必須完全落在「能譜 STDGTI ∩ 事件檔 GTI」內，且不與爆發區間重疊。爆發區間：S1 同 v7a（MINBAR 視野規則＋v4 候選），X 只用 MINBAR。
  - PCU 開啟＝該段 16 個 1 s 區間都有事件。≥ 2 個 PCU 開啟的段才用。
  - 每段：全配對 cospectrum (|ΣX|² − Σ|X_i|²)/2，逐頻除以 sinc²(πj/N)（van der Klis 1989 Eq. 2.19）。分數變異＝2/N² · Σ_j cross_j ／ Σ_{i<k} s_i s_k，其中 s＝每 PCU 每箱的源計數（總計數減背景；背景＝StdProd 背景譜全部能道的每 PCU 計數率，同 v5）。
  - 頻段：
    - HF1＝4–64 Hz（j = 64–1023）；
    - HF2＝64–512 Hz（j = 1024–8191）；
    - HF3＝512–1024 Hz（j = 8192–16383，對應 SR2000 的 ~500–1000 Hz）；
    - 對照頻段 LC＝1–4 Hz（j = 16–63）；
    - 空白頻段＝1536–2048 Hz（j = 24576–32767）。
  - 每觀測取有效段的**平均**（爆發已明確移除，平均比中位數有效率高）。特徵值＝sign(f)·√|f|（同 v5）。
  - 品質規則：有效段 ≥ 10（160 s）；空白頻段的 z＝平均／(標準差/√n)，|z| ≤ 5。不合格者 HF 缺值，觀測不進 S1-HF。
  - 不做 deadtime 振幅修正（列為限制；硬態類源計數率低，影響小）。
- 停止條件：S1 硬態類中有合格事件檔者，若 > 20% 因空白頻段 |z| > 5 被排除，則 v8c 停止並回報，不調整規則。
- 模型（在 S1-HF 內重新做 LOSO；LR／RF v2 固定設定）：
  - H-LR、H+HF-LR、H+T-LR、H+T+HF-LR、HF-LR，以及各自的 RF 版本；
  - T 缺值以訓練 fold 中位數補值並加指標（同 v5）。
- ★ **primary**：S1-HF 觀測層級 AUC，**H+HF-LR − H-LR**（兩者都在 S1-HF 內重新訓練）。
- 描述性：
  1. H+T+HF-LR − H+T-LR（高頻相對於低頻的增量）；
  2. RF 版本；
  3. HF-LR 單獨；
  4. 排除三個 AMXP 天體（SAX J1808.4-3658 401 Hz、XTE J1814-338 314 Hz、HETE J1900.1-2455 377 Hz；脈衝會落在 HF2）後重新做 LOSO；
  5. 來源層級指標；
  6. 每個天體 HF3 的平均與顯著性，以及 SR2000 式判準的描述：天體所有觀測合併後 HF3 顯著 > 0（> 3σ）→ 判為 NS；
  7. 外部凍結測試：在 S1-HF 上擬合 H_R-LR 與 H_R+HF-LR（H_R 才能跨 gain epoch），套用到 X-HF。
- 停止條件（實作檢查 IC4）：S1-HF 上 LC 頻段（1–4 Hz）與 v6 Standard-1 的 T3*（1–4 Hz）的 Spearman < 0.90 → v8c 停止並回報。

## 6. v8d：MAXI 的 N_H 控制
- 樣本：v7c2 凍結的名單與資料（`data/v7c/c2_sources.csv`、`maxi_points.csv`）。主任務：BH 13 vs NPNS 48。
- N_H：HEASoft `nh`，HI4PI 地圖，在 v7c2 使用的天體位置（Sesame）取 `avwnh`（0.1° 加權平均）。
- 吸收修正：
  - XSPEC `tbabs`（wilm／vern）× powerlaw（Γ = 2）。以 N_H 網格（0 與 10¹⁹–10²³·⁵ cm⁻²，對數 200 點）計算 2–4、4–10、10–20 keV 光子通量的穿透率 t_band(N_H)，在 log N_H 上內插。
  - 修正：L′ = L/t_L、M′ = M/t_M、H′ = H/t_H。重算 SC′、HC′、C4′、RelInt′，得到特徵集 C2D_NH、C1D_NH、CCI_NH。
- 其他與 v7c2 完全相同：每個訓練源最多 200 點、seed 42、LOSO、來源分數＝點分數平均。
- ★ **primary**：主任務來源 AUC，**RF[C2D_NH] − RF[C1D_NH]**。
  - 選 RF 是因為 v7c2 中它的 (ii) 差值最大（+0.410），並且沒有超參數選擇。**這是看過 v7 結果後的選擇**，報告中會寫明。
- 描述性：
  1. 差中差 (RF[C2D_NH] − RF[C1D_NH]) − (RF[C2D] − RF[C1D])；
  2. LR、KNN（內層 LOSO 選 k，網格同 v7）的同一比較；
  3. log N_H 單獨作分數的來源 AUC，看 N_H 本身是否分得開兩類；
  4. RF[C2D + log N_H] − RF[C1D + log N_H]；
  5. 兩類的 N_H 分布圖。
  - SVM 不做：計算量大（v7 約數小時），且 v7 中只是描述性。
- 實作檢查（IC6）：v8d 重跑未修正的 RF[C2D]、RF[C1D]，OOF 必須與 v7c2 完全相同。

## 7. 實作檢查（建模前；不通過則該子分析停止並回報，程式錯誤修正後記錄）
- IC1：v8a 以同一程序重算 v2 H-LR 硬態類 AUC，必須等於 v7a 的 0.646 [0.445, 0.841]。
- IC2：凍結 v6 模型在 E 上重現 v6a 分數（最大差 < 1e-9）。
- IC3：HF 估計量合成測試（`test_v8lib.py`）：
  - 20、200、700 Hz 正弦（rms 0.10）在對應頻段恢復到 0.09–0.11；
  - 純 Poisson 時 |HF| 的平方 < 0.01²；
  - 50% 背景時恢復；
  - 每 PCU 非癱瘓型 deadtime 10 µs、2000 c/s/PCU 時，空白頻段 |z| < 3；
  - 分箱：事件時間解析 2⁻¹³ s 時，2⁻¹² s 分箱與 sinc 修正後在 HF3 無偏（±10%）。
- IC4：見 §5。
- IC5：tbabs 穿透率在 N_H → 0 時 → 1，並隨 N_H 單調遞減；2–4 keV 的穿透率 < 4–10 keV < 10–20 keV。
- IC6：見 §6。

## 8. 輸出
- 程式：`scripts/41_v8b_select.py`、`42_v8_states_timing.py`、`43_v8c_events.py`、`44_v8_analysis.py`、`45_v8d_nh.py`、`46_v8_summary_figure.py`；共用函式 `v8lib.py`、測試 `test_v8lib.py`；重跑腳本 `run_v8.ps1`／`run_v8.sh`。
- 報告：`reports/report_v8_zh-TW.md`；README 與 `final_report_zh-TW.md` 新增 v8 一節（不改既有數字）；總結圖 `figures/v8/v8_summary.png`。
- 下載記錄：`logs/downloads.jsonl`（URL、bytes、SHA256）。事件檔放在 `data/raw/events/`（不進 git）。

## 9. 已知限制（事先寫明）
1. 本設定寫於看過 v1–v7 之後；v8a 的方向可由 v5 的顏色重疊區結果預期。
2. 硬態類只有 7 個 BH 天體（S1-HF 預期 6 個，因為 GRS 1915+105 沒有事件檔）；檢定力低。
3. SR2000 的天體與本專案重疊（§2），v8c 不是獨立的天體樣本。
4. AMXP 的相干脈衝（300–400 Hz）會落在 HF2：屬於真實的 NS 證據，但不是 SR2000 所說的寬頻雜訊；另報排除 AMXP 的結果。
5. HI4PI 是銀河系 HI 柱密度：不含分子氫、不含源本身的吸收，對遠處的銀道面源則是整條視線的上限。修正並不完整。
6. SS 433 的 X 光主要來自噴流，不是典型的吸積能態；把它當作「動力學確認 BH」是依 Marcel+2026 的規則，不代表它適合用來評估硬態分類。
7. 外部集的爆發只用 MINBAR 排除；GS 1354-64（1997）在 gain epoch 3，只能用 H_R 模型。
