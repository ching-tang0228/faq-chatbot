import csv
import os
import json
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from collections import Counter
import threading
import time

class ChatLogger:
    def __init__(self, csv_file='chat_logs.csv', db_file='chatbot.db'):
        self.csv_file = csv_file
        self.db_file = db_file
        self.lock = threading.Lock()
        self.ensure_csv_exists()
        self.ensure_db_table()
    
    def ensure_csv_exists(self):
        """確保CSV檔案存在並有標題行"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'user_question', 'bot_response', 
                    'user_satisfaction', 'session_id', 'ip_address',
                    'response_source', 'category', 'processing_status'
                ])
    
    def ensure_db_table(self):
        """確保資料庫中有聊天記錄表"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_logs (
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
            )
        ''')
        conn.commit()
        conn.close()
    
    def log_chat(self, user_question, bot_response, session_id, ip_address, 
                 response_source='GPT AI', category='一般對話'):
        """即時記錄聊天對話到CSV檔案"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with self.lock:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, user_question, bot_response, 
                    '未評分', session_id, ip_address,
                    response_source, category, 'pending'
                ])
    
    def import_csv_to_db(self, batch_size=100):
        """將CSV資料匯入資料庫"""
        if not os.path.exists(self.csv_file):
            return 0
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 讀取CSV檔案
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = list(reader)
        
        imported_count = 0
        
        for record in records:
            if record['processing_status'] == 'pending':
                try:
                    cursor.execute('''
                        INSERT INTO chat_logs 
                        (timestamp, user_question, bot_response, user_satisfaction, 
                         session_id, ip_address, response_source, category, processing_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        record['timestamp'], record['user_question'], record['bot_response'],
                        record['user_satisfaction'], record['session_id'], record['ip_address'],
                        record['response_source'], record['category'], 'processed'
                    ))
                    imported_count += 1
                except Exception as e:
                    print(f"匯入記錄失敗: {e}")
        
        conn.commit()
        conn.close()
        
        # 更新CSV檔案狀態
        self.update_csv_status()
        
        return imported_count
    
    def update_csv_status(self):
        """更新CSV檔案中的處理狀態"""
        temp_file = self.csv_file + '.tmp'
        
        with open(self.csv_file, 'r', encoding='utf-8') as infile, \
             open(temp_file, 'w', newline='', encoding='utf-8') as outfile:
            
            reader = csv.DictReader(infile)
            writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
            writer.writeheader()
            
            for row in reader:
                if row['processing_status'] == 'pending':
                    row['processing_status'] = 'processed'
                writer.writerow(row)
        
        os.replace(temp_file, self.csv_file)
    
    def get_statistics(self, days=30):
        """獲取統計資料"""
        conn = sqlite3.connect(self.db_file)
        
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 總對話數
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM chat_logs 
            WHERE timestamp >= ? AND timestamp <= ?
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        total_chats = cursor.fetchone()[0]
        
        # 常見問題統計
        cursor.execute('''
            SELECT user_question, COUNT(*) as count 
            FROM chat_logs 
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY user_question 
            ORDER BY count DESC 
            LIMIT 10
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        common_questions = cursor.fetchall()
        
        # 分類統計
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM chat_logs 
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY category 
            ORDER BY count DESC
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        category_stats = cursor.fetchall()
        
        # 來源統計
        cursor.execute('''
            SELECT response_source, COUNT(*) as count 
            FROM chat_logs 
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY response_source 
            ORDER BY count DESC
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        source_stats = cursor.fetchall()
        
        # 每日對話數
        cursor.execute('''
            SELECT DATE(timestamp) as date, COUNT(*) as count 
            FROM chat_logs 
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY DATE(timestamp) 
            ORDER BY date
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        daily_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_chats': total_chats,
            'common_questions': common_questions,
            'category_stats': category_stats,
            'source_stats': source_stats,
            'daily_stats': daily_stats,
            'period': f'{start_date.strftime("%Y-%m-%d")} 到 {end_date.strftime("%Y-%m-%d")}'
        }
    
    def export_to_excel(self, output_file='chat_logs_export.xlsx', days=30):
        """匯出聊天記錄到Excel檔案"""
        conn = sqlite3.connect(self.db_file)
        
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 讀取資料
        query = '''
            SELECT timestamp, user_question, bot_response, user_satisfaction,
                   session_id, ip_address, response_source, category
            FROM chat_logs 
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(
            start_date.strftime('%Y-%m-%d'), 
            end_date.strftime('%Y-%m-%d')
        ))
        
        conn.close()
        
        # 創建Excel檔案
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # 主要資料表
            df.to_excel(writer, sheet_name='聊天記錄', index=False)
            
            # 統計資料表
            stats = self.get_statistics(days)
            
            # 常見問題統計
            common_df = pd.DataFrame(stats['common_questions'], 
                                   columns=['問題', '次數'])
            common_df.to_excel(writer, sheet_name='常見問題', index=False)
            
            # 分類統計
            category_df = pd.DataFrame(stats['category_stats'], 
                                     columns=['分類', '次數'])
            category_df.to_excel(writer, sheet_name='分類統計', index=False)
            
            # 來源統計
            source_df = pd.DataFrame(stats['source_stats'], 
                                   columns=['回答來源', '次數'])
            source_df.to_excel(writer, sheet_name='來源統計', index=False)
            
            # 每日統計
            daily_df = pd.DataFrame(stats['daily_stats'], 
                                  columns=['日期', '對話數'])
            daily_df.to_excel(writer, sheet_name='每日統計', index=False)
        
        return output_file
    
    def get_unanswered_questions(self, days=7):
        """獲取可能需要新增到FAQ的問題"""
        conn = sqlite3.connect(self.db_file)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_question, COUNT(*) as count 
            FROM chat_logs 
            WHERE response_source = 'GPT AI' 
            AND timestamp >= ? AND timestamp <= ?
            GROUP BY user_question 
            HAVING count >= 2
            ORDER BY count DESC
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        
        unanswered = cursor.fetchall()
        conn.close()
        
        return unanswered
    
    def cleanup_old_records(self, days=90):
        """清理舊記錄"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            DELETE FROM chat_logs 
            WHERE timestamp < ?
        ''', (cutoff_date.strftime('%Y-%m-%d'),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count

# 全域記錄器實例
chat_logger = ChatLogger() 