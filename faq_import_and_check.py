import sqlite3
import pandas as pd
import os
import re

DB_PATH = 'chatbot.db'
EXCEL_PATH = 'Cleaned_FAQ資料庫.xlsx'
UPLOADS_DIR = 'static/uploads'

# --------- 自動清空 FAQ 資料表 ---------
def clear_faq_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 直接刪除舊的 faq 資料表
    cursor.execute('DROP TABLE IF EXISTS faq;')
    # 用正確欄位重建 faq 資料表
    cursor.execute('''
        CREATE TABLE faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            answer_html TEXT,
            category TEXT DEFAULT '一般',
            keywords TEXT,
            images TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print('已重建 FAQ 資料表。')

# --------- 匯入 FAQ ---------
def import_faq_from_excel():
    df = pd.read_excel(EXCEL_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    success_count = 0
    for idx, row in df.iterrows():
        category = str(row.get('分類Category', '')).strip() or '一般'
        question = str(row.get('問題Question', '')).strip()
        answer = str(row.get('答案Answer', '')).strip()
        picture = str(row.get('圖片名稱Picture', '')).strip()
        if not question or not answer:
            print(f'第{idx+1}列缺少問題或答案，跳過')
            continue
        # 若有圖片名稱，插入 Markdown 圖片語法到答案最後
        if picture and picture.lower() != 'nan':
            pic_names = [p.strip() for p in re.split(r'[;,\n]', picture) if p.strip()]
            for pic in pic_names:
                if not os.path.splitext(pic)[1]:
                    pic += '.png'
                img_path = f'static/uploads/{pic}'
                if os.path.exists(img_path):
                    answer += f'\n\n![]({img_path})'
                else:
                    print(f'⚠️  圖片檔案不存在：{img_path}（第{idx+1}列）')
                    answer += f'\n\n![]({img_path})'  # 仍插入，方便後續檢查
        answer_html = answer
        try:
            cursor.execute('''
                INSERT INTO faq (question, answer, answer_html, category, keywords, images, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (question, answer, answer_html, category, '', '[]'))
            success_count += 1
        except Exception as e:
            print(f'第{idx+1}列匯入失敗：{e}')
    conn.commit()
    conn.close()
    print(f'\nExcel FAQ 匯入完成！共匯入 {success_count} 筆。')

# --------- 檢查 FAQ 與圖片連結 ---------
def check_faq_images():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, answer FROM faq")
    faqs = cursor.fetchall()
    upload_files = set(os.listdir(UPLOADS_DIR))
    img_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
    used_files = set()
    for faq_id, question, answer in faqs:
        for match in img_pattern.findall(answer or ''):
            if 'static/uploads/' in match or '/static/uploads/' in match:
                filename = os.path.basename(match)
                used_files.add(filename)
                if filename not in upload_files:
                    print(f'❌ FAQ ID {faq_id} 問題：「{question}」的圖片檔案 {filename} 不存在 uploads 目錄！')
    unused_files = upload_files - used_files
    if unused_files:
        print('\n⚠️  下列圖片檔案在 uploads 目錄中，但 FAQ 沒有用到：')
        for f in sorted(unused_files):
            print('  ', f)
    else:
        print('\n✅ uploads 目錄下所有圖片都有被 FAQ 使用。')
    missing_files = used_files - upload_files
    if not missing_files:
        print('\n✅ FAQ 所有圖片連結都正確指向 uploads 目錄。')
    conn.close()

# --------- 顯示 FAQ 對應圖片 ---------
def list_faq_images():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, answer FROM faq")
    faqs = cursor.fetchall()
    img_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
    print('\nFAQ 與對應圖片清單：')
    print('-' * 60)
    for faq_id, question, answer in faqs:
        images = [os.path.basename(match) for match in img_pattern.findall(answer or '') if 'static/uploads/' in match or '/static/uploads/' in match]
        print(f'FAQ ID: {faq_id}')
        print(f'問題: {question}')
        print(f'對應圖片: {images if images else "無"}')
        print('-' * 40)
    conn.close()

if __name__ == "__main__":
    print('--- FAQ 資料表清空 ---')
    clear_faq_table()
    print('--- FAQ 匯入開始 ---')
    import_faq_from_excel()
    print('\n--- FAQ 圖片連結檢查 ---')
    check_faq_images()
    print('\n--- FAQ 與圖片對應清單 ---')
    list_faq_images() 