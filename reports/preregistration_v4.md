# v4 預先設定（寫於任何 v4 模型訓練與任何 v4 下載之前）

寫於 2026-09-30，分支 `v4-analysis`。**此時已看過 v1、v2、v3 的全部結果**（見 `final_report_zh-TW.md`），
所以 v4 的每個問題都是針對已知結果提出的延伸檢驗，這點會在 v4 報告中明寫。
v4 不改動 v1–v3 的任何資料、fold、程式行為或輸出。v4 以 `XRB_VERSION=v4`（v4a、burst 檢查）與 `v4b1`／`v4b2`／`v4b3`（更多資料）切換，
輸出寫到 `data/v4*/`、`results/v4*/`、`figures/v4*/`、`logs/v4*/`。設定值寫在 `scripts/config.py` 的 v4 區塊。

## 0. 兩個問題與唯一的基準

1. 換演算法能否超越 H-LR？（v4a）
2. 更多資料、更寬能段能否超越 H-LR？（v4b3 HEXTE、v4b2 更早 gain epoch、v4b1 每源全部觀測）

**基準＝H-LR 的 v2 LOSO out-of-fold 預測**（`results/v2/oof_predictions_loso.csv`，representation=`H_colours`、model=`LogReg`，門檻 0.5），不是 Dummy。
在不同樣本上的比較（v4b*），基準是「同一樣本、同一 folds 上以 v2 相同程式重算的 H-LR」，並先確認在 v2 樣本上與 v2 檔一致。

## 1. 共同規則（全部 v4 分析）

| 項目 | 規則 |
|---|---|
| 評估 | LOSO（每次保留一個天體）；folds 與 v2 相同（`results/v2/folds_loso.csv`）；擴充樣本時為同樣的 leave-one-source-out |
| 來源層級分數 | 該源所有 out-of-fold BH 分數的平均 |
| 門檻 | 固定 0.5；**只有**明確在內層選門檻的分析（1d、1e）例外，且門檻只用訓練天體決定 |
| 標題指標 | 來源層級 balanced accuracy、來源層級 AUC；另報觀測層級 balanced accuracy |
| 不確定性 | 在 BH、NS 內各自有放回抽天體 2000 次，seed 42，抽樣程序與 `09_bootstrap_sources.py`／`v3lib.bootstrap` 相同（固定 OOF，不重新訓練）；所有與 H-LR 的比較都用**同一組抽樣**做配對差 |
| 判讀 | 「有提升」＝與 H-LR 的配對差 95% 區間**完全 > 0**（對該指標）。其餘一律寫「未偵測到」。每個指標分開判讀，不合併 |
| 巢狀原則 | 所有超參數、門檻、模型／表示法的選擇只能用外層訓練天體（內層 LOSO）；外層測試天體不參與任何選擇 |
| 隨機性 | 所有 `random_state`／seed 固定（42，或下文列出的 seed 集合） |
| 變更 | 任何變更記入 `decision_log.md`，註明是否在看到 v4 結果之後 |

## 2. v4a：演算法比較（只用 `data/v2/processed/features.npz`，不下載）

表示法：H、HI、B、A，一律由 `v3lib.v2_representations` 產生（與 v2 完全相同）。

### 1a 重現檢查（先做，未通過則停止）
以 v4 程式重算 H、HI、B、A × LR、RF 的 LOSO OOF，與 `results/v2/oof_predictions_loso.csv` 比較：
LR 逐筆分數差 ≤1e-8（實務上逐位）、RF 逐筆 ≤0.01，且 0 個標籤改變。輸出 `results/v4/v4a_reproduction_check.csv`。

### 1b 固定超參數的新模型（描述性）
所有模型處理類別不平衡的方式事先固定：

| 模型 | 固定設定 | 不平衡處理 | 分數 |
|---|---|---|---|
| LR（參照） | 同 v2：StandardScaler→LogisticRegression(C=1, L2, lbfgs, max_iter=5000) | class_weight=balanced | predict_proba |
| RF（參照） | 同 v2：500 樹、max_features=sqrt、min_samples_leaf=2 | class_weight=balanced | predict_proba |
| ExtraTrees | 500 樹、max_features=sqrt、min_samples_leaf=2、random_state=42 | class_weight=balanced | predict_proba |
| HistGradientBoosting | learning_rate=0.1、max_iter=200、max_leaf_nodes=15、min_samples_leaf=20、l2_regularization=0、early_stopping=False、random_state=42 | class_weight=balanced（sklearn 1.8 支援） | predict_proba |
| SVM-RBF | StandardScaler→SVC(C=1, gamma='scale', kernel='rbf') | class_weight=balanced | 1/(1+exp(−decision_function))；不用 Platt 校正（避免其內部隨機 CV）；0.5 ⇔ SVM 決策面 |
| kNN | StandardScaler→KNeighborsClassifier(k=15, weights='uniform') | 無 class_weight：以訓練 fold 類別比例 π 做先驗校正 p′_BH = (p_BH/π_BH)/(p_BH/π_BH + p_NS/π_NS)（等價於兩類等權） | 校正後機率 |
| QDA | StandardScaler→QuadraticDiscriminantAnalysis(reg_param=0.1, priors=[0.5, 0.5]) | 均等 priors | predict_proba |
| MLP | StandardScaler→MLPClassifier(hidden=(32,), alpha=1e-3, early_stopping=True, validation_fraction=0.2, max_iter=500)；seed 0–4 五個模型平均 | fit 時 sample_weight＝兩類等權（sklearn 1.8 MLP 支援 sample_weight） | 5 個 seed 的 predict_proba 平均 |
| 1D-CNN（可選，只用 B） | —— | —— | **跳過**：本機 venv 沒有 torch（已確認），不另行安裝 |

每個模型 × 四種表示法各一組 LOSO OOF。

### 1c 天體等權重版本（描述性）
sample_weight：w_i = 1 /（該類訓練天體數 × 該天體訓練觀測數），使每個訓練天體總權重相同、兩類總權重相等（各為 1）。
對 LR、RF、HistGB 各跑一次（此時不再另設 class_weight），四種表示法。

### 1d 巢狀 LOSO（每個演算法 × 每種表示法各自，共 8 × 4 = 32 個程序，描述性）
外層 31 folds；每個外層 fold 在 30 個訓練天體上做內層 LOSO（30 folds），對下列固定網格的每個設定取得內層 OOF：

| 演算法 | 網格（其餘同 1b） |
|---|---|
| LR | C ∈ {0.01, 0.1, 1, 10} |
| RF | min_samples_leaf ∈ {1, 2, 5, 10}；**內層 200 樹**，外層重訓 500 樹 |
| ExtraTrees | min_samples_leaf ∈ {1, 2, 5, 10}；內層 200 樹，外層 500 樹 |
| HistGB | learning_rate ∈ {0.05, 0.1} × max_leaf_nodes ∈ {7, 15} |
| SVM-RBF | C ∈ {0.1, 1, 10} × gamma ∈ {0.3, 1, 3} × 'scale' 值 |
| kNN | k ∈ {5, 15, 31} |
| QDA | reg_param ∈ {0.01, 0.1, 0.5} |
| MLP | hidden ∈ {(16,), (32, 16)} × alpha ∈ {1e-4, 1e-2}；內層 seed 0–2 平均，外層 seed 0–4 平均 |

選擇規則（全部只用內層 OOF）：
1. 設定：內層**來源層級 AUC** 最高者；平手依序比內層來源 balanced accuracy（在下一步選出的門檻下）、再取網格中列在最前者。
2. 門檻：在選定設定的內層來源平均分數上，選使內層來源 balanced accuracy 最大的門檻（候選＝相鄰排序分數的中點）；
   平手時取最接近 0.5 的區間中點。
3. 以選定設定在 30 個訓練天體上重訓（樹模型 500 樹），預測外層測試天體；觀測與來源的判斷都用該 fold 選出的門檻。
4. 外層來源 AUC 以「來源平均分數 − 該 fold 門檻」計算（使不同 fold 的模型可放在同一尺度；這是近似，報告中註明）。

### 1e 主要檢定（v4 唯一的 primary）：巢狀自動選擇
程序同 1d，但內層在**全部 8 個演算法 × 4 種表示法 × 各自網格**（共 35 × 4 = 140 個設定）中挑選最佳組合與門檻。
外層 OOF 與 H-LR（v2 OOF，門檻 0.5）做配對 bootstrap 差：
- 來源層級 balanced accuracy 的差、來源層級 AUC 的差：各自 95% 區間完全 > 0 才判為「有提升」。
- 同時報告觀測層級 balanced accuracy 差、每個外層 fold 選到的組合與門檻（`results/v4/v4a_nested_selection.csv`）。
- 這個程序把「從很多模型中挑最好」的樂觀偏差包含在評估裡。1b、1c、1d 的個別組合只做描述性報告；
  報告中會明寫多重比較問題（1b 32 個＋1c 12 個＋1d 32 個＝76 個組合），**不以其中最好的一個作為結論**。
- 限制（事先寫明）：bootstrap 固定 OOF，不含選擇過程本身的變異。

### 1f 一致性
每個組合（1b、1c、1d、1e）與 H-LR 的逐筆 OOF 分數 Spearman 相關與預測標籤一致率（同 `v3lib.agreement`）。

### 1g 圖
- `figures/v4/v4a_forest_source_auc.png`：各組合來源 AUC 與 95% 區間（H-LR 為參考線），以及與 H-LR 的配對差。
- `figures/v4/v4a_colour_boundaries.png`：H 顏色平面上，以全部 456 筆擬合的 LR、RF、SVM-RBF、kNN、HistGB 的 0.5 邊界（**僅視覺化**，不用於任何評估）。

### v4a 計算量估計
以合成資料（456 × 45，非研究資料）量測單次訓練時間：LR 3 ms、RF 500 樹 0.62 s、RF 200 樹 0.26 s、ExtraTrees 500 樹 0.35 s、HistGB 0.23 s、SVC 8 ms、kNN <1 ms、QDA 11 ms、MLP 12–37 ms。
1e 內層：每個外層 fold 約 140 個設定 × 30 次訓練 ≈ 4,200 次；全部約 13 萬次訓練、約 3–4 CPU 小時。
本機 20 個邏輯處理器，以外層 fold 平行（16 個 worker）約 15–30 分鐘；1a–1d、1f–1g 合計另約 10–20 分鐘。
1d 與 1e 共用內層 OOF（只算一次）。

## 3. burst 洩漏檢查（v4，需 Standard-1；v2 的 456 筆已全部在本機 `data/raw/std1/`，不需下載）

### 2a 偵測規則（依 Galloway et al. 2008, ApJS 179, 360；arXiv:astro-ph/0608259）
Galloway+2008 §2：以 2–60 keV、1 s 光變曲線，「每次觀測計算 1 s 計數率的整體平均與標準差，超過平均 4σ 的 bin 為候選」，再以目視確認；
並指出 burst 上升時間 ≲1–10 s、持續數十到數百秒。v4 規則：
1. 光變曲線：Standard-1（FS46_*，0.125 s）各 PCU good-xenon 計數（XeCntPcu0–4）加總，重分箱為 1 s，只取能譜 GTI 內的時間。
2. 候選：計數率 > 該觀測平均 + 4σ（平均、σ 以該觀測 GTI 內全部 1 s bin 計算）的 bin；相距 <30 s 的候選 bin 合併為一個事件。
3. 自動判定為 burst（全部成立）：
   - 事件峰值 ≥ 1.5 × 持續流量（持續流量＝事件前 60 s 的中位數，不足 60 s 則用該觀測 GTI 的中位數）；
   - 上升：從峰值往前，首次低於「持續＋25% × (峰值−持續)」的時間到峰值 ≤ 10 s；
   - 衰減：峰值後回落到「持續＋50% × (峰值−持續)」以下所需時間在 3–300 s 之間；
   - 不是單一 1 s bin 的孤立突波（至少 3 個相鄰 1 s bin 高於「持續＋25% × (峰值−持續)」）。
4. 每個候選（不論是否判為 burst）都輸出光變曲線圖到 `figures/v4/burst_candidates/`，由我逐張目視，
   目視結論記在 `results/v4/burst_candidates.csv`。**主要排除集合＝自動規則**；若目視結論不同，另以「目視集合」做一次敏感度分析，兩者都報告。

### 2b 輸出
`results/v4/burst_flags.csv`：每筆觀測是否含 burst、burst 數、burst 時間佔能譜曝光比例（burst 區間＝上升起點到回落到持續＋10% × (峰值−持續)）。

### 2c 若有含 burst 的觀測
排除它們（整筆觀測），對 H-LR、H-RF、B-LR、B-RF 以相同 LOSO 重跑，與原 v2 OOF 在「共同保留的觀測」上配對比較
（bootstrap 同上）；並在排除後的樣本上重算 v2 主要比較（B vs H）與 v3a 主要比較（H+B vs H），報告 v1–v3 結論是否改變。
若某天體因此少於 5 筆觀測，保留該天體並記錄（不因結果移除天體）。報告中獨立一節。
計算量：數分鐘。

## 4. v4b 更多資料（每個子階段下載前都停下來回報名單與下載量，等核准）

### 3a v4b3：HEXTE 高能延伸（最優先）

**已查證的事實**（HEASARC）：
- Standard Products 目錄 `stdprod/` 內有 HEXTE 產品：`xh<obs>_s0.pha`／`_s1.pha`（cluster 0=A、1=B 的源譜）、
  `_b0.pha`／`_b1.pha`（背景）、`xh97mar20c_pwa.rmf`／`xh97mar20c_pwb013.rmf`、`hexte_00may26_pwa.arf`／`_pwb013.arf`，
  以及 15–30、30–60、60–250 keV 的 128 s 光變曲線（RXTE Standard Products 說明頁；抽查 3 筆 v2 觀測的目錄確認）。
- 「HEXTE cluster 不 rocking 時沒有背景取樣，不產生該 cluster 的背景與淨產品」；cluster A 自 2006 年 7 月起固定在 on-source，
  之後沒有 cluster 0 的背景產品（Standard Products 說明頁）。
- cluster B 於 2009-12-14 約 16:10 UT 停止 rocking，2010-03-29 18:00 UT 固定在 off-source 當背景用；
  之後 cluster A 的背景需用 `hextebackest` 估計，官方說明其結果在約 63 keV 有線狀殘差（HEASARC RXTE 2010 news archive）。
- 抽查到：2010 年的觀測只有 `s0`、`b1`，沒有 `s1`、`b0`。

**事先規則**
1. 只用 **cluster B（`s1`、`b1`、`pwb013` rmf/arf）**，淨譜＝s1 − b1（依 EXPOSURE、BACKSCAL 縮放，與 PCA 相同慣例）。理由：cluster B 在 2009-12-14 前一直 rocking，背景是同時量測的；全任務使用同一 cluster。
2. 觀測日期 ≥ MJD 55179.6736（2009-12-14 16:10 UT）者**沒有 HEXTE 特徵**（v2 樣本中 60 筆：6 BH、54 NS，18 個天體）；缺少 `s1` 或 `b1` 者同。
3. **deadtime**：v4b3 下載前先檢查 HEXTE pha header（是否已做 deadtime 校正、EXPOSURE 定義）。若無法從 header／官方文件確認，**停下來回報**，不自行假設。
4. 能段與特徵（在儀器計數空間，count/s/cluster）：F_X(25–40)、F_X(40–60)（以 rmf EBOUNDS 通道重疊，與 PCA 相同的均勻分配）。
   - 高能色 X1 = F_X(25–40) / F_PCA(16–25)（PCA 為 count/s/PCU；跨儀器比值只作為分類特徵，不作物理解釋）；
   - 高能色 X2 = F_X(40–60) / F_X(25–40)。
5. S/N 規則（事先固定，不依結果）：若比值的分母 S/N（淨計數率／誤差）< 3，該色設為缺值；以**訓練 fold 內的中位數**補值，
   並加一個「該色缺值」的 0/1 指標特徵（補值與指標都在 Pipeline 內，只用訓練資料）。報告缺值筆數（依類別、天體）。
   分子 S/N 不設門檻（非正值照實保留，同 PCA 慣例）。
6. 主比較（在「有 HEXTE 特徵」的觀測子集上，LOSO，與同子集重算的 H 配對）：H+X vs H，LR 與 RF 各一。
   判讀同共同規則。另報 H+X 與 v2 H-LR（全樣本）的關係作為描述。
7. 次要：**顏色重疊區**子集，定義固定為 F(7–10)/F(5–7) ≥ 0.70 且 F(16–25)/F(10–16) ≥ 0.20（v2 H 平面上 NS 軌跡右上端；
   在 v2 456 筆中有 234 筆：57 BH、177 NS、26 個天體）。這個矩形是在看過 v2 顏色圖之後選的，屬事後定義，報告中註明。
   重疊區內報告 H 與 H+X 的觀測層級 balanced accuracy 與（有 ≥3 筆重疊區觀測的天體的）來源層級指標；模型仍在全子集上訓練。
8. 下載量估計：每筆 `s1`、`b1` 約數十 KB，rmf/arf 共用（少數檔）；v2 的 396 筆（456 − 60）約 20–50 MB，約 800 個檔。

### 3b v4b2：更早的 gain epoch
**已查證的 gain epoch 邊界**（HEASARC「Energy-Channel Conversion Table」）：
epoch 1 至 1996-03-21 18:33；epoch 2 至 1996-04-15 23:05；epoch 3 至 1999-03-22 17:37；epoch 4 至 2000-05-13 00:00；epoch 5 之後。
對應 MJD：50163.7729、50188.9618、51259.7340、51677.0000（astropy 轉換）。

規則：
1. 來源規則同 v2（BlackCAT 動力學確認 BH；Galloway+2008 附錄 A 的 NS；有 RXTE MissionLongData 目錄；≥10 筆合格指向），
   但時間窗＝全部 gain epoch（MJD < 55931）。其他合格條件（曝光 ≥1000 s、STD1RATE ≥5、指向 ≤0.1°）與 v2 相同。
2. 樣本：v2 的 456 筆**原樣保留**；另加入「在 epoch 5 不足 10 筆、但全任務 ≥10 筆」而新符合規則的天體，每個以 v2 相同程序抽 15 筆（全任務時間分層）。
   以本機既有目錄初算：XTE J1859+226（BH，112 筆合格，全在 epoch 5 之前）與 V4641 Sgr（BH，全任務 11 筆）可能新增；
   **Galloway+2008 附錄 A 的 NS 名單須在 3b 開始時逐一查證**是否有目錄檔、並重算合格數，列出後停下來。
3. 新表示 R：每 bin 淨計數率 ÷ 該觀測 response 折疊「Γ=2、固定 N_H=0 的冪律」的預期計數率（v2 `features.npz` 已存 `pl2`）。
   選 N_H=0 的理由：任何固定 N_H 對所有觀測乘上相同的能量相依因子，只在 response 差異的二階效應上不同。
   H_R = [ (C(7–10)/P(7–10)) / (C(5–7)/P(5–7)) , (C(16–25)/P(16–25)) / (C(10–16)/P(10–16)) ]，C＝淨計數、P＝折疊冪律預期計數（同能段）。
4. **橋接檢查（必須先通過）**：在 v2 的 456 筆上，H_R-LR 與 H-LR 的 LOSO 配對差（來源 balanced accuracy、來源 AUC）95% 區間都包含 0，
   且逐筆 OOF 分數 Spearman ≥ 0.90。不通過則停止 v4b2 並回報。
5. 通過後，在擴充樣本上跑 H_R、R 的 LR／RF（固定超參數，同 v2），與同樣本上的 H_R-LR 參照、以及 v2 H-LR 比較；
   gain epoch 只作為診斷變數（依 epoch 分組的分數分布、分數與 epoch 的關係），**不得作為分類特徵**。
6. 下載量估計：若只新增 2 個 BH 天體：約 30 筆 × (Std2 三檔 ≈ 50 KB + Standard-1 ≈ 0.2–0.4 MB) ≈ 10–20 MB；若 NS 名單也擴大，另行回報。

### 3c v4b1：每源全部合格觀測（epoch 5）
1. 31 個 v2 天體、epoch 5、v2 相同合格與品質規則；每源用**全部**合格指向（不再抽 15 筆）。依既有候選清單約 7,975 筆（其中 456 筆已下載）。
2. 模型：H、B、A、HI × LR、RF，搭配 1c 的天體等權重；另報 class_weight=balanced 的版本作描述。
3. 主比較：天體等權重 H-LR 與各組合 vs v2 H-LR（v2 樣本的 456 筆 OOF 為基準；新樣本的評估以來源層級為主，觀測層級另報）。
4. 報告中明寫：有效樣本數仍是 31 個天體（7 BH），觀測數增加不會等比例增加檢定力。
5. 下載量估計：約 7,500 筆新觀測 ×（Std2 三檔 ≈ 50 KB + Standard-1 ≈ 0.2–0.4 MB）≈ 2–3 GB，約 3 萬次 HTTP 請求；
   以 v2／v3c 的速度（4 執行緒）估約 10–20 小時。訓練：數十分鐘。

## 5. 不做的事
1D-CNN（無 torch，跳過）；時間變化特徵；以 XSPEC 擬合參數建特徵；把 gain epoch 或觀測日期當特徵；在測試天體上調門檻。

## 6. 報告
`reports/report_v4_zh-TW.md`，結構：做了什麼 → 結果 → 解讀（數據直接支持／可能解釋（未驗證）／需要更多資料的假說）→ 限制 → 與預先設定的差異。
`final_report_zh-TW.md` 新增 v4 一節（不改 v1–v3 既有數字）。提供 `run_v4.sh`、`run_v4.ps1`。
