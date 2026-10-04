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
