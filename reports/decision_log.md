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
