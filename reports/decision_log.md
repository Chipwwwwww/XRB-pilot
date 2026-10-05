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
| 核准 | 使用者回覆「start and finish full if no big problem for v4」→ 視為核准預先設定，並授權各子階段在無重大問題時直接下載、不再逐段停下 | 否 |
| v4a 實作 | `v4lib.py`＋`test_v4lib.py`：自寫的配對 bootstrap 重現 v3a 區間至 1e-12；V4Model 重現 v2 LR/RF OOF（差 ≤2e-16）。巢狀：每個外層 fold 內層 140 個設定 × 30 次訓練；1e 跨演算法平手規則依序為內層 AUC、內層 BA、演算法順序（`V4_GRID` 順序）、表示法順序、網格順序（預先設定只寫「網格中列在最前者」，此處補齊跨演算法順序）。巢狀門檻以 BH_score = raw − 門檻 + 0.5 存檔，使固定 0.5 規則等價於該 fold 門檻 | 否（執行前決定） |
| v4a 結果 | 1a 重現通過。主要檢定（1e）與 H-LR 差：來源 BA −0.062 [−0.146, +0.021]、來源 AUC −0.173 [−0.399, +0.012] → 未偵測到。76 個描述性組合中 3 個（QDA 系列）來源 BA 區間 > 0，屬多重比較下可預期的數量，不作結論 | 結果 |
| burst 檢查 | 自動規則標出 61 筆（含 12 筆 BH：GRS 1915+105 heartbeat、硬態 BH 閃焰等變異，非 type-I burst）；逐張目視 187 筆有候選的觀測：目視集合 58 筆（全為 NS，含 3 筆「可能」）。自動規則漏掉 8 筆明顯 burst（GTI 截斷、上升 >10 s、半衰減 <3 s）。依預先設定，主要排除集合＝自動規則，目視集合為敏感度分析 | 目視在看到偵測結果後進行（預先設定即如此） |
| v4b3 | HEXTE `DEADAPP = T`（header 查證；OGIP：已做 deadtime 校正），繼續執行。1 筆 NS（92023-03-37-00）cluster B 背景曝光為 0 → 兩個高能色皆為缺值，依缺值規則補值 | 否（依規則處理） |
| v4b2 名單查證 | Galloway+2008 Table 3（48 個）與 BlackCAT 動力學 BH（18 個）以 CDS Sesame（SIMBAD）位置比對全部 291 個 MissionLongData 目錄的中位指向（≤0.1°）。**發現 v2 的來源規則執行有誤**：v2 預先設定寫「appendix A 中所有有目錄檔者（24 個）」，但以位置比對另有 13 個 NS 有目錄檔且合格指向 ≥10（如 MXB 0513-40、2S 0918-549、EXO 1745-248 …）。v2 結果不改；列為 v2 限制。另修正比對程式：原本只以選中目錄的名稱判斷是否已在 v2，使 XB1254-690（=4U 1254-69，v2 已有）被誤列為新天體 → 改為任一匹配目錄在 v2 即算已在（在任何 v4b2 下載前修正） | 在看過 burst 偵測結果之後、v4a 結果之前；與分類結果無關 |
| v4b2 名單 | 新增 15 個天體：BH 2（XTE J1859+226、V4641 Sgr）、NS 13；Rapid Burster（MXB 1730-335）與 IGR J17473-2721 有目錄但指向與 SIMBAD 位置相差 >0.1°，依規則不納入。Ser X-1 在 Galloway Table 3 中（v2 預先設定稱其無 appendix 章節，可能有誤），依 Table 3 納入 | 否 |
| v4b2 下載程式 | `21_v4b2_fetch_process.py` 為 `04_fetch_process.py` 的複本，只多掃描 AO1–AO4（原程式只掃 AO4–AO16，epoch 1–4 的觀測會找不到）；v1–v3 仍用原程式 | 否 |
| v4b2 基準補齊 | 預先設定 §0 規定不同樣本的基準為「同樣本重算的 H-LR」，分析程式原本只與 H_R-LR 比較；補上與同樣本 H-LR（`H_count_space|LogReg`）的配對比較 | **是**（看到 v4b2 結果後補上，依預先設定 §0，屬遺漏修正） |
| v4b1 原始檔位置 | 約 7,500 筆新觀測、~2 GB、~3 萬個檔案若放在 repo 內會同步到 OneDrive；改存到 repo 外 `~/xrb-pilot-data/raw`（`XRB_EXTERNAL_RAW` 可改），已在 `data/raw` 的 v2 檔直接沿用；每個下載仍記錄 URL 與 SHA256 於 `logs/downloads.jsonl`。下載執行緒 4 → 6 | 否（下載前決定） |
| 天體等權重 scale 修正 | 煙霧測試 v4b1 分析時發現 `v4lib.source_equal_weights` 讓每一類權重總和為 1（整個 fit 總和 2），而 class_weight=balanced 的總和為 n；LR 目標函數中權重的總量直接乘在損失上，等於把正則化加強約 n/2 倍（分數被壓在 0.4–0.6），HistGB 的 min_hessian_to_split 也受影響（RF 與權重尺度無關）。修正為每類總和 n/2（與 balanced 同尺度；每源總權重相同的相對比例不變），新增單元測試（每源觀測數相同時與 balanced 完全相同）。只重跑 v4a 的固定模型部分（1a–1c）：1a／1b 逐位相同，1c 12 個組合改變；結論不變（來源 BA 區間 > 0 的仍是相同 3 個 QDA 組合，來源 AUC 區間 > 0 的仍為 0 個）。修正前的 1c 結果在 commit 9120afb。v4b1 主要比較（天體等權重 H-LR）尚未執行，使用修正後的權重 | **是**（看過 v4a 結果後發現；屬實作錯誤修正，預先設定的權重定義不變。v4b1 結果之前） |
| v4b1 描述性補充 | 在 v4b1 分析中另加：(1) v4b1 訓練的 OOF 分數限制在 v2 的 456 筆觀測上、與 v2 H-LR 逐筆同樣本的配對比較；(2) 每源平均分數表與圖 `figures/v4b1/v4b1_source_scores.png`。皆為描述性 | 否（v4b1 結果之前決定） |
| v4b1 結果 | 7,975 個候選中接受 7,949 筆（排除 26：HEASARC 缺 Std2 產品 14、deadtime 過高 7、曝光過短 5）。主要比較天體等權重 H-LR − v2 H-LR：來源 BA 0.000 [0, 0]、來源 AUC 0.000 [−0.048, +0.036]、觀測 BA −0.009 [−0.114, +0.123] → 未偵測到；31 個天體判斷與 v2 完全相同。描述性：16 個組合中 4 個（皆含強度 A／HI）來源 BA +0.134 [+0.021, +0.298]、來源 AUC 區間 > 0 的 0 個，不作結論。v4 全部完成 | 結果 |

## v5（Standard-1 低頻時間變異）

| 時間 | 決定 / 變更 | 是否在看到 v5 結果之後 |
|---|---|---|
| 階段 0 | 使用者指示「if v4 is finish, come up with v5 and run it yourself」→ v4 完成並推送後，自行設計 v5 並自行核准預先設定（沒有另外請使用者審閱）。撰寫 `preregistration_v5.md`：問題＝Standard-1（0.125 s）低頻時間變異在兩個顏色之外是否有 BH／NS 資訊。查證：Standard-1 格式（HEASARC ABC Guide；本機檔 TIMEDEL=128、1024 bins）、PCA deadtime（RXTE Cookbook）、cospectrum 白雜訊期望值為 0（Bachetti+2015 ApJ 800, 109；Bachetti & Huppenkothen 2018）、分箱因子（van der Klis 1989 Eq. 2.19）、文獻背景（Sunyaev & Revnivtsev 2000；Muñoz-Darias+2011）。`config.py` 的 v4 區塊條件放寬為 v4／v5 開頭並新增 v5 區塊；已確認 v1、v2、v3c、v4、v4b1、v4b2 的所有設定值與修改前完全相同。v5 寫於看過 v1–v4 全部結果之後 | 否（尚未計算任何 v5 特徵或模型） |
| v5 結果 | 8,170 筆中 7,228 筆有時間特徵；實作檢查通過（cospectrum vs 自功率 T2 ρ=0.970、n=276；7 個 BH 天體內 rms 與硬色皆正相關，中位數 0.61）。Primary（S1）H+T-LR − v2 H-LR：來源 BA +0.113 [−0.021, +0.277]、來源 AUC +0.065 [0.000, +0.179] → 未偵測到；觀測 BA +0.102 [+0.001, +0.249]。描述性：45 個配對差中 15 個區間 > 0（顏色重疊區 AUC、S2 來源 BA、S3 來源 BA 與 AUC），T 單獨比 H 差。單元測試「PCU 列中關閉」的案例原本寫錯，在計算真實特徵前修正（規則未改） | 結果 |

## v6（確認時間訊號＋新方法）

| 時間 | 決定 / 變更 | 是否在看到 v6 結果之後 |
|---|---|---|
| 階段 0 | 使用者要求「deep think … innovations … make it v6」「new algorithms or methods」「before v6 the deep thinking is important」。依 v1–v5 證據設計 v6：primary＝凍結模型在外部天體（訓練從未用過）上檢驗 v5 的 H+T 主張；新方法：全配對 cospectrum 估計量＋單 PCU 混合估計、νPν 質心頻率、顏色條件時間概似比分類器（CCTLR）、顏色條件的天體置換檢定、天體層級 conformal 預測集、觀測數預算曲線、天體層級 proper scoring rule。外部天體名單查證：Casares & Jonker 2014 §3／Table 2（Cyg X-1、LMC X-1、LMC X-3、M33 X-7）；Patruno & Watts 2021 Table 1（AMXP 與慢速脈衝星）。透明聲明：E 中 v4b2 的 15 個天體曾在 v4b2／v5 以其他模型看過結果，因此另報只含 v6 新天體的敏感度分析。`config.py` 的 v4／v5 區塊條件擴充到 v6 並新增 v6 區塊；已確認 v1–v5 所有設定值與修改前完全相同 | 否（尚未下載任何 v6 資料、未計算任何 v6 特徵或模型） |
| v6 結果 | 外部天體 28 個名稱中納入 12 個（Cyg X-1、LMC X-3、6 個 AMXP、4 個慢速脈衝星壓力集），180 筆全部通過；LMC X-1、Swift J1756.9-2508 因指向偏離 >0.1° 排除，M33 X-7、Swift J1749.4-2807 無目錄，NGC 6440 X-2 無法解析。Primary（外部 23 源、凍結）H_R+T-LR − H_R-LR：來源 AUC 0.000（兩者 1.000）、來源 BA +0.105 [0.000, +0.237] → 未偵測到；觀測 BA +0.080 [+0.003, +0.162]、Brier −0.059 [−0.093, −0.027]、log loss −0.127 [−0.217, −0.044]。E_new：來源 BA 0.917 vs 0.750。置換檢定：S1 四項 Holm 後皆顯著（T1* p=0.0024），外部未複製（p=0.16–0.94）。CCTLR 未勝過 H+T-LR。全配對估計量：變異 −31%～−41%、缺值 942→341。Conformal：外部 NS 覆蓋 0.895 vs 0.632。壓力集 4 個慢速脈衝星皆判為 NS（4U 1626-67 升至 0.40） | 結果 |

## v7（能態條件評估、爆發污染、持續黑洞、MAXI 跨儀器；2026-10-05）

| 時間 | 決定 / 變更 | 是否在看過 v7 結果之後 |
|---|---|---|
| 階段 0 | 使用者貼上 v7 任務說明（A 能態、B1 MINBAR 爆發、B2 持續黑洞、C MAXI）。已有 v1–v6，本輪為 v7。撰寫 `preregistration_v7.md` 與 `config.py` v7 區塊（v4／v5／v6 區塊條件擴充到 v7；v7 區塊在最後並恢復 epoch 5 選樣窗）；已確認 v1–v6 所有設定值不變。查證：MINBAR DR1 官方檔（Monash Bridges，CC BY 4.0，figshare md5）、RM06 Table 2 門檻（r＝0.1–10 Hz rms）、Z 源名單、Marcel+2026（arXiv:2606.19952）Table 1 的 Cyg X-1／LMC X-1／LMC X-3 動力學確認與高／低質量分界、SIMBAD 伴星光譜型、Orosz+2009／2014、de Beurs+2022 全文與 GitHub（含處理後資料與 R 程式）、MAXI 標準產品格式與 on-demand 無程式化介面。發現：LMC X-1 的 RXTE 目錄中位指向距 SIMBAD 位置 0.263°（以 SIMBAD 位置 ≤0.1° 仍有 31 筆合格）；LMC X-1 伴星在 SIMBAD 非超巨星；de Beurs 的「BH」12 個中 7 個是 candidate。以上列為待使用者決定事項。未下載任何 v7 資料、未訓練任何模型 | 否 |
| 核准 | 2026-10-05 07:23 使用者回覆「按照你的直接continue到最後」→ 核准 v7 預先設定，三項待決事項皆採建議：(1) LMC X-1 以 SIMBAD 位置 ≤0.1° 為指向規則（三個持續黑洞一律用同一規則）；(2) B2 敏感度的理由改為「排除 Marcel+2026 Table 1 分界線以上的兩個高質量 X 光雙星」；(3) C1 用 de Beurs 公開處理後檔案、C2 用 MAXI 標準產品能段。並授權各階段（含下載）無重大問題時不再停下 | 否 |
| v7b1 規則修正 | 依字面規則（任何儀器、任何發源天體）比對後發現：9 筆是 WFC／JEM-X 在同一時間觀測到天球另一側（8°–58° 外）爆發源的巧合，並非視野內污染（例如 GRO J1655-40 的觀測配到 4U 1636-536、GX 3+1 的爆發）。預先設定「任何發源天體」的本意是包含 PCA 視野內的鄰近源，因此主要規則改為：MINBAR 爆發與能譜 GTI 重疊，且（與本觀測同 ObsID 或發源天體位置距本源 ≤ 1°，PCA 視野 FWHM 1°）。位置取自 MINBAR 官方 source table（`minbar_sources_v2.7.fits`，md5 核對）。主要規則：58/456 筆受污染（全為 NS）；字面規則 67 筆（含 3 筆 BH 的巧合）保留為敏感度分析 | **是**（看過 MINBAR 比對結果之後、任何 v7 分類結果之前） |
| v7b1 交叉檢查 | MINBAR（視野規則）vs v4 目視：一致 99.1%（兩者皆有 56、只有 MINBAR 2、只有 Standard-1 2）。逐張看圖：只有 MINBAR 的 2 筆（96405-01-05-01 4U 1323-62 位於 GTI 斷點、50045-06-05-00 EXO 0748-676 在掩食後）是 v4 漏判的真爆發；只有 Standard-1 的 2 筆（90044-01-04-00 4U 1746-37、50031-02-03-01 KS 1731-260）是 MINBAR 未收錄的明顯爆發。新增敏感度集合「MINBAR ∪ v4 目視」（60 筆） | **是**（新增的敏感度集合是看過比對結果後決定；主要分析不變） |
| v7b1 比較對象 | 預先設定「與 v2 在共同天體上配對比較」解讀為：排除（或替補）後重新訓練的 OOF 與 v2 原始 456 筆 OOF，以天體配對（回答「v2 報告的數字會不會變」）；另報與 v2 在同一批保留觀測上的比較（描述性） | 否（解讀於任何 v7 分類結果之前） |
| v7b2 執行 | 選樣依核准規則（指向距 SIMBAD 位置 ≤0.1°）：Cyg X-1 1205、LMC X-1 31、LMC X-3 830 筆合格；以 03 的演算法取 15 筆時間分層；`04_fetch_process.py`（XRB_VERSION=v7b2，程式未改）45/45 接受。DTF 中位數 Cyg X-1 2.3%（最大 3.8%）、LMC X-1 1.1%、LMC X-3 1.3%。MINBAR（視野規則）0 筆受污染 | 否 |
| v7b2 事後檢查 | 看到 H-LR 加入持續黑洞後 NS 分數普遍上升（Cyg X-2 0.21→0.40），檢查發現 2 筆 LMC X-3（92095-03-12-11、93113-01-54-00）硬色約 −0.9 至 −1.0（暗源、16–25 keV 淨計數為負，依 v2 規則保留原值），對 LR 有高槓桿。描述性事後分析：去掉這 2 筆後 NS 分數回到接近 v2（Cyg X-2 0.24、GX 3+1 0.11），來源 AUC 差 +0.006。主要分析不改 | **是**（事後、描述性） |
| v7c2 標籤細節 | 下載任何 MAXI 光變之前決定：(1) NPNS＝MINBAR 官方 source table 的爆發源，扣除有脈衝週期者（Liu+2007 LMXB 目錄 Ppulse、Patruno & Watts 2021 Table 1）；(2) 次要的脈衝星組＝Liu+2006 HMXB／Liu+2007 LMXB 目錄中有 Ppulse 者＋Patruno & Watts Table 1（預先設定原本只寫 Patruno & Watts，但那只涵蓋 LMXB，與任務說明「脈衝星（多為 HMXB）」不符，因此補上 de Beurs 引用的 Liu 目錄）；(3) 以位置對到 MAXI J 名稱（≤0.35°，J 名稱的 RA 精度約 0.25°）；同一 MAXI 源被不同類別或不同天體對到者排除 | 否（C2 資料下載前；C1 重現結果尚未出來） |
| v7c1 結果 | de Beurs repo 釘選 commit 488b785；以其 10 個子樣本、三類 LOSO 重現：SVM 36/44（BH 5/12，與論文相同），與其公開的逐源 SVM 中位機率 Spearman 0.9989、最大差 0.011、44 源預測類別 100% 一致；KNN 38/44（BH 7/12；論文 37/44、6/12），皆在預先寫定容許範圍內 → 重現成功，繼續 C2 | 結果 |
| v7c2 名單修正 | 第一次比對後（尚未建任何 C2 模型）發現並修正：(a) Liu+2007 LMXB 目錄的 Ppulse 也收錄 burst oscillation 週期（核燃燒驅動，如 4U 1608-52、4U 1636-536、4U 1728-34），使經典爆發源被誤歸為脈衝星 → LMXB 脈衝星只用 Patruno & Watts 2021 Table 1（吸積驅動），HMXB 仍用 Liu+2006；(b) J 名稱位置精度約 0.25°，0.35° 容許度把 IGR J16358-4726 誤配到 4U 1630-47 → 改以 Sesame 解析 MAXI 源名、≤0.1° 比對（無法解析者才用 J 名稱位置、≤0.3°）；(c) MAXI 源名含「with」者為兩源混合光變，排除；(d) 名稱：A 0620-00 以 V616 Mon 解析，Patruno & Watts 表中 IGR J17480-2466、IGR J16358-4724 改為 SIMBAD 名 IGR J17480-2446、IGR J16358-4726。修正後通過篩選：BH 13、NPNS 48、PSR 39 | **是**（看過第一次比對結果之後、任何 C2 模型之前） |
| v7c2 計算量 | 主任務（BH vs NPNS）的 KNN／SVM 依預先設定做完整內層 LOSO（SVM 每折 60 個內層 fold × 9 組參數）；次要任務（BH vs 脈衝星）只做 LR、RF（預先設定寫 KNN／SVM 也做；為節省約 2 小時計算而縮減，屬描述性分析） | 否（任何 C2 結果之前） |
| v7c2 計算量（SVM） | 主任務 SVM 依預先設定做內層 LOSO 時，16 個工作程序跑滿 30 分鐘仍未完成任何一個外層 fold（實際資料的支持向量多，每次擬合數秒），全部約需 6 小時以上。改為：SVM 的內層選參改用訓練天體上的 grouped 5-fold（仍是巢狀、只在訓練天體內選，同一網格、同一來源 AUC 準則）；KNN 已依預先設定完成內層 LOSO。SVM 為描述性分析（primary 是 LR）。在任何 SVM 結果產生之前決定 | 否（任何 SVM 結果之前；LR／RF／KNN 的結果已看過） |
| v7a 結果 | 能態：軟態類 221、硬態類 180、中間 21、無法判定 34（移除爆發列 143）。健全性檢查通過（XTE J1118+480 15/15 硬態類；Z 源 27/28 軟態類）。★ H-LR 觀測層級 AUC 軟態類 0.954 − 硬態類 0.646 = +0.309 [+0.099, +0.510] → 有差異；H-RF、B-LR、B-RF 與排除爆發後的 OOF 一致。中間層 1 個 BH 天體，只描述。探索性的硬態專屬訓練無可測增益 | 結果 |
| v7c2／v7c3 結果 | 主要任務 BH 13 vs NPNS 48。★ LR (i) CCI − 2 色：來源 AUC −0.029 [−0.066, +0.002]、BA −0.077 [−0.192, +0.010]；★ (ii) 2 色 − ≥4 keV 色：AUC +0.139 [−0.032, +0.306]、BA +0.098 [−0.087, +0.280] → 皆未偵測到。LR 本身 AUC 0.56–0.59；KNN 2 色 0.800。描述性：(ii) 對 RF／KNN／SVM 的 AUC 區間皆 > 0；(i) SVM −0.119 [−0.212, −0.040]。次要任務（BH vs 脈衝星）LR 2 色 AUC 0.815。v7c3：30 個共同天體 Spearman 0.63、判斷一致 73% | 結果 |
| v7 完成 | 報告 `report_v7_zh-TW.md`、README 與 `final_report_zh-TW.md` 新增 v7 一節（既有數字未改）、總結圖 `figures/v7/v7_summary.png`、`run_v7.ps1`／`run_v7.sh` | — |

## v8（硬態內的低頻與高頻時間資訊、新增動力學確認黑洞、MAXI 的 N_H 控制；2026-10-05）

| 時間 | 決定 / 變更 | 是否在看過 v8 結果之後 |
|---|---|---|
| 階段 0（約 21:30） | 使用者回覆「直接進行下一步」，指 v7 報告列的三個下一步。依 v5–v7 的授權，由我撰寫並自行核准 `preregistration_v8.md`，不另停下。分支 `v8-analysis` 自 `v7-analysis`（68ca4a7）。`config.py`：v4–v7 區塊條件擴充到 v8，新增 v8 區塊；已以子程序逐一比對 v1、v2、v3c、v4、v4b1–3、v5、v6、v7、v7a–c 的所有大寫設定值，與 v7 版完全相同。查證：SR2000（arXiv:astro-ph/0003308）的樣本、頻段與方法；RXTE 歸檔 SE 事件檔格式（實際下載一個檔確認含 PCUID）；以 HTTP range 讀檔頭盤點 S1 硬態類 180 筆的事件模式（148 筆合格，約 0.98 GB）；HEASARC TAP 查 Marcel+2026 Table 1 尚未用過的 BH（可用者只有 GS 1354-64、SS 433）；WSL HEASoft 的 `nh`（HI4PI）與 XSPEC。未下載任何 v8 資料、未計算任何 v8 特徵、未訓練任何 v8 模型 | 否 |
| IC3 判準（建模前） | 預先設定寫「純 Poisson 時 HF 的平方 < 0.01²」。這是絕對門檻：模擬中 2000 c/s/PCU、640 s 時，HF2 頻段的統計雜訊約 3×10⁻⁴，遠大於 10⁻⁴，即使估計量無偏也會失敗，因此是我寫錯的判準。改為統計判準：各頻段平均值相對其標準誤 \|z\| < 3（無偏）。另外，段落邏輯測試的期望值我手算錯了（應為 6 段，寫成 5 段），程式本身無誤，已更正期望值。全部 IC3 測試通過（`logs/v8c/test_v8lib.csv`）：正弦恢復 0.098–0.107、純 Poisson \|z\| ≤ 1.9、10 µs deadtime 下空白頻段 z = 0.38 | 否（任何真實 HF 特徵之前） |
| v8b 下載 | `41_v8b_select.py`：GS 1354-64 11 筆合格（HEASARC TAP，其中 3 筆目錄曝光缺值）、SS 433 108 筆（MissionLongData）。`21_v4b2_fetch_process.py`（XRB_VERSION=v8b，程式未改）：GS 1354-64 8/11 接受（20431-01-01-00、-02-00、-02-03 三筆沒有 StdProd，404），SS 433 15/15 接受。外部集 X 的能態（`42_v8_states_timing.py`）：硬態類 99 筆（不含壓力測試源），BH 天體 5 個（Cyg X-1 14、GS 1354-64 7、V4641 Sgr 5、LMC X-1 3、XTE J1859+226 1），NS 天體 15 個 → v8b primary 可檢定。SS 433 15/15 為軟態類 | 否（看到能態計數，未看任何分類結果） |
| v8d 程式錯誤 | `v8d_heasoft.sh` 以 bash 讀 Windows 寫出的 CSV 時保留了行尾 `\r`，使 N_H 輸出列被拆開（斷言失敗而停止，未產生任何結果）。修正為讀檔前 `tr -d '\r'`，重算 N_H 與穿透率表 | 否 |
| v8c 下載方式 | 事件檔盤點：S1 與 X 的硬態類共 311 筆，201 筆有合格事件檔，共約 2.4 GB（模式：E_125us_64M_0_1s 327 檔、E_125us_64M_0_8s 5、E_16us_64M_0_8s 5、E_250us_128M_0_1s 4）。`common.download`（urllib）在本機只有約 0.1 MB/s，同時以 curl 平行下載約 0.5 MB/s／連線。改用 `v8lib.download_curl`：curl 串流到 `.part` 再改名，記錄格式與 `common.download` 相同（URL、bytes、SHA256，另加 `tool=curl`）。已下載的檔案保留（存在即略過）。只改下載工具，不改任何規則 | 否 |
| v8d 結果 | IC5（tbabs 穿透率：N_H→0 時為 1、單調、2–4 < 4–10 < 10–20 keV）、IC6（未校正的 RF／LR／KNN 與 v7c2 OOF 最大差 ≤ 1.1e-16）皆通過。HI4PI N_H 中位數：BH 0.39、NPNS 0.46 ×10²² cm⁻²。★ RF[C2D_NH] − RF[C1D_NH] 來源 AUC **+0.377 [+0.160, +0.595] → 有差異**；log N_H 單獨 AUC 0.41 [0.24, 0.59]；差中差（校正後 − 校正前的增益）RF −0.034 [−0.223, +0.130]、KNN −0.104 [−0.231, +0.006]、LR −0.016。注意：RF[C1D] 的 AUC 只有 0.364（低於 0.5），增益有一部分來自基準低於隨機；RF[C2D_NH] 本身 0.737 [0.550, 0.907] | 結果 |
| v8a 結果 | IC1 通過（v2 H-LR 硬態類 AUC 與區間與 v7a 完全相同；硬態專屬 H-LR 與 v7a 2f 最大差 1e-16）。★ 硬態類觀測層級 AUC：v5 H+T-LR 0.910 − v2 H-LR 0.646 = **+0.264 [+0.048, +0.455] → 有差異**。描述性：H+T*-LR +0.270、H+T-RF − H-RF +0.230、H+N+T − H+N +0.201、排除爆發 +0.280、只用硬態訓練 +0.267；T1 +0.280、T2 +0.228、T3 +0.008；能態差距的差中差 −0.229 [−0.420, −0.005]（H+T-LR 的軟－硬差距 0.080）；硬態類來源層級 AUC +0.185 [+0.008, +0.403]、BA +0.147 [−0.084, +0.391] | 結果 |
| v8b 結果 | IC2 通過（E 上 401 筆分數與 v6a 最大差 1.1e-16）。★ X 硬態類（99 筆、5 BH／15 NS 天體）凍結 H_R+T-LR 0.882 − H_R-LR 0.817 = **+0.064 [−0.185, +0.367] → 未偵測到**。GS 1354-64 硬態 0.54 → 0.97、LMC X-1 0.82 → 0.99、Cyg X-1 0.74 → 0.80；但 IGR J00291+5934（AMXP）0.45 → 0.89、EXO 1745-248 0.32 → 0.73 被推向 BH。軟態類 −0.118 [−0.337, +0.055]（SS 433 0.31 → 0.02、V4641 Sgr 0.93 → 0.65） | 結果 |
| v8c IC4 未通過 | 事件檔下載完成（201 筆、2.44 GB；盤點加上 HTTP 重試，第一次盤點有 1 筆因連線錯誤漏掉）。空白頻段品質檢查：S1 148 筆中 0 筆被排除（\|z\| > 3 的 4 筆）。**IC4：事件資料 LC（1–4 Hz）與 Standard-1 T3* 的 Spearman 0.813，低於預先寫定的 0.90 → 依預先設定 v8c 停止**。在任何 v8c 模型之前做了診斷（`results/v8c/ic4_diagnosis.csv`）：(1) 硬態類內 1–4 Hz rms 的動態範圍很窄（IQR 0.11–0.14），T3* 自己的 split-half Spearman 只有 0.563（Spearman-Brown 換算全資料約 0.72），兩個 Standard-1 估計量（v5 A/B 與 v6 全配對）互比也只有 0.896；(2) 高 S/N 的一半觀測 Spearman 0.978、斜率約 1、中位比 0.94 → 沒有偏差；(3) 但發現預先寫定的「每段分數變異取平均」（mean of ratios）在暗源上不穩：16 s 段的源平均值很不準，分母接近 0 的段會爆掉（Aql X-1 80403-01-03-00 單段 −195，觀測平均 −0.48）。修正為標準的 ratio of means（各段交叉功率加總 ／ 各段源計數乘積加總，標準誤用 delta method），舊值以 `*_mean_of_ratios` 欄位保留；IC3 全部重跑通過，另加一個暗源合成測試（4 c/s/PCU 源、25 c/s/PCU 背景，rms 0.30 恢復為 0.304）。修正後 IC4 = 0.818，仍未通過，原因是 (1) 的雜訊上限，不是程式錯誤 | **是**（看過 IC4 結果之後、任何 v8c 模型之前） |
| v8c 處置 | 依預先設定，v8c 的 ★ primary **不作確認性判讀**。由於診斷顯示估計量本身沒有偏差、未通過是判準設定不當（0.90 是依 v5 全能態樣本的動態範圍訂的，不適用於硬態類內），仍執行 v8c 的全部預先寫好的模型與描述，但**全部標為探索性**，報告中不使用「有差異」作結論 | **是**（同上） |
| v8c 結果（探索性） | S1-HF：148 筆、23 源（6 BH）。在 S1-HF 內重新訓練：H-LR 0.797、H+HF-LR 0.740（−0.056 [−0.154, +0.010]）、H+T-LR 0.943、H+T+HF-LR 0.936（−0.007）、HF-LR 0.384；RF：H+HF-RF − H-RF +0.244 [+0.098, +0.411]、H+T+HF-RF − H+T-RF +0.034 [+0.005, +0.075]。排除 AMXP 後 LR 增量 −0.027。外部 X-HF（44 筆，2 BH／11 NS）凍結 H_R+HF-LR − H_R-LR −0.021。SR2000 式判準（每源 HF3 > 3σ → NS）：BH 6/6 判為 BH，NS 6/17 判為 NS | 結果 |
| v8c 事後修正（空白頻段扣除） | 看到上列結果後發現：4U 1323-619 在空白頻段（1536–2048 Hz）的功率（0.096）大於 512–1024 Hz（0.072），GS 1826-238 兩者相當 → 有一個跨 PCU 的白色相關成分（可能是同時打到多個 PCU 的粒子事件；暗源經源計數率正規化後被放大）。事後描述性分析：各頻段減去「空白頻段 × 頻寬比」。扣除後 SR2000 式判準只有 SAX J1808.4-3658（z = 3.3，可能是 401 Hz 脈衝的倍頻）在 3σ 以上；BH 全部未偵測到（\|z\| < 1.5）；4U 1608-52、4U 1636-53、4U 1702-429、4U 1728-34 的 z 為 1.8–2.6。模型：H+HFc-LR − H-LR +0.074 [−0.023, +0.201]、H+HFc-RF − H-RF +0.189 [+0.019, +0.400]、相對 H+T 的增量 LR +0.006、RF +0.009。全部標為事後分析 | **是**（看過 v8c 結果之後） |
| v8 完成 | 報告 `report_v8_zh-TW.md`；README 與 `final_report_zh-TW.md` 新增 v8 一節（只有插入，既有數字未改）；總結圖 `figures/v8/v8_summary.png`；`run_v8.ps1`／`run_v8.sh`（43 以 exit 3 結束時仍繼續，與實際執行過程相同） | — |

## v9（NICER 獨立檢驗：硬態內時間資訊、BH 特徵頻率；MAXI 能態分層；2026-10-05）

| 時間 | 決定 / 變更 | 是否在看過 v9 結果之後 |
|---|---|---|
| 合併 | 使用者「merge and pull and get on to next step」：PR #5（v7）與 #6（v8）以 merge commit 合併到 master（7ecd480、a2e1cce），本機 master 已 pull | — |
| 階段 0（約 23:00） | 撰寫並自行核准 `preregistration_v9.md`。分支 `v9-analysis` 自 master a2e1cce。`config.py`：v4–v7 區塊條件擴充到 v9，新增 v9 區塊；已逐一比對 v1–v8 全部版本（含 v8、v8b–d）的大寫設定值，與 v8 版完全相同。查證：HEASARC TAP `nicermastr` 欄位與 Marcel BH／MINBAR NS 的 NICER 觀測數；cl 事件檔格式（HTTP range 讀檔頭：TIME/PI/DET_ID，每列 39 bytes，亮源單檔可達 2.2 GB）；NICER 偵測器編號、PI 道寬、視野（Mission Guide、CALDB Det Params）；NICER deadtime 論文（arXiv:2409.12574 摘要）。未下載任何 NICER 事件、未計算任何 v9 特徵、未訓練任何 v9 模型 | 否 |
| v9 下載來源（建模前） | 小規模測試時，HEASARC 主站單連線只有約 0.1–0.4 MB/s，亮 BH 的一筆前段（上限 300 MB）要 10–30 分鐘。改從 HEASARC 官方的 AWS 開放資料鏡像（`https://nasa-heasarc.s3.amazonaws.com/nicer/data/obs/`）以 range 下載：實測約 3.5 MB/s，前 4 MB 與主站逐位元組相同。`config.V9_ARCHIVE` 改為鏡像（原網址保留為 `V9_ARCHIVE_HEASARC`）；串流下載改為 curl 每次 16 MB 的 range 請求。測試下載的檔案已刪除，只看過「Aql X-1 第 0 段為軟態類」一筆，沒有任何模型結果。選樣、資料預算與品質規則都不變 | 否 |
| v9 原始檔位置（建模前） | NICER 前段檔預估約 30–40 GB，若放在 repo（OneDrive）內會被同步。依 v4b1 的做法改存到 repo 外的 `XRB_EXTERNAL_RAW`（預設 `~/xrb-pilot-data/raw/nicer/`）；`logs/downloads.jsonl` 照常記錄 URL、bytes、SHA256 | 否 |
| v9c 結果（描述性） | MAXI 主任務依 C4（≥ 4 keV 顏色）三分位（切點 −0.671、−0.445）分層。預先寫定的點層級 AUC 各層都接近 0.5（RF[C2D] 0.49–0.56；C2D − C1D：+0.052 [+0.007, +0.103]、+0.060、+0.167），因為點層級指標被點數多的天體主導（如 Cyg X-1 約 4000 點）。**事後**加上來源層級版本（`v9c_maxi_c4_strata_source_level_post_hoc.csv`）：RF[C2D] − RF[C1D] 在最軟／中間／最硬三層為 +0.388 [+0.151, +0.628]／+0.269 [−0.048, +0.570]／+0.388 [+0.160, +0.603]；N_H 校正後 +0.257／+0.399／+0.361 → 2–4 keV 的增益不集中在任何一層 | 結果；來源層級版本為**事後**加入 |
| v9 資料 | `47_v9_select.py`：25 個確認 BH、115 個 MINBAR 條目（9 個因 0.05° 內有其他條目而排除）；合格 ≥ 5 筆者 BH 11、NS 55，共 522 個時間分段（合格數 < 8 的天體有空分段）。`48_v9_nicer.py`：試 792 筆、接受 368 筆（BH 9 源、NS 54 源），從 AWS 鏡像下載前段共 14.2 GB；排除原因：2–10 keV < 20 c/s 239 筆、有效 128 s 段 < 3 筆 185 筆。SS 433、GS 2023+338 沒有合格觀測。硬態類：BH 7 源 31 筆（MAXI J1820+070 7、Cyg X-1 7、Swift J1727.8-1613 5、GX 339-4 4、GRS 1915+105 4、4U 1543-47 3、LMC X-3 1），NS 32 源 111 筆 | 否（看到數量，未看模型） |
| v9 結果 | IC3 通過（Cyg X-2＋GX 17+2 軟態類 15/16 = 0.94）。★ v9a 硬態類觀測層級 AUC：H_N-LR 0.683 → H_N+T_N-LR 0.795，差 **+0.112 [−0.004, +0.229] → 未偵測到**。描述性：RF +0.236 [+0.104, +0.372]；只用硬態訓練 +0.191 [+0.039, +0.329]；差中差 −0.125 [−0.246, −0.001]（H_N 的軟－硬差距 0.211 → 0.087）；頻段 T2 +0.143 [+0.028, +0.271]、T3 +0.115 [+0.030, +0.217]、T1 +0.048；新 BH（MAXI J1820+070、Swift J1727.8-1613）＋NS：+0.074 [−0.094, +0.252]；計數率 ≥ 100：+0.115 [−0.010, +0.241]；硬態類來源層級 AUC +0.121 [−0.004, +0.254]；軟態類 −0.013。★ v9b：log₁₀ ν_c 顏色條件置換檢定 D = −0.310、p = 0.136 → **未偵測到**（方向與 v6d 的 S1 結果 −0.31 相同）；T3 p = 0.038（Holm 0.19） | 結果 |
| v9 事後檢查 | 看過結果後的描述性分析（不改判讀）：(1) 在 BH 所在的 c2 區間（0.111–0.399），以天體為單位比較 ν_c 的幾何平均：BH 中位數 0.90 Hz、NS 4.25 Hz，Mann–Whitney p = 0.013、AUC 0.81（`results/v9b/v9b_nuc_colour_window_post_hoc.csv`）。預先寫定的 kNN 殘差化不看標籤，BH 在顏色上聚集時會互為鄰居而吃掉部分差異，因此偏保守。(2) 11 個 NS 天體的硬態類觀測 c2 > 0.7（極硬），可能是背景主導（v9 不扣 NICER 背景）或是 dip／掩食；排除後 v9a 為 LR +0.135 [−0.001, +0.273]、RF +0.244 [+0.100, +0.385]（`results/v9a/v9a_post_hoc_exclude_c2_gt_0.7.csv`） | **是**（事後、描述性） |
| v9 完成 | 報告 `report_v9_zh-TW.md`；README 與 `final_report_zh-TW.md` 新增 v9 一節（只有插入，既有數字未改）；總結圖 `figures/v9/v9_summary.png`；`run_v9.ps1`／`run_v9.sh` | — |

## v10（跨儀器整合檢驗：RXTE＋NICER；2026-10-06）

| 時間 | 決定 / 變更 | 是否在看過 v10 結果之後 |
|---|---|---|
| 合併 | 使用者「都存git並且開始v10」：PR #7（v9）以 merge commit 合併到 master（dde4517），本機已 pull。原始資料（data/raw、~/xrb-pilot-data）依全域規則不進 git（皆可由腳本重新下載，SHA256 已記錄） | — |
| 階段 0 | 撰寫並自行核准 `preregistration_v10.md`。分支 `v10-analysis` 自 master dde4517。`config.py`：v4–v7、v9 區塊條件擴充到 v10，新增 v10 區塊；已逐一比對 v1–v9 全部版本的設定值，與 v9 版完全相同。估算：NICER 整筆（每筆上限 1 GB）需在 v9 前段之外再下載約 24 GB（12 筆會被截斷），磁碟剩約 87 GB。尚未下載任何 v10 資料、未計算任何 v10 特徵或合併統計量 | 否 |
| v10b 置換方式（建模前） | 合成測試（`test_v10lib.py`）顯示：在兩台儀器的天體聯集上整體置換（預先設定字面做法）時，只出現在一台儀器的天體也會分走 BH 標籤，使各儀器內的 BH 數大幅波動，虛無分布變寬、檢定力被稀釋。改為**依儀器出現情形分層的受限置換**（只在 RXTE／只在 NICER／兩者皆有，各層 BH 數固定、同一天體在兩台同一標籤），仍符合預先設定「BH 數固定、同一標籤」。合成資料：虛無下 p < 0.05 的比例 0.065（200 組），BH 偏移 −1.5 SD 時檢定力 0.98（50 組）。在任何 v10b 統計量計算之前決定 | 否 |
| v10c 執行 | IC1 通過：6403520101（17.0 MB、729,479 個事件），前段＋尾段串接讀取＝一次下載完整檔。記憶體：OneDrive 佔用約 10 GB RAM，特徵計算平行數由 4 降為 2 | 否 |
| v10c 結果 | 整筆 NICER：366/368 筆可用（2 筆計數率 19.2、19.8 c/s，略低於 20）。尾段 24.2 GB（180 筆讀到檔尾、12 筆在 1 GB 截斷）。每筆的 128 s 段數中位數 9 → 16。前段 vs 整筆 Spearman：T1 0.915、T2 0.948、T3 0.961、0.1–10 Hz rms 0.968、ν_c 0.932。整筆的 split-half 信度（Spearman-Brown）：T1 0.81、T2 0.89、T3 0.81、rms 0.86、ν_c 0.89。能態變動 9/368。IC4 通過（15/16 軟態類） | 結果 |
| v10 程式錯誤 | `pooled_perm` 分層時，若所有天體都只出現在同一台儀器（單一儀器的 IC2b），`np.array(..., dtype=object)` 會把等長 tuple 轉成二維陣列而出錯；改用 Python list。v10a 已先算完，重跑結果相同。圖中散點的抖動改用 crc32 種子（原本用 `hash()`，每次執行位置不同） | 否（程式修正，統計量不變） |
| v10 結果 | IC3：34 個 RXTE 天體對到 NICER 天體，標籤無衝突；天體聯集 86 個（16 BH）。IC2a：只放 RXTE v2 時，合併 bootstrap 完全重現 v8a（+0.2643 [+0.0484, +0.4549]）；IC2b：單一儀器的 D 與 `v6lib.perm_test` 相同。★ **v10a 合併硬態時間增益 +0.145 [+0.028, +0.257] → 有差異**。各子樣本：RXTE v2 +0.264、RXTE 外部 +0.064、NICER 整筆 +0.107 [−0.010, +0.224]。BH 數加權 +0.154；RF（RXTE v2＋NICER）+0.224 [+0.108, +0.333]；排除背景可疑的 13 筆 NICER 後 +0.152。逐一移除 BH 天體：+0.110（移除 XTE J1118+480）到 +0.158。★ **v10b 合併 D(log₁₀ ν_c) = −0.368 dex，p = 0.0012 → 有差異**。RXTE 硬態類單獨 −0.265（p = 0.0018），NICER 整筆單獨 −0.471（p = 0.033）。顏色區間（事先寫定、描述性）：合併 −0.381（p = 0.015）。逐一移除 BH 天體：−0.33 到 −0.42 | 結果 |
