# XRB-pilot：RXTE/PCA 能譜的 BH／NS 分類小型驗證

研究問題：單次 RXTE/PCA 觀測的 5–25 keV 能譜，能否分類「訓練時沒見過的天體」是黑洞（BH）還是中子星（NS）？
這是 **8 個來源（4 BH + 4 NS）、每來源 15 次觀測** 的流程驗證，不是族群層級的結論。

完整報告：[reports/report_zh-TW.md](reports/report_zh-TW.md)　預先固定的設定：[reports/preregistration.md](reports/preregistration.md)

## 環境
- Python venv：`C:\Users\User\venvs\xrb-pilot`（Python 3.12.10；放在 OneDrive 之外）
- 版本鎖定：`requirements-lock.txt`；摘要：`logs/environment.txt`
- 重建：
  ```powershell
  C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe -m venv C:\Users\User\venvs\xrb-pilot
  C:\Users\User\venvs\xrb-pilot\Scripts\python.exe -m pip install -r requirements-lock.txt
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
