# AI-RDM Monitor 資料可信度審計報告

審計時間：2026-07-03（台北時間）  
審計資料版本：`public/data/latest.json`，`as_of = 2026-07-02T19:46:40Z`  
目前 AI-RDM：`70.8`，狀態：`強擴張`

## 一、總結

目前 `70.8` 分在「現有程式實作」下可以完整重算出來，三個子分數與 README 公式的加權關係一致：

```text
AI-RDM = 45% * 77.0 + 35% * 100.0 + 20% * 5.5 = 70.75，四捨五入為 70.8
```

但資料可信度不應視為完全高信心。主要原因不是台灣月營收或市場價格，而是 SEC capex 的季度處理仍有缺口：

- 程式目前沒有把 6-month / 9-month / FY YTD 誤當成單季 capex，這點是正確的。
- 但對只揭露 YTD 累計值、缺少離散季度 fact 的公司，程式沒有用 YTD 差分反推單季值。
- 因此 `latest_quarter` 的 YoY 多數可用，但 `qoq_growth_pct` 與「最近四季 capex」不可靠。

結論：`70.8` 作為「目前公式下的機械計算值」合理；作為「高可信 AI 基建實需分數」則需要修正 SEC YTD 差分與 missing data 計分政策後再提高信心。

## 二、台灣月營收審計

資料來源：`https://mopsfin.twse.com.tw/opendata/t187ap05_L.csv`  
raw snapshot：`public/data/raw/tw_revenue_latest.csv`

審計結果：

- 指定 10 家公司全部正確命中。
- `資料年月 = 11505` 正確轉換為 `2026-05`。
- `YoY` 與 `MoM` 直接取自公開資料欄位，並且用 `當月營收 / 去年當月營收 - 1`、`當月營收 / 上月營收 - 1` 重算後一致。
- 營收金額欄位為「千元」。目前 AI-RDM 只使用成長率，因此千元單位不影響分數。

| 代號 | 公司 | 月份 | 當月營收（千元） | MoM | YoY |
|---|---|---:|---:|---:|---:|
| 3037 | 欣興 | 2026-05 | 14,059,973 | 0.91% | 32.37% |
| 2383 | 台光電 | 2026-05 | 15,618,565 | 12.17% | 114.63% |
| 2454 | 聯發科 | 2026-05 | 47,434,191 | 1.49% | 4.99% |
| 2330 | 台積電 | 2026-05 | 416,975,163 | 1.52% | 30.09% |
| 6669 | 緯穎 | 2026-05 | 84,050,473 | 1.59% | 18.16% |
| 3711 | 日月光投控 | 2026-05 | 63,033,313 | 1.26% | 28.57% |
| 2308 | 台達電 | 2026-05 | 58,961,817 | 0.46% | 43.65% |
| 2345 | 智邦 | 2026-05 | 28,622,864 | 4.61% | 56.58% |
| 2376 | 技嘉 | 2026-05 | 49,053,470 | -6.15% | 4.98% |
| 2356 | 英業達 | 2026-05 | 82,807,865 | -2.33% | 35.30% |

Supply Chain Revenue Momentum 重算：

```text
YoY > 0 比例 = 10 / 10 = 100%
median YoY = 31.23%
median YoY 標準化 = (31.23 - -20) / (50 - -20) * 100 = 73.19
三個月平均 YoY 加速比例 = 缺資料，目前以中性 50 分處理
Supply score = 40% * 100 + 30% * 50 + 30% * 73.19 = 77.0
```

注意事項：

- 目前只有一個月份觀測，尚不能真正計算 3-month average YoY acceleration。
- README 已揭露初始化時該項以中性 50 分處理；因此 `77.0` 是可重現，但不是完整歷史動能分數。

## 三、SEC capex 審計

資料來源：

- `data.sec.gov/api/xbrl/companyfacts/CIK##########.json`
- 最新 10-Q / 10-K filing text 作為關鍵字輔助

目前程式篩選單季 fact 的邏輯：

- 有 `start`、`end`。
- form 為 `10-Q` / `10-K` / amended variants。
- duration 為 70 到 115 天，或 frame 看起來是 `CY####Q#`。
- 因此 6-month、9-month、FY YTD 通常不會被誤當成單季。

審計結論：

- 沒有發現目前把 9-month YTD 直接誤當成單季 capex 的情況。
- 但目前程式會丟掉可用的 YTD 累計值，沒有用 YTD 差分補出缺漏季度。
- 這導致 GOOGL、META、AMZN 的 `qoq_growth_pct` 不可靠；部分情況下其實是在比較 Q1 對前一年 Q1，或 Q1 對前一年 Q3。

### 目前 `latest.json` 的 capex

| 公司 | latest quarter | latest capex | YoY | 目前 QoQ | 審計判斷 |
|---|---:|---:|---:|---:|---|
| MSFT | 2026Q1 | 30.876B | 84.39% | 3.35% | YoY 與 QoQ 合理 |
| GOOGL | 2026Q1 | 35.674B | 107.44% | 107.44% | YoY 可用，QoQ 錯誤 |
| META | 2026Q1 | 18.997B | 46.80% | 46.80% | YoY 可用，QoQ 錯誤 |
| AMZN | 2026Q1 | 44.203B | 76.68% | 25.95% | YoY 可用，QoQ 不是相鄰季度 |

### 用 YTD 差分後的最近季度序列

以下是審計時用同一份 companyfacts 反推的結果。這不是目前 repo 的功能，只用來判斷目前資料處理缺口。

| 公司 | 2025Q2 | 2025Q3 | 2025Q4 | 2026Q1 | 修正後 QoQ | YoY |
|---|---:|---:|---:|---:|---:|---:|
| MSFT | 17.079B | 19.394B | 29.876B | 30.876B | 3.35% | 84.39% |
| GOOGL | 22.446B | 23.953B | 27.851B | 35.674B | 28.09% | 107.44% |
| META | 16.538B | 18.829B | 21.383B | 18.997B | -11.16% | 46.80% |
| AMZN | 32.183B | 35.095B | 39.522B | 44.203B | 11.84% | 76.68% |

需要修正：

1. SEC capex parser 應支援 YTD 差分：
   - Q2 = 6M YTD - Q1
   - Q3 = 9M YTD - 6M YTD
   - Q4 = FY YTD - 9M YTD
2. `qoq_growth_pct` 必須確認比較的是相鄰季度；若缺相鄰季度，應標示 missing。
3. `latest_quarter` 附近應保存 `start`、`end`、`duration_days`、`tag`、`derived_from_ytd`，方便資料透明區查核。

## 四、市場價格審計

AI hardware basket 與 QQQ 全部成功抓取，且本次都來自 Yahoo Finance unofficial chart endpoint。

| Ticker | Source | Last date | 20D return |
|---|---|---:|---:|
| NVDA | yahoo | 2026-07-02 | -9.82% |
| AMD | yahoo | 2026-07-02 | -5.84% |
| AVGO | yahoo | 2026-07-02 | -25.03% |
| MU | yahoo | 2026-07-02 | -11.14% |
| TSM | yahoo | 2026-07-02 | -0.66% |
| ASML | yahoo | 2026-07-02 | 2.05% |
| ANET | yahoo | 2026-07-02 | -8.24% |
| VRT | yahoo | 2026-07-02 | -9.12% |
| SMCI | yahoo | 2026-07-02 | -43.08% |
| LITE | yahoo | 2026-07-02 | -22.50% |
| QQQ | yahoo | 2026-07-02 | -4.44% |

Market Confirmation Spread 重算：

```text
AI hardware basket 20D return = -13.34%
QQQ 20D return = -4.44%
Spread = -8.90%
Market score = (-8.90 - -10) / (10 - -10) * 100 = 5.5
```

審計結果：

- basket 名單與 README 一致。
- QQQ benchmark 正確抓取。
- spread 與 0-100 標準化公式正確。
- 單一來源是 unofficial endpoint，仍應保留 source status；目前已有記錄。

## 五、三個子分數是否符合公式

### Supply Chain Revenue Momentum

符合 README 公式，但目前三個月平均 YoY 加速項尚無足夠歷史，依 README 補充說明以中性 50 分處理。

### Hyperscaler Capex Momentum

分數公式符合 README：

```text
median capex YoY = 80.53%，標準化後 capped at 100
capex YoY > 0 比例 = 4 / 4 = 100
positive keyword ratio = 4 / 4 = 100
Capex score = 50% * 100 + 30% * 100 + 20% * 100 = 100
```

但資料前處理不完全符合「最近四季 capex」的精神，因為目前沒有 YTD 差分補季度，QoQ 與四季趨勢不可靠。

### Market Confirmation Spread

符合 README 公式。

### AI-RDM total

符合 README 公式：

```text
45% * 77.0 + 35% * 100.0 + 20% * 5.5 = 70.8
```

## 六、missing data 處理

目前沒有 active missing data，三個來源都是 `ok`。

程式邏輯審計：

- missing 不會被直接誤算成 0 或 100。
- 若整個 component 無 score，會沿用上一版或初始化為 50，並標記 stale。
- 但若 component 只有部分公司 missing，目前比例分母使用「成功抓到資料的公司數」，不是完整觀察名單。

這會避免把 missing 當 0，但也可能在部分 missing 時高估分數。例如 4 家 hyperscaler 只成功 2 家且都 YoY > 0，程式會算 100% positive，而不是 2/4。

建議修正：

- 若部分 missing，分數可以繼續計算，但應額外提供 confidence / coverage。
- 或者對比例項使用完整 watchlist 作為分母。
- 或者 missing 超過門檻時，不更新該子分數並沿用舊值標記 stale。

## 七、目前 70.8 分是否合理

合理，但只能說是「現有公式與目前資料處理下合理」。

支持 70.8 的因素：

- 台灣供應鏈 10 檔 YoY 全數為正，median YoY 約 31.23%，供應鏈分數 77.0 有資料支持。
- Hyperscaler latest Q1 capex YoY 四家公司全為正，median YoY 80.53%，capex 分數被推到 100。
- 市場價格確認非常弱，AI hardware basket 20D 跑輸 QQQ 約 8.90%，市場分數只有 5.5，確實拉低總分。

降低可信度的因素：

- 供應鏈三個月平均 YoY 加速尚未真正算出，目前是中性 fallback。
- SEC capex 未支援 YTD 差分，最近四季趨勢與 QoQ 不可靠。
- Capex 子分數目前沒有使用 QoQ，但 UI 與資料透明區呈現 QoQ，容易讓使用者誤以為四家公司 QoQ 都可靠。

整體判斷：

```text
AI-RDM = 70.8 作為初版監測值可以接受。
但在修正 SEC YTD 差分前，不建議把它解讀為高信心的「強擴張」結論。
更準確的說法是：供應鏈 YoY 與 hyperscaler Q1 YoY 很強，但市場價格確認偏弱，且 capex 四季趨勢仍需修正資料處理後再確認。
```

## 八、需要修正的地方

優先順序：

1. **P1：修正 SEC capex quarterly derivation**
   - 支援 YTD 差分，補出 Q2/Q3/Q4。
   - 避免 `qoq_growth_pct` 比較非相鄰季度。
   - 在 JSON 中標記 `derived_from_ytd`。

2. **P1：在 SEC 輸出保存 audit metadata**
   - 保存 `tag`、`start`、`end`、`duration_days`、`filed`、`form`。
   - 讓資料透明區可檢查單季值是直接 fact 或 YTD 差分。

3. **P2：定義 partial missing 的分母政策**
   - 目前 missing 不會變成 0 或 100，但成功樣本分母可能高估。
   - 建議新增 coverage，或 missing 過多時沿用舊值標記 stale。

4. **P2：供應鏈三個月加速初期信心標記**
   - 目前以 50 分處理是穩健 fallback，但應在分數旁標示「歷史不足」。
   - 累積至少六個月後再視為完整 Supply Chain Momentum。

5. **P3：明確標示台灣營收金額單位**
   - JSON 目前保存的是千元值。
   - 分數不受影響，但資料透明區若未來顯示金額，應標示 NTD thousand。

6. **P3：SEC tag 定義差異**
   - AMZN 使用 `PaymentsToAcquireProductiveAssets` fallback，和其他公司 `PaymentsToAcquirePropertyPlantAndEquipment` 不完全同名。
   - 可以接受作為 fallback，但應在 UI 或 JSON 中明確揭露。

## 九、最終審計評語

目前 repo 的資料管線已有良好 error handling、source status 與 stale 概念，台灣月營收與市場價格處理基本可信。

最大缺口是 SEC capex 的季度化。它沒有把 YTD 誤當單季，這是好事；但也沒有把 YTD 差分成單季，導致最近四季與 QoQ 不完整。只要補上這一點，AI-RDM 對「AI 基建實需動能」的可信度會明顯提高。
