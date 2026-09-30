# XRB-pilot：RXTE/PCA 能譜的 BH／NS 分類小型驗證

**整合報告（先讀這份）：[reports/final_report_zh-TW.md](reports/final_report_zh-TW.md)**——v1 到 v3 的問題、方法、結果與限制；收尾圖 `figures/final/colour_colour_decision_boundary.png`（`scripts/15_colour_colour.py`）。


研究問題：單次 RXTE/PCA 觀測的 5–25 keV 能譜，能否分類「訓練時沒見過的天體」是黑洞（BH）還是中子星（NS）？
這是 **8 個來源（4 BH + 4 NS）、每來源 15 次觀測** 的流程驗證，不是族群層級的結論。

完整報告：[reports/report_zh-TW.md](reports/report_zh-TW.md)　預先固定的設定：[reports/preregistration.md](reports/preregistration.md)

**v2（擴充）**：31 個天體（7 BH + 24 NS）、Standard-1 完整 deadtime、以天體為單位的 bootstrap、硬度基線、XSPEC 交叉檢查。
報告：[reports/report_v2_zh-TW.md](reports/report_v2_zh-TW.md)　設定：[reports/preregistration_v2.md](reports/preregistration_v2.md)
輸出在 `data/v2/`、`results/v2/`、`figures/v2/`、`logs/v2/`；執行 `.\run_all.ps1 -v2`（腳本以環境變數 `XRB_VERSION=v2` 切換）。
XSPEC 交叉檢查需要 WSL Ubuntu-22.04 與 conda 環境 `henv`（安裝：`wsl -d Ubuntu-22.04 -u root -- bash scripts/install_heasoft_wsl.sh`）。

**v3（預先登記：[reports/preregistration_v3.md](reports/preregistration_v3.md)，報告：[reports/report_v3_zh-TW.md](reports/report_v3_zh-TW.md)）**：
v3a 巢狀比較（完整能譜在兩個顏色之外有無增量）＋來源層級 AUC、v3b 3–25 keV、v3c BH candidates——**全部已完成**（分支 `v3-analysis`）。
結論：兩個硬度比已包含可測到的 BH/NS 資訊；3–5 keV 與完整形狀都沒有增量；加入 candidates 只改善門檻失準的設定。
候選名單查證：[reports/v3c_candidate_verification.md](reports/v3c_candidate_verification.md)。
執行：`.\run_v3.ps1 -a`、`-b`、`-c`（或 `./run_v3.sh a b c`）；v3a 重新訓練加 `--retrain`。共用模組 `scripts/v3lib.py`。
輸出在 `results/v3/`、`figures/v3/`、`data/v3/`；v3c 選樣／處理輸出在 `data/v3c/`、`results/v3c/`、`figures/v3c/`，log 在 `logs/v3/`、`logs/v3c/`。
v3c 原始 FITS 在 `data/raw/`（不進 git），以 `XRB_VERSION=v3c` 執行 `04_fetch_process.py` 重新下載（`logs/downloads.jsonl` 有 SHA256）。

**v4（預先登記：[reports/preregistration_v4.md](reports/preregistration_v4.md)，報告：[reports/report_v4_zh-TW.md](reports/report_v4_zh-TW.md)；分支 `v4-analysis`）**：
問「換演算法、加資料、加能段能否勝過 v2 的 H-LR（兩個顏色＋Logistic Regression）」。**預先設定寫於看過 v1–v3 結果之後。**
v4a 換演算法（8 種 × 4 表示、巢狀 LOSO 自動選擇）、burst 汙染檢查、v4b3 HEXTE 25–60 keV、v4b2 更早 gain epoch（名單以位置重新查證）、v4b1 每源全部合格觀測。
結論：**沒有任何主要比較勝過 H-LR**（v4a 巢狀自動選擇 −0.06、v4b3 HEXTE ±0、v4b1 全部 7,949 筆觀測 ±0.000）；v4b2 擴充到 46 個天體後 RF 只在來源 balanced accuracy（門檻）上較好，AUC 無差異。
執行：`.\run_v4.ps1 -test -a -burst -b3 -b2 -b1`（或 `./run_v4.sh test a burst b3 b2 b1`）；共用模組 `scripts/v4lib.py`，腳本 `scripts/16_*`–`25_*`。
輸出在 `results/v4*/`、`figures/v4*/`、`data/v4*/`，log 在 `logs/v4*/`。v4b1 的原始檔（約 2 GB）下載到 `XRB_EXTERNAL_RAW`（預設 `~/xrb-pilot-data/raw`），不在 repo 內。
**v5（預先登記：[reports/preregistration_v5.md](reports/preregistration_v5.md)，報告：[reports/report_v5_zh-TW.md](reports/report_v5_zh-TW.md)；分支 `v5-analysis`）**：
問 Standard-1（0.125 s）的低頻時間變異（0.016–4 Hz，兩組 PCU 的 cospectrum）能否在兩個顏色之外提供資訊。**預先設定寫於看過 v1–v4 之後，依使用者指示自行核准。**
結果：H+T-LR 在 v2 樣本上點估計明顯較好（來源 BA 0.908 vs 0.795、AUC 0.988 vs 0.923），但依嚴格規則 primary **未偵測到**（AUC 差區間下限 0.000）；
描述性比較方向一致（45 個配對差中 15 個區間 > 0），改善集中在顏色重疊的硬態區。屬探索性結果，需要在新天體上確認。
執行：`.\run_v5.ps1`（或 `./run_v5.sh`）；模組 `scripts/v5lib.py`，腳本 `26_*`、`27_*`；輸出 `data/v5/`、`results/v5/`、`figures/v5/`。
**v6（預先登記：[reports/preregistration_v6.md](reports/preregistration_v6.md)，報告：[reports/report_v6_zh-TW.md](reports/report_v6_zh-TW.md)；分支 `v6-analysis`）**：
凍結模型在 23 個訓練從未用過的確認天體（Cyg X-1、LMC X-3、6 個 AMXP 與 v4b2 的 15 個天體；4 BH、19 NS）上驗證 v5 的時間訊號，並測試新方法：
全配對 cospectrum 估計量、νPν 質心頻率、顏色條件時間概似比分類器（CCTLR）、天體層級置換檢定、conformal 預測集、觀測預算曲線、proper scoring rule。
結果：外部天體上來源 BA 0.868 → 0.974，但 AUC 兩者皆 1.000，primary 依嚴格規則**未偵測到**；Brier、log loss、觀測 BA 一致改善；
CCTLR 沒有勝過簡單的 H+T-LR；「同顏色下 BH 低頻變異較強」在 v2 天體上顯著、在外部天體上未複製。
執行：`.\run_v6.ps1`（或 `./run_v6.sh`）；模組 `scripts/v6lib.py`，腳本 `28_*`–`30_*`；輸出 `data/v6/`、`results/v6/`、`figures/v6/`。

## 環境
- Python venv：`C:\Users\User\venvs\xrb-pilot`（Python 3.12.10；放在 OneDrive 之外）
- 版本鎖定：`requirements-lock.txt`；摘要：`logs/environment.txt`
- 重建：
  ```powershell
  C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe -m venv C:\Users\User\venvs\xrb-pilot
  C:\Users\User\venvs\xrb-pilot\Scripts\python.exe -m pip install -r requirements-lock.txt
  ```
- macOS／Linux：
  ```bash
  uv venv --python 3.12 ~/venvs/xrb-pilot
  uv pip install --python ~/venvs/xrb-pilot/bin/python -r requirements-lock.txt
  ./run_all.sh          # v1；./run_all.sh --v2 為 v2（XSPEC 交叉檢查需 WSL，Mac 上預設跳過）
  ```
- 不需要 HEASoft／XSPEC（使用 HEASARC 已處理好的 Standard Products；限制見報告）。僅用 CPU。

## 依序執行
```powershell
.\run_all.ps1
```
或逐步（在 `scripts\` 目錄下，用 venv 的 python.exe）：

| 步驟 | 程式 | 輸出 |
|---|---|---|
| 1 | `01_inspect_archive.py`, `02_catalogs.py`（先前完成） | archive 檢查、`data/catalog_observations.csv` |
| 3a | `03_select_observations.py` | `data/sources.csv`, `data/observation_candidates.csv`, `results/attrition_catalog.csv` |
| 3b | `04_fetch_process.py` | 下載至 `data/raw/spectra/<ObsID>/`；`data/observations.csv`；`data/processed/features.npz`；`data/processed/feature_definitions.csv` |
| 2 | `05_two_source_check.py` | `figures/step2_two_sources.png`, `reports/step2_fits_check.md` |
| 3c | `06_dataset_checks.py` | `results/data_checks.md`, `figures/step3_*.png` |
| 4 | `07_train_eval.py` | `results/folds_loso.csv`, `results/fold_checks.csv`, `results/oof_predictions_loso.csv`, `results/metrics_*.csv`, `results/per_source_results.csv`, `figures/step4_loso_scores.png` |
| 5 | `08_error_analysis.py` | `results/error_analysis.md`, `figures/step5_*.png` |

共用模組：`common.py`（下載＋SHA256 紀錄、進度檔）、`config.py`（全部固定參數）、`spectra.py`（FITS 讀取、背景扣除、重分箱）、`plotstyle.py`。

## 資料對應與紀錄
- 每個下載檔的 URL、本機路徑、大小、SHA256：`logs/downloads.jsonl`
- 每筆候選觀測（含被排除者與原因）、URL、本機路徑、品質旗標：`data/observations.csv`
- `features.npz`：`rate`/`err`（count s⁻¹ keV⁻¹ PCU⁻¹）、`srate`/`brate`（總計數／背景）、`edges`（keV）、`obs_id`、`source_id`（g）、`y`（1=BH）、`F`
- 進度：`reports/progress.json`、`logs/progress.jsonl`
- `data/raw/`、`data/cache/` 與 venv 不納入 Git（見 `.gitignore`）。
