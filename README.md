# 🎲 香港六合彩分析平台 · Mark Six Analytics

> 數據驅動的六合彩分析與可解釋AI預測系統

![Mark Six Analytics](https://img.shields.io/badge/Mark_Six-Analytics-gold?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square)
![React](https://img.shields.io/badge/React-18-cyan?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 📋 功能總覽

| 模組 | 功能 |
|------|------|
| 🕷️ 資料爬蟲 | 自動爬取 2013 年至今的六合彩開獎資料 |
| 📊 統計分析 | 頻率統計、奇偶比例、大小分布、熱力圖 |
| 🤖 AI 預測 | 3 種可解釋模型（頻率加權、趨勢分析、集成學習） |
| 🌐 前端介面 | 深色主題 Dashboard，響應式設計 |
| 🔌 API 後端 | Flask REST API，支援分頁與 CSV 匯出 |
| 🚀 部署支援 | GitHub Pages 靜態部署 + 本地開發 |

---

## 🏗️ 專案結構

```
marksix/
├── build_site.py              # 爬蟲 + 統計 + AI 預測 + 產生 index.html（主程式）
├── index.html                 # 網站（GitHub Pages），資料內嵌在 var DATA=
├── marksix_all_draws.json     # 全部歷史開獎資料
├── marksix_compact.json       # 網站用的統計與預測資料
├── requirements.txt
├── tests/
│   ├── test_build_site.py     # 規則驗證、爬蟲、合併、統計、模型邊界測試
│   └── test_frontend.js       # 前端測試（Playwright）
├── .github/workflows/
│   ├── update.yml             # 每日自動更新資料
│   └── test.yml               # push / PR 時跑測試
└── scraper.py, generate_data.py, api_server.py   # 舊版腳本，未維護（路徑指向不存在的 data/）
```

---

## 🚀 快速開始

```bash
pip install -r requirements.txt

# 更新資料並重建 index.html
#  - 已有 marksix_all_draws.json：只抓今年與去年，合併後重建；沒有新開獎就不動
#  - 沒有既有資料：從 2013 年全部抓取
python3 build_site.py

# 本機預覽
python3 -m http.server 8080
# 打開 http://localhost:8080
```

### 資料規則

每期資料必須符合六合彩規則才會被收錄（`is_valid_draw`）：

- 6 個主號碼 + 1 個特別號，都在 1–49
- 7 個號碼互不重複
- 期號格式 `YY/NNN`，且 `YY` 與開獎日期年份一致

### 執行測試

```bash
python3 -m unittest discover -s tests -v

# 前端測試（需要 Node.js）
npm install --no-save playwright && npx playwright install chromium
node tests/test_frontend.js
```

---

## 🔌 API 文檔

> ⚠️ `api_server.py` 是舊版腳本，需要 `data/marksix_data.json`（由同樣是舊版的 `generate_data.py` 產生），目前沒有維護，GitHub Pages 網站也沒有用到。

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/results` | GET | 全部歷史資料 (`?limit=N&offset=M`) |
| `/api/recent` | GET | 最近 N 期 (`?n=10`) |
| `/api/frequency` | GET | 號碼出現頻率 |
| `/api/stats` | GET | 奇偶 / 大小統計 |
| `/api/hot` | GET | 最近 20 期出現次數 |
| `/api/predict` | GET | AI 預測結果 (`?model=frequency_weighted`) |
| `/api/heatmap` | GET | 熱力圖數據 |
| `/api/gaps` | GET | 間隔分析 |
| `/api/export/csv` | GET | 匯出 CSV 檔案 |

### 範例請求

```bash
# 取得最近 5 期
curl http://localhost:5000/api/recent?n=5

# 取得特定模型預測
curl http://localhost:5000/api/predict?model=trend

# 匯出 CSV
curl http://localhost:5000/api/export/csv -o results.csv
```

---

## 🤖 AI 預測模型說明

### 模型 1：頻率加權模型 (Hot/Cold Frequency)

**策略**：3 個熱號 + 2 個中間號 + 1 個冷號

- 計算每個號碼的歷史出現頻率
- 分類為熱號（Top 1/3）、中間（Middle 1/3）、冷號（Bottom 1/3）
- 結合近 20 期頻率加權
- 確保選號覆蓋不同溫度區間

### 模型 2：近期趨勢模型 (Recent Trend)

**策略**：偏好近期上升趨勢的號碼

- 使用指數加權移動平均（EWMA）
- 比較前 10 期 vs 後 10 期出現次數
- 計算趨勢方向（上升↑ / 持平→ / 下降↓）
- 優先選擇趨勢上升且加權分數高的號碼

### 模型 3：集成學習模型 (ML Ensemble)

**策略**：多特徵綜合評分 + 平衡約束

特徵工程：
- 歷史頻率（權重 25%）
- 近期頻率（權重 35%）
- 間隔分析（權重 15%）
- 平衡獎勵（25%）

約束條件：
- 奇偶數各不超過 4 個
- 大小數各不超過 4 個

---

## 🔄 自動更新（GitHub Actions）

`.github/workflows/update.yml` 每天香港時間 22:30 執行（也可以在 Actions 頁面手動觸發）：

1. 跑單元測試
2. `python build_site.py`：抓最新開獎、合併、重建網站
3. 有變更才 commit 並 push，GitHub Pages 自動部署

| 情況 | 結果 |
|------|------|
| 有新開獎 | 更新資料與網站 ✅ |
| 沒有新開獎 | 不重建、不 commit ✅ |
| lottery.hk 暫時無回應 | 重試 3 次後保留既有資料 ✅ |
| 超過 14 天沒有新資料 | workflow 失敗 ❌，提醒檢查資料來源 |

---

## ⚠️ 免責聲明

六合彩為隨機抽獎遊戲，任何統計分析與預測**均不保證中獎**。

本系統僅供**娛樂參考與學習**用途，請理性投注。未成年人士請勿購彩。

---

## 📄 License

MIT License - 自由使用、修改與分發。
