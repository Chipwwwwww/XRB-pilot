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
| 軟體 | 使用者允許安裝軟體 → 安裝 WSL Ubuntu 22.04（使用者核准 UAC；未重開機）與 HEASARC 官方 conda HEASoft（`scripts/install_heasoft_wsl.sh`） | — |
