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
