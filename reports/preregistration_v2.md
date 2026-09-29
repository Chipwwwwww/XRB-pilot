# v2 預先設定（擴充樣本 + 完整 deadtime + 來源層級 bootstrap）

寫於 2026-09-29，在 v1 結果之後、**任何 v2 能譜下載完成或 v2 模型訓練之前**。參數在 `scripts/config.py` 的 v2 區塊（`XRB_VERSION=v2` 啟用）。
v1 設定與輸出不變；v2 輸出寫到 `data/v2/`、`results/v2/`、`figures/v2/`、`logs/v2/`。

## 1. 來源（規則化，不挑選）
- BH：BlackCAT Table 4（dynamical BHs：列出 K₂ 與 f(M) 的系統）中，**所有** 有 RXTE MissionLongData 目錄檔者：
  GRO J1655-40、GRS 1915+105、XTE J1550-564、4U 1543-47、GX 339-4、XTE J1650-500、XTE J1118+480、XTE J1859+226、V4641 Sgr。
- NS：Galloway+2008 appendix A（RXTE 觀測到 type-I bursts 的來源）中，**所有** 有 MissionLongData 目錄檔者（24 個）。
  只在 Galloway 其他表格出現的 burster（例如 4U 0614+09）、或沒有 appendix-A 章節的來源（GX 13+1、Ser X-1）不納入。
- 時間窗擴大為整個 gain epoch 5（MJD 51677–55931，直到任務結束）。StdProd 在 PCU0/PCU1 失去 propane 層後即不含它們，所以同一 epoch 內的處理一致。
- 合格指向數 < 10 的來源排除並記錄（結果：XTE J1859+226 = 0、V4641 Sgr = 9 → 排除）。最終 7 BH + 24 NS。
- 每源 15 筆（合格數 10–14 則全取）；抽樣、品質規則、能量格點、A/B 表示、模型、門檻都與 v1 相同。

## 2. Deadtime（v1 的建議下一步）
- 由 Standard-1（`pca/FS46_*.gz`，DATAMODE=Standard1b）計算 spectrum GTI 內的平均率：
  每個 PCU 的 good xenon (XeCntPcu0–4)、整個陣列的 propane (VpCnt)、coincident (RemainingCnt)、VLE (VLECnt)。
- 依 RXTE GOF deadtime 頁的光譜修正 recipe，逐 PCU：DTF_i = 1e-5 × (Xe_i + (Vp+Rem)/N_on) + 6e-5 × VLE/N_on，
  取 spectrum 使用的 PCU 平均；DCOR = 1/(1−DTF) 乘在淨計數率。N_on = Std1 good-xenon 率 > 1 c/s 的 PCU 數。
- 同頁另一段寫 VLE 每事件 150 µs；以 1.5e-4 計算的 DTF 只作敏感度紀錄，不用於特徵。
- 取不到 Standard-1 或時間不重疊 → 該觀測排除，改用同區段下一候選。MAX_DTF = 0.10 規則不變（現在套用在完整 DTF 上）。

## 3. 新增的事先宣告分析
- **來源層級 bootstrap**（v1 與 v2 都做）：在 BH、NS 內各自有放回地抽「天體」，2000 次，seed 42；
  使用固定的 out-of-fold 預測（不重新訓練），報告 2.5–97.5 百分位與 B−A 配對差。
- **硬度基線**（檢驗「模型是否只學到硬度」）：
  H = [F(7–10)/F(5–7), F(16–25)/F(10–16)]（計數空間的兩個顏色；原訂取 log10，訓練前發現 2 筆 16–25 keV 淨計數略為負值而改為線性比值，見 decision_log）；
  HI = H + log10 F(5–25)。與 A、B 用相同 folds、相同模型。
  若 A/B 不顯著優於 H/HI，代表完整能譜在這個設定下沒有提供超過兩個顏色的資訊。

## 4. 狀態標籤
- 搜尋可機器讀取、逐 ObsID、同時涵蓋 BH 與 NS 的狀態分類表：Dunn+2010（MNRAS 403, 61）未收錄於 VizieR，
  其他研究則是單一來源或定義不一致。依原則不自行由外觀指定 hard/soft 標籤；以第 3 節的硬度基線替代檢驗。

## 5. HEASoft
- 使用者已允許安裝軟體。WSL 需系統管理員權限（UAC）與重新開機；已啟動 `wsl --install -d Ubuntu-22.04`，等待使用者核准。
  v2 的 deadtime 修正不依賴 HEASoft（Standard-1 計算與 GOF recipe 相同）；HEASoft 留待需要重新抽取光譜或新背景模型時使用。
