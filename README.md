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
marksix-project/
├── public/
│   └── index.html          # 完整前端 (React + Chart.js)
├── scripts/
│   ├── scraper.py          # 資料爬蟲 (lottery.hk)
│   ├── generate_data.py    # 統計計算 + AI 預測
│   └── api_server.py       # Flask API 後端
├── data/
│   ├── marksix_data.json   # 完整資料 (含所有統計)
│   └── compact_data.json   # 前端嵌入用精簡版
└── README.md
```

---

## 🚀 快速開始

### 方法 A：直接使用（靜態版本）

前端已內嵌資料，直接開啟即可使用：

```bash
# 1. 直接打開前端
open public/index.html
# 或用任何 HTTP 伺服器
python3 -m http.server 8080 --directory public/
# 然後打開 http://localhost:8080
```

### 方法 B：完整本地開發

```bash
# 1. 安裝 Python 依賴
pip install requests beautifulsoup4 flask flask-cors

# 2. 爬取最新資料（需要網路）
python3 scripts/scraper.py

# 3. 生成統計與預測
python3 scripts/generate_data.py

# 4. 啟動 API 伺服器
python3 scripts/api_server.py
# API 運行在 http://localhost:5000

# 5. 開啟前端
open public/index.html
```

---

## 🔌 API 文檔

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

## 🚀 部署到 GitHub Pages

```bash
# 1. 建立 GitHub 倉庫
git init
git remote add origin https://github.com/YOUR_USERNAME/marksix-analysis.git

# 2. 複製 public/index.html 到根目錄
cp public/index.html ./index.html

# 3. 推送
git add .
git commit -m "Initial commit: Mark Six Analytics Platform"
git push -u origin main

# 4. 啟用 GitHub Pages
#    Settings → Pages → Source: Deploy from branch → main → / (root)

# 5. 訪問
#    https://YOUR_USERNAME.github.io/marksix-analysis/
```

---

## 🔄 自動更新（Cron Job）

建立 `update.sh`：

```bash
#!/bin/bash
cd /path/to/marksix-project
python3 scripts/scraper.py --update
python3 scripts/generate_data.py
# 可選：自動推送
git add data/
git commit -m "Auto update: $(date +%Y-%m-%d)"
git push
```

加入 crontab（每天晚上 10:30 更新）：

```bash
crontab -e
# 加入：
30 22 * * * /path/to/update.sh >> /path/to/update.log 2>&1
```

---

## ⚠️ 免責聲明

六合彩為隨機抽獎遊戲，任何統計分析與預測**均不保證中獎**。

本系統僅供**娛樂參考與學習**用途，請理性投注。未成年人士請勿購彩。

---

## 📄 License

MIT License - 自由使用、修改與分發。
