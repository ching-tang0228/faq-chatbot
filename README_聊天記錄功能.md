# 聊天記錄管理功能說明

## 功能概述

本系統新增了完整的聊天記錄管理功能，讓您可以：
- 📊 即時記錄所有使用者對話
- 📈 分析使用者行為和常見問題
- 📄 匯出Excel報表進行深入分析
- 🔍 識別需要新增到FAQ的問題
- 🧹 自動清理舊記錄保持系統效能

## 架構設計

### 混合記錄方案

採用 **CSV即時記錄 + 資料庫分析** 的混合方案：

1. **即時記錄**：每次對話後立即寫入CSV檔案
2. **定期整理**：將CSV資料匯入資料庫進行分析
3. **統計分析**：提供多維度的統計資料
4. **Excel匯出**：生成格式化的報表

### 資料結構

#### CSV記錄格式
```csv
timestamp,user_question,bot_response,user_satisfaction,session_id,ip_address,response_source,category,processing_status
2024-01-15 14:30:25,如何申請長照服務?,長照服務申請流程如下...,未評分,session_001,192.168.1.100,FAQ資料庫,長照服務,pending
```

#### 資料庫記錄表
```sql
CREATE TABLE chat_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME,
    user_question TEXT,
    bot_response TEXT,
    user_satisfaction TEXT DEFAULT '未評分',
    session_id TEXT,
    ip_address TEXT,
    response_source TEXT,
    category TEXT,
    processing_status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 功能模組

### 1. 即時記錄模組 (`chat_logger.py`)

**主要功能：**
- 自動記錄每次對話
- 支援多執行緒安全寫入
- 包含完整的對話資訊

**使用方式：**
```python
from chat_logger import chat_logger

# 記錄對話
chat_logger.log_chat(
    user_question="使用者問題",
    bot_response="機器人回答",
    session_id="session_123",
    ip_address="192.168.1.100",
    response_source="FAQ資料庫",
    category="長照服務"
)
```

### 2. 統計分析模組

**提供的統計資料：**
- 總對話數
- FAQ命中率
- 常見問題排行
- 分類統計
- 來源統計
- 每日對話趨勢

**API端點：**
- `GET /api/logs/statistics?days=30` - 獲取統計資料

### 3. Excel匯出模組

**匯出內容：**
- 聊天記錄詳細資料
- 常見問題統計
- 分類統計
- 來源統計
- 每日統計

**API端點：**
- `POST /api/logs/export` - 匯出Excel檔案
- `GET /api/logs/download/<filename>` - 下載檔案

### 4. 資料整理模組

**功能：**
- CSV到資料庫匯入
- 舊記錄清理
- 未回答問題識別

**API端點：**
- `POST /api/logs/import` - 匯入CSV到資料庫
- `GET /api/logs/unanswered?days=7` - 獲取未回答問題
- `POST /api/logs/cleanup` - 清理舊記錄

## 後台管理介面

### 存取方式
- 網址：`/logs-admin`
- 從管理頁面點擊「聊天記錄管理」按鈕

### 功能區塊

#### 1. 統計儀表板
- 📊 總對話數、FAQ命中率、GPT回答數、活躍會話
- 📋 常見問題Top 10
- 📈 分類統計

#### 2. 資料匯出
- 📄 選擇匯出天數（7天、30天、90天、一年）
- 📥 一鍵匯出Excel檔案
- 💾 自動下載功能

#### 3. 未回答問題
- ❓ 識別重複詢問的問題
- 📅 可調整查詢時間範圍
- 💡 協助改善FAQ資料庫

#### 4. 系統維護
- 🔄 CSV到資料庫匯入
- 🗑️ 舊記錄清理
- ⚙️ 系統效能優化

## 使用流程

### 日常使用
1. **自動記錄**：系統自動記錄所有對話
2. **定期整理**：每週執行一次CSV匯入
3. **分析報表**：每月匯出Excel報表分析
4. **改善FAQ**：根據未回答問題更新資料庫

### 管理操作
1. 進入 `/logs-admin` 頁面
2. 查看統計儀表板了解使用情況
3. 匯出Excel報表進行深入分析
4. 查看未回答問題，考慮新增到FAQ
5. 定期清理舊記錄保持系統效能

## 技術特點

### 效能優化
- **即時記錄**：使用CSV檔案避免資料庫鎖定
- **批次處理**：定期匯入減少資料庫負載
- **自動清理**：定期清理舊記錄保持效能

### 資料安全
- **檔案鎖定**：多執行緒安全寫入
- **狀態追蹤**：避免重複匯入
- **備份機制**：CSV檔案作為備份

### 擴展性
- **模組化設計**：各功能獨立可擴展
- **API介面**：支援外部系統整合
- **格式標準**：支援多種匯出格式

## 測試驗證

### 執行測試
```bash
python test_logger.py
```

### 測試內容
- ✅ 聊天記錄功能
- ✅ 統計分析功能
- ✅ Excel匯出功能
- ✅ 資料整理功能
- ✅ 系統整合測試

## 部署注意事項

### 依賴套件
新增以下套件到 `requirements.txt`：
```
pandas==2.0.3
openpyxl==3.1.2
```

### 檔案權限
確保應用程式有權限：
- 讀寫CSV檔案
- 創建Excel檔案
- 存取資料庫

### 定期維護
建議設定定期任務：
- 每日：CSV匯入資料庫
- 每週：清理90天前記錄
- 每月：匯出統計報表

## 故障排除

### 常見問題

**Q: CSV檔案無法寫入？**
A: 檢查檔案權限和磁碟空間

**Q: Excel匯出失敗？**
A: 確認pandas和openpyxl套件已安裝

**Q: 統計資料不準確？**
A: 執行CSV匯入資料庫操作

**Q: 系統效能變慢？**
A: 定期清理舊記錄

### 日誌檢查
- 檢查應用程式日誌中的錯誤訊息
- 確認CSV檔案格式正確
- 驗證資料庫連線正常

## 未來擴展

### 計劃功能
- 📊 即時圖表顯示
- 🔔 異常問題警報
- 📱 行動裝置支援
- 🤖 AI輔助分析
- 🔗 外部系統整合

### 自訂需求
- 支援自訂統計維度
- 可配置的清理策略
- 多格式匯出支援
- 進階搜尋功能

---

**版本：** 1.0.0  
**更新日期：** 2024年1月  
**維護者：** 系統管理員 