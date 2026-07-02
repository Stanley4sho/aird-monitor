# AI-RDM Monitor：00988A AI 基建實需動能監測器

一個完全免費、可部署到 GitHub Pages 的 React + Vite + TypeScript PWA。  
它不是股價看板，而是用公開資料自動更新自創指標：

**AI Infrastructure Real-Demand Momentum Index，AI-RDM，AI 基建實需動能指數。**

AI-RDM 以 0 到 100 分衡量 AI 基礎建設真實需求動能：

- 70-100：強擴張
- 55-69：溫和擴張
- 45-54：中性震盪
- 30-44：放緩
- 0-29：明顯轉弱

> 本專案僅供研究與教育用途，不構成任何投資建議、買賣建議或績效保證。

## 技術架構

- 前端：React + Vite + TypeScript
- 圖表：Recharts
- CSS：Tailwind CSS
- PWA：manifest + service worker + iPhone icon
- 資料抓取：Python scripts
- 排程：GitHub Actions
- 儲存：`public/data/*.json`
- 部署：GitHub Pages
- API key：不需要
- 付費服務：不使用
- 雲端資料庫：不使用

## 專案結構

```text
src/
  components/
  charts/
  utils/
scripts/
  fetch_tw_revenue.py
  fetch_sec_capex.py
  fetch_market_prices.py
  compute_airdm.py
  update_data.py
public/data/
  latest.json
  history.json
  source_status.json
  raw/
.github/workflows/update-data.yml
README.md
requirements.txt
package.json
```

## AI-RDM 公式

```text
AI-RDM =
45% * Supply Chain Revenue Momentum
+ 35% * Hyperscaler Capex Momentum
+ 20% * Market Confirmation Spread
```

### A. Supply Chain Revenue Momentum，權重 45%

觀察名單：

- 3037.TW 欣興
- 2383.TW 台光電
- 2454.TW 聯發科
- 2330.TW 台積電
- 6669.TW 緯穎
- 3711.TW 日月光投控
- 2308.TW 台達電
- 2345.TW 智邦
- 2376.TW 技嘉
- 2356.TW 英業達

資料來源：

- 台灣上市公司月營收開放資料
- `https://mopsfin.twse.com.tw/opendata/t187ap05_L.csv`
- Python 端抓取，處理 UTF-8 / Big5 / CP950 fallback
- 原始快照保存在 `public/data/raw/tw_revenue_latest.csv`

計算方式：

```text
Supply Chain Revenue Momentum =
40% * 觀察名單中 YoY > 0 的公司比例
+ 30% * 觀察名單中 3-month average YoY 加速的公司比例
+ 30% * median YoY growth 標準化分數
```

median YoY 標準化：

- median YoY <= -20%：0 分
- median YoY >= +50%：100 分
- 中間線性換算

注意：台灣開放資料 endpoint 主要提供最新月份。`history.json` 會累積每次更新的月營收觀測值，用來計算三個月平均 YoY 與加速。若剛初始化、尚未累積至少六個月觀測，三個月平均 YoY 加速項暫以中性 50 分處理，並在資料透明區標記。

### B. Hyperscaler Capex Momentum，權重 35%

觀察名單：

- Microsoft，MSFT
- Alphabet，GOOGL
- Meta，META
- Amazon，AMZN

資料來源：

- SEC EDGAR / XBRL，不使用 API key
- `https://data.sec.gov/submissions/CIK##########.json`
- `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`

XBRL tag 優先序：

1. `PaymentsToAcquirePropertyPlantAndEquipment`
2. `CapitalExpenditures`
3. `PropertyPlantAndEquipmentAdditions`
4. fallback：`PaymentsToAcquireProductiveAssets`

SEC 要求 User-Agent。workflow 預設：

```text
ai-rdm-monitor contact example@example.com
```

你可以在 workflow 裡把 `SEC_USER_AGENT` 改成自己的 repo 名稱與聯絡信箱。

計算方式：

```text
Hyperscaler Capex Momentum =
50% * 四家公司 capex YoY growth 的 median 標準化分數
+ 30% * 四家公司中 capex YoY > 0 的比例
+ 20% * 最新 10-Q / 10-K 是否出現 AI infrastructure、datacenter、capex、capacity expansion 等關鍵字的比例
```

median capex YoY 標準化：

- median capex YoY <= -10%：0 分
- median capex YoY >= +40%：100 分
- 中間線性換算

如果某家公司無法可靠抓到 capex，會標示為 `missing` 或 `partial`，不會亂補數字。

### C. Market Confirmation Spread，權重 20%

AI hardware basket：

- NVDA
- AMD
- AVGO
- MU
- TSM
- ASML
- ANET
- VRT
- SMCI
- LITE

Benchmark：

- QQQ

資料來源優先序：

1. Stooq CSV
2. Yahoo Finance unofficial chart endpoint
3. Nasdaq historical endpoint fallback

計算方式：

```text
Spread =
AI hardware basket 過去 20 trading days 等權平均報酬率
- QQQ 過去 20 trading days 報酬率
```

標準化：

- Spread >= +10%：100 分
- Spread <= -10%：0 分
- 中間線性換算

市場價格只佔 20%，用來確認產業鏈是否同步反映需求，不取代基本面。

## 警示規則

### Slowdown Warning

```text
AI-RDM < 45
且 Supply Chain Revenue Momentum < 50
且 Hyperscaler Capex Momentum < 50
```

顯示：

```text
AI 基建實需放緩風險升高
```

### Bubble Divergence Warning

```text
Market Confirmation Spread > 70
且 Supply Chain Revenue Momentum 與 Hyperscaler Capex Momentum 的平均 < 50
```

顯示：

```text
市場價格強，但基本面跟不上，泡沫化風險升高
```

## 本機開發

```bash
npm install
python3 -m venv work/.venv
work/.venv/bin/pip install -r requirements.txt
work/.venv/bin/python scripts/update_data.py
npm run dev
```

Production build：

```bash
npm run build
```

## 資料更新

完整更新：

```bash
python scripts/update_data.py
```

只更新市場價格 proxy：

```bash
UPDATE_MODE=market python scripts/update_data.py
```

輸出檔案：

- `public/data/latest.json`：最新 AI-RDM 分數與明細
- `public/data/history.json`：趨勢圖與台灣月營收累積觀測值
- `public/data/source_status.json`：資料源狀態、missing 名單、原始快照位置

更新策略：

- 抓取失敗不會清空舊資料
- 單一公司 missing 不會讓整體流程失敗
- 若某資料源失敗，會沿用上一版分數並標示 `stale`
- 若完全沒有舊資料，才會以中性 50 分作為初始化 fallback

## GitHub Actions

workflow：`.github/workflows/update-data.yml`

排程：

- 每天台北時間 07:30 完整更新一次
- 美股開盤期間，工作日 UTC 14:30 到 21:30 每小時嘗試市場價格 proxy 更新
- 支援手動觸發 `workflow_dispatch`

commit message：

```text
data: update AI-RDM YYYY-MM-DD HH:mm UTC
```

## 建立 GitHub repo

1. 到 GitHub 建立新 repository，例如 `ai-rdm-monitor`。
2. 在本機專案目錄初始化並推送：

```bash
git init
git add .
git commit -m "feat: create AI-RDM Monitor"
git branch -M main
git remote add origin https://github.com/<你的帳號>/ai-rdm-monitor.git
git push -u origin main
```

## 啟用 GitHub Pages

1. 進入 repo 的 `Settings`。
2. 左側選 `Pages`。
3. `Build and deployment` 的 `Source` 選 `GitHub Actions`。
4. 儲存設定。

workflow 會在每次更新後執行 `npm run build`，並把 `dist/` 部署到 GitHub Pages。

## 啟用 GitHub Actions 寫入權限

1. 進入 repo 的 `Settings`。
2. 左側選 `Actions` -> `General`。
3. 找到 `Workflow permissions`。
4. 選 `Read and write permissions`。
5. 勾選 `Allow GitHub Actions to create and approve pull requests` 不是必要，但可以開。
6. 按 `Save`。

## 手動執行第一次資料更新

1. 進入 repo 的 `Actions`。
2. 選 `Update AI-RDM data and deploy`。
3. 按 `Run workflow`。
4. `mode` 選 `full`。
5. 等 workflow 完成。
6. 回到 `Settings` -> `Pages` 查看網站 URL。

第一次完整更新後，`public/data/latest.json`、`history.json`、`source_status.json` 會被 commit 回 repo。

## 加入 iPhone 主畫面

1. 用 iPhone Safari 開啟 GitHub Pages 網站。
2. 按底部分享按鈕。
3. 選 `加入主畫面`。
4. 名稱可保留 `AI-RDM`。
5. 按 `新增`。

加入後會以 PWA 方式開啟，資料仍由 GitHub Pages 的 JSON 檔更新。

## 常見問題

### 為什麼不是即時股價？

AI-RDM 的目標是監測 AI 基建真實需求，不是做交易終端。價格只佔 20%，主要用來觀察市場是否確認或偏離基本面。

### 為什麼台灣月營收的三個月加速初期可能是中性？

公開 endpoint 提供最新月份；專案會在 `history.json` 累積後續月份。累積至少六個月後，才可可靠比較最近三個月 YoY 平均是否高於前三個月。

### 資料來源失敗怎麼辦？

網站會顯示上一版資料，並在資料透明區標示 `stale`、`partial` 或 `error`。workflow 不會因單一 ticker 或單一公司失敗就清空資料。
