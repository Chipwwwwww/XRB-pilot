# Decision log

| 時間 (2026-09-29) | 決定 / 變更 | 是否在看到分類結果之後 |
|---|---|---|
| 沿用先前工作 | 沿用既有 venv、`01/02` 程式、catalog 與兩組光譜；`common.download` 改成遇到 HTTP 404 不重試 | 否 |
| 選樣前 | 來源、時間窗、篩選條件、抽樣方式寫入 `scripts/config.py` | 否 |
| 選樣時 | 修正 bug：catalog 有 NaN RA/DEC，導致中位座標為 NaN、全部指向檢查失敗 → 改用 `nanmedian`；NaN 座標列不通過指向條件 | 否（尚無任何能譜） |
| 下載前 | Deadtime 依 GOF recipe 乘在淨計數率上：DCOR×(r_s−r_b) | 否 |
| 下載後、訓練前 | 撰寫 `reports/preregistration.md`（在選樣程式已執行、下載進行中時寫成，但早於任何模型訓練） | 否 |
| 資料檢查後、訓練前 | Response 檢查圖改以 PCU 組合著色，並在 `data_checks.md` 加入 PCU 組合 × 傾斜表（只是診斷，不影響特徵） | 否 |
| 訓練後 | 沒有更改來源、觀測、特徵、模型或門檻 | — |

## v2（使用者要求「直接執行建議的下一步」之後）

| 時間 (2026-09-29) | 決定 / 變更 | 是否在看到 v2 分類結果之後 |
|---|---|---|
| v2 開始 | 腳本改為讀 `XRB_VERSION`；v1 輸出路徑與內容不變（v2 寫入 `*/v2/`） | 否 |
| v2 設定 | 來源規則、整個 epoch 5、MIN_ELIGIBLE=10、Standard-1 deadtime、bootstrap、硬度基線 → `config.py` v2 區塊與 `preregistration_v2.md` | 否（但在看過 v1 結果之後） |
| 下載後、訓練前 | 硬度基線原訂 log10 顏色；2 筆 BH（95409-01-29-00 GX 339-4、60113-01-34-00 XTE J1650-500）16–25 keV 淨計數略為負 → 改用線性比值 | 否（尚未訓練任何 v2 模型） |
| v2 圖表 | 發現 `08_error_analysis.py` 一個 f-string 路徑未改到，v2 執行時覆寫了 v1 的 `figures/step5_hid_errors_*.png`；已用 git 還原 v1 檔案並修正路徑 | 與結果無關（輸出路徑錯誤） |
| 訓練後 | bootstrap 增加 B−H、A−HI 配對差（原只宣告 B−A）；屬於同一事先宣告問題「是否只學到硬度」的直接檢驗，不影響任何模型或資料 | 是（新增的是比較方式，已註明） |
| XSPEC 檢查 | HEASoft 6.37.1 安裝完成；交叉檢查腳本改為把 XSPEC 指令寫成檔案再由 WSL bash 執行（inline 傳遞時 `$xspec_tclout` 被展開為空）；12 筆與 Python 一致至 1e-9 | 與分類結果無關 |
| 軟體 | 使用者允許安裝軟體 → 安裝 WSL Ubuntu 22.04（使用者核准 UAC；未重開機）與 HEASARC 官方 conda HEASoft（`scripts/install_heasoft_wsl.sh`） | — |

## 第二台電腦（macOS）

| 時間 (2026-09-30) | 決定 / 變更 | 是否在看到分類結果之後 |
|---|---|---|
| Mac 環境 | venv 放 `~/venvs/xrb-pilot`（uv 安裝 Python 3.12.14，`requirements-lock.txt` 全部可安裝、未修改） | 與結果無關 |
| 原始數據 | 不從 Windows 複製；依 `logs/downloads.jsonl` 重新下載 2689 個檔案，SHA256 全部一致 | 與結果無關 |
| 執行腳本 | 新增 `run_all.sh`（對應 `run_all.ps1`）；XSPEC 交叉檢查依賴 WSL，Mac 上預設跳過，只在 Windows 執行（`--xspec` 保留給日後移植） | 與結果無關 |
| Mac 重現檢查 | 在 repo 副本上執行 `./run_all.sh`（v1，約 34 秒）：`features.npz` 與 Windows 差 ≤1e-16；LogReg 完全相同；RandomForest 單筆 BH_score 差 ≤0.006、天體平均差 ≤0.001，所有預測標籤與準確率相同。`observations.csv` 只差路徑分隔符（`\` vs `/`）；`sources.csv` 多 `n_eligible`/`included` 欄位（v2 改版後的程式本來就會寫，repo 裡的 v1 檔是舊版產生）。未提交重跑的輸出 | 與結果無關（重現性檢查） |

## v3（2026-09-30，在雲端沙盒執行 v3a；v3b/v3c 待本機執行）

| 時間 | 決定 / 變更 | 是否在看到 v3 分類結果之後 |
|---|---|---|
| v3 開始 | 寫 `preregistration_v3.md`（v3a 巢狀比較、v3b 3–25 keV、v3c candidates）與 `config.py` v3c 區塊；已看過 v1/v2 結果與 v2 B-vs-H 逐筆一致性（事後描述，已在預先設定中註明） | 否 |
| v3a 執行 | 雲端沙盒（1 CPU，scikit-learn 1.8.0、numpy 2.4.4、pandas 3.0.2）。A/B/H/HI 重現 v2 OOF：LR 差 ≤8e-10、RF ≤2e-16，0 個標籤改變；bootstrap 區間與 v2 檔案完全一致 | 與結果無關（重現檢查） |
| v3a 程式 | bootstrap 改為向量化（純效能；結果與 `09_bootstrap_sources.py` 逐位一致）；OOF 已存在時預設重用（`--retrain` 可重跑）；抑制 sklearn 1.8 `penalty` FutureWarning | 否（純效能／log） |
| v3b/v3c | 無法在雲端執行（HEASARC 對沙盒回應 403、原始 FITS 不在 git）。程式以合成 FITS 做過端到端 smoke test（合成資料，不是結果，未保存） | 否 |
| v3c 名單 | 候選名單由記憶整理，**未逐一查證**；執行前須由使用者對照 BlackCAT 確認並凍結 | 否 |

## v3 本機執行（Windows，2026-09-30，分支 `v3-analysis`）

| 時間 | 決定 / 變更 | 是否在看到 v3b/v3c 分類結果之後 |
|---|---|---|
| 套用 patch | `Downloads\xrb-pilot-v3.patch` 原本不在；使用者在對話中貼上全文，從對話紀錄取出未被改寫格式的版本（另一份貼上版本的 email 標頭被轉成 Markdown 連結），`git am` 無衝突（commit 7b1ccd8；PNG 129984 bytes 與 patch 一致） | 否 |
| 環境 | venv 套件與 `requirements-lock.txt` 一致（numpy 2.4.4、pandas 2.3.3、scipy 1.17.1、scikit-learn 1.8.0、astropy 7.2.0、matplotlib 3.10.9）；沙盒用 pandas 3.0.2 | 與結果無關 |
| v3a 本機重現 | `11_v3a_increment.py --retrain`：12 組 OOF 與沙盒相比 LR 最大差 7.8e-10、RF 2.2e-16，0 個標籤改變；`v3a_bootstrap/metrics/agreement` 完全相同 → `results/v3/v3a_local_vs_sandbox.csv`。提交本機重跑的輸出；沙盒副本已刪除 | 與結果無關（重現檢查） |
| 2026-09-30 03:47 +08:00 v3c 名單凍結 | 對照 BlackCAT 網頁版各天體頁與 Corral-Santana+2016：16 個全部保留、0 刪除（無動力學確認、無 NS 證據）。MAXI J1659-152、Swift J1753.5-0127 屬 BlackCAT「嚴格說非動力學、但質量證據強」類，依規則保留並標註；GRS 1758-258、1E 1740.7-2942、4U 1957+11 為論文 §2 persistent 類。詳見 `reports/v3c_candidate_verification.md`；`config.py` 未修改（SHA256 06503f11…013d）。此時尚未執行 v3b、未下載任何 v3c 資料 | 否（v3b、v3c 皆尚未執行） |
| v3b 執行 | `12_v3b_extended_band.py`：格點 50 bins、2.883–25.008 keV（新增 5 個 <4.91 keV bins）；456/456 筆接受，5–25 keV 部分與 v2 最大相對差 6.9e-16，0 筆 v2_mismatch、0 筆 3–5 keV 非正值 bin。未改任何規則 | 執行本身與結果無關；之後未更改任何設定 |
| v3c 目錄檔 | `13_v3c_resolve_catalogs.py`：13/16 找到。依 HEASARC MissionLongData listing 修正 `catalog_name`：Swift J1753.5-0127 → `SWIFTJ1753.5-01`（唯一修改，允許的檔名修正）。XTE J1748-288、GRS 1739-278 在 listing 中沒有任何對應檔（搜尋 1739/1748/GRS 變體）→ 無 RXTE 目錄，依程式規則跳過並記錄 | 否（v3b 仍在執行、尚未看其結果；v3c 尚未下載） |
| v3c 選樣／處理 | `XRB_VERSION=v3c` 執行 03/04/06：14 源皆 ≥16 筆合格，各取 15 筆，210/210 接受；格點與 v2 相同；XTE J1908+094 hdr_sep ≤1.2e-5°，全部源 ≤0.035°；06 在單一類別下正常完成（未改程式）。1E 1740.7-2942、GRS 1758-258 的 OBJECT 為 `NEAR_...`，但指向差 ≤5e-4°。15 筆有高能端非正值 bin（照 v2 規則保留） | 否 |
| v3c 分析 | `14_v3c_candidates.py` 依預先設定執行；未改任何設定 | 執行後未更改 |
| 報告 | `report_v3_zh-TW.md` §3–§7 改寫為 v3b、v3c 結果、解讀（分三層）、限制與「與預先設定的差異」；README、progress.json 更新。與預先設定的差異僅：Swift J1753.5-0127 檔名修正、2 個候選無 RXTE 目錄 | 是（只寫文件，未改分析） |
| 目前進度 | v3a/v3b/v3c 全部完成並 commit 在分支 `v3-analysis`（未合併 master）。下一步（需另行預先設定）：依能態分組比較、逐源 N_H、更多確認 BH | — |

## 收尾（2026-09-30，雲端沙盒，以 `v3-analysis` 2f11821 為基底）

| 時間 | 決定 / 變更 | 是否在看到結果之後 |
|---|---|---|
| 收尾 | 新增 `scripts/15_colour_colour.py` 與 `figures/final/colour_colour_decision_boundary.png`：兩個顏色的散佈圖，疊上 LR／RF 以全部 31 個確認天體擬合的 0.5 邊界與 14 個候選的中位數。純描述，**不是新的評估**，不影響任何已報告數字 | 是（只做視覺化，未改分析） |
| 收尾 | `report_v3_zh-TW.md` §4.3 表格說明原寫「16–84% 觀測分位數」，與欄位（平均、≥0.5 比例）不符，改為正確描述；數字未改 | 是（文字更正） |
| 收尾 | 新增 `reports/final_report_zh-TW.md`（v1–v3 整合報告）；README 加上連結。洩漏高估量依 `results/v2/secondary_observation_split.csv` 與 v3a LOSO 同表示、同模型逐一相減：+0.04 ~ +0.16 | 是（只寫文件） |
| 收尾 | 停止擴充。後續若要做能態分組、時間特徵或物理空間特徵，需另寫預先設定 | — |

## v4（2026-09-30，分支 `v4-analysis`；預先設定寫於看過 v1–v3 全部結果之後）

| 時間 | 決定 / 變更 | 是否在看到 v4 結果之後 |
|---|---|---|
| 階段 0 | 撰寫 `preregistration_v4.md` 與 `config.py` v4 區塊（只在 `XRB_VERSION` 為 v4／v4b1／v4b2／v4b3 時生效；已確認 v1、v2、v3c 載入值不變）。查證：PCA gain epoch 邊界（HEASARC Energy-Channel Conversion Table）；HEXTE Standard Products 檔案結構與 cluster A／B rocking 狀態（Standard Products 說明、2010 news archive；抽查 3 筆 v2 觀測的 stdprod 目錄）；Galloway+2008 的 burst 搜尋判準（arXiv:astro-ph/0608259 §2）。計算時間以合成資料（非研究資料）量測。本機無 torch → 1D-CNN 預先宣告跳過。顏色重疊區矩形（c1≥0.70、c2≥0.20）是看過 v2 顏色圖後選的，已在預先設定中註明為事後定義 | 否（尚未訓練任何 v4 模型、未下載任何 v4 資料） |
