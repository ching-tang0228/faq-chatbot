# 安心臥照護系統 FAQ 聊天機器人

這是一個基於 Flask 的 FAQ 聊天機器人系統，支援圖片顯示和智能問答功能。

## 功能特色

- 🤖 智能 FAQ 問答系統
- 🖼️ 支援圖片顯示和預覽
- 📱 響應式網頁設計
- 🔍 關鍵字搜尋和相關問題推薦
- 📊 管理後台介面
- 💬 聊天歷史記錄

## 技術架構

- **後端**: Flask + SQLAlchemy
- **前端**: HTML + CSS + JavaScript
- **AI**: OpenAI GPT API
- **資料庫**: SQLite (本地) / PostgreSQL (Render)

## 本地開發

1. 安裝依賴：
```bash
pip install -r requirements.txt
```

2. 設定環境變數：
建立 `.env` 檔案：
```
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_secret_key_here
```

3. 執行應用程式：
```bash
python chatbot_app.py
```

4. 開啟瀏覽器訪問：`http://localhost:5000`

## 部署到 Render

### 方法一：使用 GitHub 自動部署

1. 將程式碼推送到 GitHub
2. 在 Render 建立新的 Web Service
3. 連接您的 GitHub 儲存庫
4. 設定環境變數：
   - `OPENAI_API_KEY`: 您的 OpenAI API 金鑰
   - `SECRET_KEY`: 隨機生成的密鑰
5. 部署完成後會得到公開 URL

### 方法二：使用 render.yaml

1. 將程式碼推送到 GitHub
2. 在 Render 建立新的 Blueprint Instance
3. 選擇您的 GitHub 儲存庫
4. Render 會自動讀取 `render.yaml` 配置
5. 設定環境變數後自動部署

## 環境變數說明

- `OPENAI_API_KEY`: OpenAI API 金鑰（必需）
- `SECRET_KEY`: Flask 應用程式密鑰（必需）
- `DATABASE_URL`: 資料庫連線字串（Render 自動提供）

## 專案結構

```
├── chatbot_app.py          # 主應用程式
├── requirements.txt        # Python 依賴
├── Procfile               # Heroku 部署配置
├── render.yaml            # Render 部署配置
├── templates/             # HTML 模板
│   ├── index.html         # 主頁面
│   └── admin.html         # 管理後台
├── static/                # 靜態檔案
│   └── uploads/           # 上傳的圖片
└── picture/               # 預設圖片
```

## 注意事項

- 確保 OpenAI API 金鑰有效且有足夠的額度
- 圖片上傳大小限制為 16MB
- 建議在生產環境中使用 HTTPS
- 定期備份資料庫資料

## 授權

本專案僅供學習和研究使用。 #   f a q - c h a t b o t 
 
 #   f a q - c h a t b o t  
 