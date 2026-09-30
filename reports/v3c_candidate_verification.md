# v3c 候選名單查證（凍結於 2026-09-30 03:47 +08:00，任何 v3c 下載與任何 v3b/v3c 分類結果之前）

依據：
- BlackCAT 網頁版（https://research.iac.es/proyecto/compactos/BlackCAT/，transients 表 72 個天體，各天體頁 `info.php?id=N`），2026-09-30 查詢。
- Corral-Santana et al. 2016，A&A 587, A61（arXiv:1510.08869）：§2 “Persistent” 段、Table 2（動力學確認者以灰底標示）與 Table 5（動力學確認 BH 的雙星參數）。

規則（使用者指定）：已有動力學確認 → 刪除；有 NS 證據（爆發、脈衝）→ 刪除；找不到可靠依據 → 刪除。只允許刪除或修正 `catalog_name`，不新增天體。

BlackCAT 網頁版的天體頁有三種狀態：
- 動力學確認：頁面寫 “Dynamically confirmed BH”，並有 f(M)、K2、M1。例如 GRO J1655-40（id 21）。
- 較強證據，但仍非動力學確認：“Strictly speaking it is not a dynamical BH but there is either a robust mass function or mass determination suggesting the presence of a BH”。
- 一般 candidate：“It is not a dynamical BH but there was at least a suggestion that it might contain a BH based on X-ray properties”，或頁面沒有狀態句。BlackCAT 收錄 transient 的條件是動力學確認，或 X-ray 能譜/時變性質與 BH 相符（論文 §2）。

## 結果：16 個全部保留、0 個刪除

| # | source_id | BlackCAT | 狀態 | NS 證據 | 決定 | 理由 / 來源 |
|---|---|---|---|---|---|---|
| 1 | H1743-322 | id 8 | candidate（頁面無狀態句；不在 Table 5） | 無 | 保留 | https://research.iac.es/proyecto/compactos/BlackCAT/info.php?id=8 |
| 2 | 4U1630-47 | id 2（4U 1630-472） | candidate（無狀態句；不在 Table 5） | 無 | 保留 | …/info.php?id=2 |
| 3 | XTEJ1752-223 | id 48 | “not a dynamical BH but … suggestion … X-ray properties” | 無 | 保留 | …/info.php?id=48 |
| 4 | XTEJ1817-330 | id 42 | 同上 | 無 | 保留 | …/info.php?id=42 |
| 5 | XTEJ1720-318 | id 36 | candidate（無狀態句） | 無 | 保留 | …/info.php?id=36 |
| 6 | XTEJ1748-288 | id 28 | candidate（無狀態句；note：硬能譜、無對應體） | 無 | 保留 | …/info.php?id=28 |
| 7 | MAXIJ1659-152 | id 49 | “Strictly speaking it is not a dynamical BH but … robust mass function or mass determination” | 無 | 保留（見註 a） | …/info.php?id=49 |
| 8 | SWIFTJ1753.5-0127 | id 39 | 同上，頁面列 f(M)=7.8±1.0 M☉（Yanes-Rizo 2025，Hα 翼，非伴星偵測） | 無；Shaw+2016 得 M>7.4±1.2 M☉ | 保留（見註 a） | …/info.php?id=39；https://arxiv.org/abs/1608.04969 |
| 9 | XTEJ1908+094 | id 35 | candidate（無狀態句） | 無 | 保留；0.1° 指向檢查必須保留（4U 1907+097 約 0.4° 外） | …/info.php?id=35 |
| 10 | IGRJ17091-3624 | id 37 | candidate（無狀態句） | 無 | 保留 | …/info.php?id=37 |
| 11 | SLX1746-331 | id 10 | candidate（Peng 2023 質量下限 3±2 M☉，“would imply a BH”） | 無 | 保留（銀河中心） | …/info.php?id=10 |
| 12 | GRS1739-278 | id 24 | candidate（無狀態句） | 無 | 保留（銀河中心） | …/info.php?id=24 |
| 13 | XTEJ1652-453 | id 47 | candidate（無狀態句；IR 對應體不確定） | 無 | 保留 | …/info.php?id=47 |
| 14 | GRS1758-258 | 不在 transient 表；列於論文 §2 “Persistent” 段 | 論文：“quasi-persistent microquasar with a large extinction … near the Galactic centre” | 無 | 保留（見註 b） | arXiv:1510.08869 §2 |
| 15 | 1E1740.7-2942 | 不在 transient 表；論文 §2 | 論文：“4U 1957+11 … and 1E 1740.7-2942 … are persistent BH candidates but they have not been dynamically confirmed” | 無 | 保留（銀河中心） | arXiv:1510.08869 §2 |
| 16 | 4U1957+11 | 不在 transient 表；論文 §2 | 同上 | 無 | 保留 | arXiv:1510.08869 §2 |

註：
- a. MAXI J1659-152 與 Swift J1753.5-0127 在 BlackCAT 屬於「嚴格說不是動力學 BH，但質量函數／質量估計很強」類，與論文中 Swift J1357.2-0933 同類。論文把 Swift J1357.2-0933 另外計入「17+1」個動力學 BH，但本案的規則是「已動力學確認才刪除」，而 BlackCAT 明寫這兩個「not a dynamical BH」，所以保留為 candidate。在報告中標出它們的 BH 證據比其他候選強。
- b. GRS 1758-258 在論文 §2 的 persistent BH 段落中列出，但該句沒有直接用 “BH candidate” 一詞。BlackCAT 把 Galactic BHs 分為 transient／persistent／non-active 三類，此段即 persistent 類，因此視為 BlackCAT 收錄的 persistent candidate。這是對分類段落的解讀，已註明。
- NS 證據：BlackCAT 各天體頁與論文 Table 2 註解均未提到任何一個天體有 type-I 爆發或脈衝；另外對 Swift J1753.5-0127 查了文獻（Shaw+2016）。沒有做其餘逐一的文獻檢索，這是本次查證的限制。
- 銀河中心混淆：XTE J1748-288、SLX 1746-331、GRS 1739-278、GRS 1758-258、1E 1740.7-2942 位於 PCA 約 1° 視野內亮源密集區，Standard Products 可能混入其他源。依預先設定只在報告中標註，不以此刪除。
- `catalog_name`：未修改。實際檔名將由 `13_v3c_resolve_catalogs.py` 查 HEASARC；若需依 listing 修正，會另行記錄。

凍結時 `scripts/config.py` 的 SHA256：`06503f11f9e0c48626beebe25dd96f7fb84eab84e1863d4daedef4d8b849013d`（名單內容未改）。
