# 乾淨世界 to TikTok 自動化搬運流程 (Ganjing to TikTok Pipeline)

## 📋 專案概述

本項目是一套全自動化的影片搬運與發布系統，自動監控「乾淨世界」指定頻道，自動下載最新影片、進行格式裁切與剪輯優化、利用 AI 生成熱門標題與標籤，並透過自動化腳本排程發布至 TikTok，全程無須人工干預。

## 🏗️ 系統架構

```
Ganjing World Source → Download → Video Processing → AI Content Generation → TikTok Upload
 (Playwright, HTTP)      (MP4)      (FFmpeg, 9:16)     (GPT-4o-mini)         (Playwright)
```

## 📦 項目結構

```
ganjing-tiktok-workflow/
├── src/                          # 核心源代碼
│   ├── __init__.py
│   ├── config.py                 # 配置文件
│   ├── database.py               # 資料庫模組 ✅
│   ├── downloader.py             # 影片下載模組 ✅
│   ├── video_processor.py        # 影片處理模組 ✅
│   ├── content_generator.py      # 文案生成模組 ✅
│   ├── uploader.py               # 自動發布模組 ✅
│   └── main.py                   # 主控與排程程序 ✅
├── temp/
│   ├── raw/                      # 原始下載影片
│   └── processed/                # 已處理影片
├── data/
│   └── pipeline.db               # SQLite 資料庫
├── logs/                         # 執行日誌
├── config/                       # 配置文件目錄
├── test_database.py              # 資料庫測試 ✅
├── test_downloader.py            # 下載器測試 ✅
├── test_video_processor.py       # 影片處理測試 ✅
├── test_content_generator.py     # 文案生成測試 ✅
├── test_uploader.py              # TikTok 上傳器測試 ✅
├── test_main.py                  # 主控與排程測試 ✅
├── requirements.txt              # Python 依賴
└── README.md

## ✅ 開發進度

### Milestone 1: 資料庫與歷史記錄模組 ✅ 完成
- [x] SQLite 資料庫架構設計
- [x] 影片記錄表 (videos)
- [x] 處理日誌表 (processing_logs)
- [x] 基本 CRUD 操作
- [x] 狀態追蹤功能
- [x] 統計查詢功能
- [x] 單元測試通過

### Milestone 2: 影片監控與下載模組 ✅ 完成
- [x] Playwright 公開影片來源解析
- [x] 頻道監控邏輯
- [x] 自動下載功能
- [x] 重複檢查機制
- [x] 影片時長篩選與下載失敗紀錄

### Milestone 3: 自動剪輯與格式轉化模組 ✅ 完成
- [x] FFmpeg 集成
- [x] 9:16 豎屏轉換
- [x] 背景模糊襯底
- [x] 轉檔失敗紀錄與狀態追蹤

### Milestone 4: 文案與標籤自動生成模組 ✅ 完成
- [x] OpenAI API 集成
- [x] 標題生成
- [x] Hashtag 生成
- [x] 文案保存、失敗紀錄與資料庫遷移

### Milestone 5: TikTok 自動發布模組 ✅ 完成
- [x] Playwright 集成
- [x] 持久化 Session 管理
- [x] 自動發布邏輯
- [x] 每日發布上限與 CAPTCHA 偵測暫停

### Milestone 6: 排程與主控模組 ✅ 完成
- [x] 定時任務排程
- [x] 工作流程整合
- [x] 執行摘要與錯誤日誌

## 🚀 快速開始

### 安裝依賴
```bash
pip install -r requirements.txt
python3 -m playwright install chromium
```

### 運行資料庫測試
```bash
python3 test_database.py
```

### 運行下載器測試
```bash
python3 -m unittest -v test_downloader.py
```

### 運行影片處理器測試
```bash
python3 -m unittest -v test_video_processor.py
```

### 運行文案生成器測試
```bash
python3 -m unittest -v test_content_generator.py
```

### 運行 TikTok 上傳器測試
```bash
python3 -m unittest -v test_uploader.py
```

### 運行主控與排程測試
```bash
python3 -m unittest -v test_main.py
```

### 執行工作流程
```bash
python3 src/main.py --once
```

### 執行 dry run
```bash
python3 src/main.py --once --dry-run
```

不帶 `--once` 時，程式會依 `TIKTOK_UPLOAD['scheduled_times']` 定時執行。

## ⚙️ 配置

設定以下環境變數與參數：

- `GANJING_CHANNEL_URL`: 乾淨世界頻道 URL
- `OPENAI_API_KEY`: OpenAI API 密鑰
- `TIKTOK_UPLOAD`: TikTok 上傳配置
- `NOTIFICATION`: 通知設置 (Telegram/LINE)

```bash
export GANJING_CHANNEL_URL="https://ganjingworld.com/channel/你的頻道"
export OPENAI_API_KEY="你的金鑰"
```

下載器透過瀏覽器讀取 `GANJING_CHANNEL_URL` 頁面中連向 `/video/` 的公開影片頁，並下載其公開、無 DRM 的 MP4 媒體 URL。來源頁的影片連結與播放器 selector 可在 `GANJING_DOWNLOAD` 調整。僅處理你有權下載、轉製及發布的內容；不會繞過登入、付費牆、CAPTCHA 或 DRM。

## 📝 技術棧

| 模組 | 技術 | 用途 |
|------|------|------|
| 核心語言 | Python 3.10+ | 主要邏輯編寫與排程控管 |
| 影片下載 | Playwright/requests | 讀取公開影片頁並串流下載 MP4 |
| 影片處理 | FFmpeg/moviepy | 轉碼、轉 9:16 豎屏、背景模糊襯底 |
| 文案生成 | OpenAI API | 自動生成爆款標題與相關 Hashtags |
| 自動上傳 | Playwright | 模擬真實瀏覽器上傳至 TikTok |
| 狀態紀錄 | SQLite3 | 防止重複下載與記錄執行 Log |

## ⚠️ 風控與防封號規範

1. **發布頻率**: 單一帳號每日自動發布不超過 2~3 支影片
2. **IP 穩定度**: 需搭配住宅代理 IP，避免使用機房 IP
3. **人機驗證**: CAPTCHA 出現時自動暫停並發送通知

## 📞 支持

遇到問題請檢查：
- 日誌文件: `logs/` 目錄
- 資料庫狀態: `python3 test_database.py`
- 配置設置: `src/config.py`

---

**最後更新**: 2026-09-02 | **版本**: v0.1.0-alpha