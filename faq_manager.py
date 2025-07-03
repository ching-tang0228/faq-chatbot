import sqlite3
import os
from datetime import datetime
import re

class FAQManager:
    def __init__(self, db_path='chatbot.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化資料庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 建立FAQ表格
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category TEXT DEFAULT '一般',
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_faq(self, question, answer, category='一般', keywords=None):
        """新增FAQ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO faq (question, answer, category, keywords)
            VALUES (?, ?, ?, ?)
        ''', (question, answer, category, keywords))
        
        conn.commit()
        conn.close()
        return cursor.lastrowid
    
    def get_all_faqs(self):
        """獲取所有FAQ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM faq ORDER BY category, id')
        faqs = cursor.fetchall()
        
        conn.close()
        return faqs
    
    def search_faq(self, query):
        """搜尋FAQ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 使用LIKE進行模糊搜尋
        cursor.execute('''
            SELECT * FROM faq 
            WHERE question LIKE ? OR answer LIKE ? OR keywords LIKE ?
            ORDER BY id
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        faqs = cursor.fetchall()
        conn.close()
        return faqs
    
    def delete_faq(self, faq_id):
        """刪除FAQ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM faq WHERE id = ?', (faq_id,))
        conn.commit()
        conn.close()
    
    def import_from_text(self, text_content):
        """從文字內容匯入FAQ"""
        # 簡單的解析邏輯，可以根據您的文件格式調整
        lines = text_content.split('\n')
        current_question = None
        current_answer = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 假設問題以數字開頭或包含"問："、"Q："等標記
            if re.match(r'^\d+\.', line) or '問：' in line or 'Q：' in line or 'Q.' in line:
                # 儲存前一個FAQ
                if current_question and current_answer:
                    self.add_faq(current_question, '\n'.join(current_answer))
                
                # 開始新的FAQ
                current_question = line
                current_answer = []
            elif current_question:
                # 這是答案的一部分
                current_answer.append(line)
        
        # 儲存最後一個FAQ
        if current_question and current_answer:
            self.add_faq(current_question, '\n'.join(current_answer))
    
    def export_faqs(self):
        """匯出FAQ為文字格式"""
        faqs = self.get_all_faqs()
        output = []
        
        for faq in faqs:
            output.append(f"問題：{faq[1]}")
            output.append(f"答案：{faq[2]}")
            output.append(f"分類：{faq[3]}")
            output.append("-" * 50)
        
        return '\n'.join(output)

def main():
    """主程式 - FAQ管理工具"""
    manager = FAQManager()
    
    print("=== FAQ 管理工具 ===")
    print("1. 新增FAQ")
    print("2. 查看所有FAQ")
    print("3. 搜尋FAQ")
    print("4. 刪除FAQ")
    print("5. 從文字匯入FAQ")
    print("6. 匯出FAQ")
    print("0. 退出")
    
    while True:
        choice = input("\n請選擇操作 (0-6): ").strip()
        
        if choice == '0':
            print("再見！")
            break
        
        elif choice == '1':
            question = input("請輸入問題: ").strip()
            answer = input("請輸入答案: ").strip()
            category = input("請輸入分類 (預設: 一般): ").strip() or '一般'
            keywords = input("請輸入關鍵字 (可選): ").strip() or None
            
            faq_id = manager.add_faq(question, answer, category, keywords)
            print(f"FAQ已新增，ID: {faq_id}")
        
        elif choice == '2':
            faqs = manager.get_all_faqs()
            if not faqs:
                print("目前沒有FAQ")
            else:
                print("\n=== 所有FAQ ===")
                for faq in faqs:
                    print(f"ID: {faq[0]}")
                    print(f"問題: {faq[1]}")
                    print(f"答案: {faq[2]}")
                    print(f"分類: {faq[3]}")
                    print("-" * 30)
        
        elif choice == '3':
            query = input("請輸入搜尋關鍵字: ").strip()
            faqs = manager.search_faq(query)
            if not faqs:
                print("沒有找到相關FAQ")
            else:
                print(f"\n找到 {len(faqs)} 個相關FAQ:")
                for faq in faqs:
                    print(f"ID: {faq[0]}")
                    print(f"問題: {faq[1]}")
                    print(f"答案: {faq[2]}")
                    print("-" * 30)
        
        elif choice == '4':
            faq_id = input("請輸入要刪除的FAQ ID: ").strip()
            try:
                manager.delete_faq(int(faq_id))
                print("FAQ已刪除")
            except ValueError:
                print("無效的ID")
        
        elif choice == '5':
            print("請將您的FAQ文件內容貼上 (按Enter兩次結束):")
            lines = []
            while True:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
            
            text_content = '\n'.join(lines[:-1])  # 移除最後的空行
            manager.import_from_text(text_content)
            print("FAQ已匯入")
        
        elif choice == '6':
            content = manager.export_faqs()
            print("\n=== 匯出的FAQ ===")
            print(content)
        
        else:
            print("無效的選擇")

if __name__ == "__main__":
    main() 