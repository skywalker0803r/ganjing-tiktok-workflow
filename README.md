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
## 🚀 使用方式

### 1. 安裝環境

需要 Python 3.10+、FFmpeg，以及可執行 Chromium 的 Linux 環境。進入專案根目錄後執行：

- [x] OpenAI API 集成
python3 -m pip install -r requirements.txt
- [x] Hashtag 生成
python3 -m playwright install-deps chromium
- [x] 文案保存、失敗紀錄與資料庫遷移

若目前使用者沒有安裝系統套件的權限，請由容器管理員執行最後一行。`install-deps` 只需在環境初始化時執行一次。

### 2. 建立設定檔

```bash
cp .env.example .env
```

編輯 `.env`，至少填入：

```dotenv
GANJING_CHANNEL_URL=https://ganjingworld.com/你的公開頻道或標籤頁
OPENAI_API_KEY=你的_OpenAI_API_key
```

`.env` 只保留在本機，請勿提交或貼到公開訊息中。程式會在啟動時自動讀取專案根目錄的 `.env`；也可以改用同名 shell 環境變數。

### 3. 執行測試

執行完整測試套件：

```bash
python3 -m unittest -v
```

也可以單獨測試各模組：

```bash
- [x] Playwright 集成
### Milestone 6: 排程與主控模組 ✅ 完成
## 🚀 快速開始
python3 -m playwright install chromium
python3 test_database.py
python3 -m unittest -v test_downloader.py
```

### 4. 執行工作流程

先用 dry-run 確認下載、轉檔與文案生成流程。dry-run 不會發布到 TikTok，但仍可能呼叫 OpenAI API：

```bash
python3 src/main.py --once --dry-run
```

確認結果後，執行一次完整流程：

```bash
python3 src/main.py --once
```

首次上傳時，TikTok 瀏覽器會以非 headless 模式開啟，請依畫面完成登入與必要的人機驗證。Session 會保存於 `data/tiktok-session/`，後續執行會重用登入狀態。

不帶 `--once` 時，程式會持續執行，並依 `src/config.py` 中 `TIKTOK_UPLOAD['scheduled_times']` 的時間排程：

```bash
python3 src/main.py
```

### 5. 查看結果

- 原始下載影片：`temp/raw/`
- 直式處理影片：`temp/processed/`
- SQLite 狀態資料庫：`data/pipeline.db`
- 執行日誌：`logs/`

影片下載、處理、文案生成與上傳狀態都會寫入資料庫，已處理過的影片不會重複下載。
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
cp .env.example .env
# 編輯 .env，填入你的頻道 URL 與 API 金鑰
```

程式啟動時會自動讀取專案根目錄的 `.env`。若不使用 `.env`，也可以直接設定同名的 shell 環境變數。

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
- 資料庫狀態: `python3 -m unittest -v test_database.py`
- 環境設定: `.env` 是否存在且包含 `GANJING_CHANNEL_URL`
- Playwright 瀏覽器: `python3 -m playwright install chromium`

常見錯誤：

- `GANJING_CHANNEL_URL is not configured`: 建立 `.env` 並填入公開來源頁 URL。
- `Executable doesn't exist`: 執行 `python3 -m playwright install chromium`。
- `libatk-1.0.so.0` 或其他共享函式庫缺失：執行 `python3 -m playwright install-deps chromium`。
- `No public video player found`: 確認來源頁包含可公開播放、且你有權下載與發布的影片。

---

**最後更新**: 2026-09-02 | **版本**: v0.1.0-alpha