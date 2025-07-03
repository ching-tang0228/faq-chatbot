from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
import re
import markdown
from werkzeug.utils import secure_filename
import heapq

# 載入環境變數
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
# 檢查是否在 Render 環境中
if os.getenv('RENDER'):
    # Render 環境使用 PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///chatbot.db'
else:
    # 本地環境使用 SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 確保上傳資料夾存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化資料庫
db = SQLAlchemy(app)
CORS(app)

# 設定OpenAI API - 舊版寫法
openai_api_key = os.getenv('OPENAI_API_KEY')
client = openai.OpenAI(api_key=openai_api_key)

# 資料庫模型
class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    answer_html = db.Column(db.Text)  # 儲存HTML格式的答案
    category = db.Column(db.String(100), nullable=False)
    keywords = db.Column(db.Text)
    images = db.Column(db.Text)  # 儲存圖片路徑，JSON格式
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    bot_response_html = db.Column(db.Text)  # 儲存HTML格式的回應
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# 創建資料庫表格
with app.app_context():
    db.create_all()

def convert_markdown_to_html(markdown_text):
    """將Markdown轉換為HTML"""
    try:
        # 設定Markdown擴展
        md = markdown.Markdown(extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.codehilite',
            'markdown.extensions.nl2br'
        ])
        return md.convert(markdown_text)
    except:
        return markdown_text

def get_all_faqs_for_gpt():
    """獲取所有FAQ資料，格式化為GPT可理解的格式"""
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, question, answer, answer_html, category, keywords, images
        FROM faq
        ORDER BY id
    ''')
    faqs = cursor.fetchall()
    conn.close()
    if not faqs:
        return "目前沒有FAQ資料。"
    faq_text = "==== FAQ清單開始 ====" + "\n"
    for faq in faqs:
        faq_id, question, answer, answer_html, category, keywords, images = faq
        faq_text += f"---\nFAQ #{faq_id}\n分類：{category}\n問題：{question}\n答案：{answer}\n"
        if keywords:
            faq_text += f"關鍵字：{keywords}\n"
        if images:
            try:
                image_list = json.loads(images)
                faq_text += f"相關圖片：{', '.join(image_list)}\n"
            except:
                pass
    faq_text += "==== FAQ清單結束 ====" + "\n"
    return faq_text

def retrieve_top_faqs(user_question, top_n=5):
    """根據關鍵字從 FAQ 資料庫挑出最相關的 top_n 條 FAQ"""
    clean_question = re.sub(r'[^\w\s]', '', user_question.lower())
    keywords = clean_question.split()
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT id, question, answer, answer_html, category, keywords, images FROM faq''')
    faqs = cursor.fetchall()
    conn.close()
    scored_faqs = []
    for faq in faqs:
        score = 0
        faq_question = (faq[1] or '').lower()
        faq_keywords = (faq[5] or '').lower()
        faq_answer = (faq[2] or '').lower()
        for keyword in keywords:
            if keyword in faq_question:
                score += 2
            if keyword in faq_keywords:
                score += 1
            if keyword in faq_answer:
                score += 0.5
        if user_question.lower() in faq_question:
            score += 5
        if score > 0:
            scored_faqs.append((score, faq))
    # 取分數最高的 top_n 條
    top_faqs = heapq.nlargest(top_n, scored_faqs, key=lambda x: x[0])
    return [faq for score, faq in top_faqs]

def smart_search_faq(user_question):
    """本地比對命中直接回傳 FAQ 答案，否則才用 GPT"""
    try:
        # 先本地檢索最相關的 5 條 FAQ
        top_faqs = retrieve_top_faqs(user_question, top_n=5)
        # 設定一個分數門檻，完全包含關鍵詞或高分就直接回傳
        if top_faqs:
            # 重新計算分數，找出最相關那一條
            best_faq = None
            best_score = 0
            clean_question = re.sub(r'[^\w\s]', '', user_question.lower())
            keywords = clean_question.split()
            for faq in top_faqs:
                score = 0
                faq_question = (faq[1] or '').lower()
                faq_keywords = (faq[5] or '').lower()
                faq_answer = (faq[2] or '').lower()
                for keyword in keywords:
                    if keyword in faq_question:
                        score += 2
                    if keyword in faq_keywords:
                        score += 1
                    if keyword in faq_answer:
                        score += 0.5
                if user_question.lower() in faq_question:
                    score += 5
                if score > best_score:
                    best_score = score
                    best_faq = faq
            # 如果分數超過門檻（如4分），直接回傳 FAQ 答案
            if best_score >= 4:
                return {
                    'type': 'faq_response',
                    'answer': best_faq[2],
                    'answer_html': convert_markdown_to_html(best_faq[2]),
                    'source': 'FAQ資料庫',
                    'category': best_faq[4]
                }
        # 沒有本地命中，才丟給 GPT
        return {
            'type': 'general_conversation',
            'answer': get_gpt_response(user_question),
            'answer_html': convert_markdown_to_html(get_gpt_response(user_question)),
            'source': 'GPT AI',
            'category': '一般對話'
        }
    except Exception as e:
        print(f"FAQ本地比對/GPT分析錯誤: {str(e)}")
        return fallback_keyword_search(user_question)

def fallback_keyword_search(user_question):
    """回退方案：使用關鍵字搜尋"""
    # 原本的 smart_search_faq 邏輯
    clean_question = re.sub(r'[^\w\s]', '', user_question.lower())
    keywords = clean_question.split()
    
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, question, answer, answer_html, category, keywords, images
        FROM faq
        WHERE question LIKE ? OR answer LIKE ? OR keywords LIKE ?
    ''', (f'%{user_question}%', f'%{user_question}%', f'%{user_question}%'))
    
    faqs = cursor.fetchall()
    conn.close()
    
    if not faqs:
        return None
    
    best_match = None
    best_score = 0
    
    for faq in faqs:
        score = 0
        faq_question = re.sub(r'[^\w\s]', '', faq[1].lower())
        faq_keywords = faq[5] or ""
        
        for keyword in keywords:
            if keyword in faq_question:
                score += 2
            if keyword in faq_keywords.lower():
                score += 1
            if keyword in faq[2].lower():
                score += 0.5
        
        if user_question.lower() in faq[1].lower():
            score += 5
        
        if score > best_score:
            best_score = score
            best_match = faq
    
    return best_match if best_score >= 1 else None

def get_gpt_response(user_message, context=""):
    """使用GPT API獲取回應 - 舊版openai 0.28.0寫法"""
    try:
        system_prompt = f"""你是一個親切且樂於助人的客服AI。你的任務是：
1. 盡量幫助用戶解答所有問題，即使不在FAQ資料庫範圍，也請用你的知識、推理、創意、常識來協助解決。
2. 不要拒絕回答，也不要請用戶去用其他工具查詢。
3. 如果你不知道正確答案，也可以推測、解釋、給出建議或創意回應。
4. 保持禮貌、專業、溫暖，像ChatGPT一樣。

{context}

請用繁體中文回應，保持簡潔明瞭。"""

        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"抱歉，我目前無法處理您的請求。錯誤：{str(e)}"

def is_faq_related(user_message):
    system_prompt = "你是一個分類助手，請判斷下列問題是否屬於照護系統FAQ主題（如產品功能、使用說明、照護服務、提醒、圖表解讀等）。只需回答『相關』或『不相關』。"
    response = client.chat.completions.create(
        model="gpt-4.1-mini-2025-04-14",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    result = response['choices'][0]['message']['content'].strip()
    return result

@app.route('/')
def index():
    """主頁面"""
    return render_template('index.html')

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """提供上傳的圖片檔案"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': '請輸入訊息'}), 400
        if 'session_id' not in session:
            session['session_id'] = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = session['session_id']

        # 直接讓 GPT 做 FAQ 分類與比對
        faq_match = gpt_faq_search(user_message)

        if faq_match:
            bot_response = faq_match['answer']
            bot_response_html = faq_match['answer_html']
            response_source = faq_match['source']
            category = faq_match['category']
            images = None
            related_options = faq_match.get('related_options', [])
        else:
            bot_response = "抱歉，AI 回答失敗。"
            bot_response_html = bot_response
            response_source = "GPT AI"
            category = "一般對話"
            images = None
            related_options = []

        # 儲存聊天記錄
        chat_record = ChatHistory(
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response,
            bot_response_html=bot_response_html
        )
        db.session.add(chat_record)
        db.session.commit()

        return jsonify({
            'response': bot_response,
            'response_html': bot_response_html,
            'source': response_source,
            'category': category,
            'images': images,
            'related_options': related_options,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print('API /api/chat 發生錯誤:', e)
        import traceback
        traceback.print_exc()
        return jsonify({'error': '抱歉，連線發生錯誤，請稍後再試。'}), 500

@app.route('/api/faq', methods=['GET'])
def get_faqs():
    """獲取所有FAQ"""
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, question, answer, category FROM faq ORDER BY category, id')
    faqs = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'id': faq[0],
        'question': faq[1],
        'answer': faq[2],
        'category': faq[3]
    } for faq in faqs])

@app.route('/api/faq', methods=['POST'])
def add_faq():
    """添加新的FAQ"""
    data = request.get_json()
    
    # 轉換Markdown為HTML
    answer_html = convert_markdown_to_html(data['answer'])
    
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO faq (question, answer, answer_html, category, keywords, images)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data['question'],
        data['answer'],
        answer_html,
        data.get('category', '一般'),
        data.get('keywords', ''),
        data.get('images', '[]')
    ))
    
    conn.commit()
    faq_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'message': 'FAQ添加成功', 'id': faq_id})

@app.route('/api/faq/<int:faq_id>', methods=['DELETE'])
def delete_faq(faq_id):
    """刪除FAQ"""
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM faq WHERE id = ?', (faq_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'FAQ刪除成功'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上傳圖片檔案"""
    if 'file' not in request.files:
        return jsonify({'error': '沒有檔案'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '沒有選擇檔案'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        # 確保檔名唯一
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            filename = f"{base}_{counter}{ext}"
            counter += 1
        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({
            'filename': filename,
            'url': f'/static/uploads/{filename}'
        })

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """獲取聊天記錄"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify([])
    
    history = ChatHistory.query.filter_by(session_id=session_id).order_by(ChatHistory.timestamp).all()
    return jsonify([{
        'user_message': record.user_message,
        'bot_response': record.bot_response,
        'bot_response_html': record.bot_response_html,
        'timestamp': record.timestamp.isoformat()
    } for record in history])

@app.route('/admin')
def admin():
    """管理介面"""
    return render_template('admin.html')

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat_history():
    try:
        if 'session_id' in session:
            session_id = session['session_id']
            conn = sqlite3.connect('chatbot.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_history WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
        return jsonify({'message': '聊天紀錄已清空'})
    except Exception as e:
        print('API /api/chat/clear 發生錯誤:', e)
        return jsonify({'error': '清空失敗'}), 500

# 新增：比對用正規化函式

def normalize(text):
    return str(text).replace(' ', '').replace('　', '').replace('\n', '').strip()

# 新增：GPT FAQ 查詢主流程

def gpt_faq_search(user_question):
    """先本地完全一致比對 FAQ 條目，命中直接回傳，否則才丟給 GPT。"""
    # 取得所有 FAQ 條目
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT id, category, question, answer, images FROM faq ORDER BY category, id''')
    faqs = cursor.fetchall()
    conn.close()

    # 先本地完全一致比對（加強：去除空白、全形空白、換行、前後空格）
    for faq in faqs:
        if normalize(user_question) == normalize(faq[2]):
            # 完全一致，直接回傳
            answer = faq[3]
            answer_html = convert_markdown_to_html(answer)
            images = json.loads(faq[4]) if faq[4] else []
            if images and isinstance(images, list):
                for img in images:
                    if not any(img.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                        img_file = f"{img}.png"
                    else:
                        img_file = img
                    md_img = f'![](static/uploads/{img_file})'
                    html_img = f'<br><img src=\"static/uploads/{img_file}\" style=\"max-width:300px;\">'
                    answer += f'\n\n{md_img}'
                    answer_html += html_img
            
            # 生成相關選項
            related_options = generate_related_options(user_question, faqs, faq[1], faq[2])
            
            return {
                'type': 'faq_response',
                'answer': answer,
                'answer_html': answer_html,
                'source': 'FAQ資料庫',
                'category': faq[1],
                'related_options': related_options
            }

    # 沒有完全一致才丟給 GPT
    # 組合 FAQ 條目為 prompt
    faq_list = []
    for faq in faqs:
        faq_id, category, question, answer, images = faq
        try:
            image_list = json.loads(images) if images else []
        except:
            image_list = []
        faq_list.append({
            "分類": category,
            "問題": question,
            "答案": answer,
            "圖片名稱": image_list
        })
    # 強化 prompt
    prompt = (
        "你是一個FAQ客服助理，請根據下方FAQ資料庫，先判斷使用者問題是否與FAQ『問題』完全一致（包括標點），如果有完全一致，請務必直接回傳該FAQ條目的所有內容（分類、問題、答案、圖片名稱），不要自行改寫。若沒有完全一致，再找最相關的問題與答案，若FAQ都沒有合適的，才用你自己的知識回答。\n"
        "請務必回傳以下JSON格式：{\"分類\":..., \"問題\":..., \"答案\":..., \"圖片名稱\":...}，若FAQ沒有合適答案，請將分類、問題、答案都填'無'，只用'答案'欄位回覆你的內容。\n"
        f"FAQ資料庫：{json.dumps(faq_list, ensure_ascii=False)}\n"
        f"使用者問題：{user_question}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": "你是一個FAQ客服助理，請根據FAQ資料庫回答。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.3
        )
        gpt_reply = response.choices[0].message.content.strip()
        print('=== GPT 回傳內容 ===')
        print(gpt_reply)
        try:
            import re
            match = re.search(r'\{[\s\S]*\}', gpt_reply)
            if match:
                faq_json = json.loads(match.group(0))
            else:
                faq_json = {"分類": "無", "問題": "無", "答案": gpt_reply, "圖片名稱": []}
        except Exception as e:
            faq_json = {"分類": "無", "問題": "無", "答案": gpt_reply, "圖片名稱": []}
        
        # 生成相關選項
        related_options = generate_related_options(user_question, faqs, faq_json.get("分類"), faq_json.get("問題"))
        
        if faq_json.get("分類") != "無" and faq_json.get("答案") != "無":
            answer = faq_json.get("答案", "")
            answer_html = convert_markdown_to_html(answer)
            images = faq_json.get("圖片名稱", [])
            if images and isinstance(images, list):
                for img in images:
                    if not any(img.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                        img_file = f"{img}.png"
                    else:
                        img_file = img
                    md_img = f'![](static/uploads/{img_file})'
                    html_img = f'<br><img src=\"static/uploads/{img_file}\" style=\"max-width:300px;\">'
                    answer += f'\n\n{md_img}'
                    answer_html += html_img
            return {
                'type': 'faq_response',
                'answer': answer,
                'answer_html': answer_html,
                'source': 'FAQ資料庫',
                'category': faq_json.get("分類", ""),
                'related_options': related_options
            }
        else:
            answer = faq_json.get("答案", gpt_reply)
            answer_html = convert_markdown_to_html(answer)
            return {
                'type': 'general_conversation',
                'answer': answer,
                'answer_html': answer_html,
                'source': 'GPT AI',
                'category': '一般對話',
                'related_options': related_options
            }
    except Exception as e:
        # 生成相關選項
        related_options = generate_related_options(user_question, faqs, faq_json.get("分類"), faq_json.get("問題"))
        
        return {
            'type': 'general_conversation',
            'answer': f"抱歉，AI 回答失敗：{str(e)}",
            'answer_html': f"抱歉，AI 回答失敗：{str(e)}",
            'source': 'GPT AI',
            'category': '一般對話',
            'related_options': related_options
        }

def generate_related_options(user_question, faqs, current_category=None, answered_question=None):
    """生成相關選項，優先從相同分類中選擇，並排除本次已回答的FAQ問題"""
    try:
        # 處理本次提問的關鍵詞
        clean_question = re.sub(r'[^\w\s]', '', user_question.lower())
        user_keywords = set(clean_question.split())
        
        # 分類FAQ：相同分類和其他分類
        same_category_faqs = []
        other_category_faqs = []
        
        for faq in faqs:
            score = 0
            faq_question = (faq[2] or '').lower()
            faq_answer = (faq[3] or '').lower()
            faq_category = faq[1]
            
            # FAQ問題的關鍵詞
            faq_keywords = set(re.sub(r'[^\w\s]', '', faq_question).split())
            # 若與本次提問關鍵詞交集大於等於2，視為語意重複，直接跳過
            if len(user_keywords & faq_keywords) >= 2:
                continue
            # 若本次已回答該FAQ問題，直接跳過
            if answered_question and normalize(faq_question) == normalize(answered_question):
                continue
            
            # 計算關鍵字分數
            for keyword in user_keywords:
                if keyword in faq_question:
                    score += 2
                if keyword in faq_answer:
                    score += 1
            
            # 如果當前問題有分類，且FAQ與當前問題相同分類，給予額外分數
            if current_category and faq_category == current_category:
                score += 3  # 相同分類給予額外分數
            
            if score > 0:
                if current_category and faq_category == current_category:
                    same_category_faqs.append((score, faq))
                else:
                    other_category_faqs.append((score, faq))
        
        related_options = []
        
        # 優先從相同分類中選擇（最多2個）
        if same_category_faqs:
            same_category_top = heapq.nlargest(2, same_category_faqs, key=lambda x: x[0])
            for score, faq in same_category_top:
                related_options.append({
                    'type': 'faq',
                    'text': faq[2],
                    'category': faq[1],
                    'same_category': True
                })
        
        # 從其他分類中補充（最多1個）
        if len(related_options) < 3 and other_category_faqs:
            other_category_top = heapq.nlargest(1, other_category_faqs, key=lambda x: x[0])
            for score, faq in other_category_top:
                if not any(opt['text'] == faq[2] for opt in related_options):
                    related_options.append({
                        'type': 'faq',
                        'text': faq[2],
                        'category': faq[1],
                        'same_category': False
                    })
        
        # 如果相關選項不足3個，從所有FAQ中隨機補充
        if len(related_options) < 3:
            all_faqs = same_category_faqs + other_category_faqs
            for score, faq in all_faqs:
                if len(related_options) >= 3:
                    break
                if not any(opt['text'] == faq[2] for opt in related_options):
                    is_same_category = current_category and faq[1] == current_category
                    related_options.append({
                        'type': 'faq',
                        'text': faq[2],
                        'category': faq[1],
                        'same_category': is_same_category
                    })
        
        # 添加其他常見問題連結作為最後一個選項
        related_options.append({
            'type': 'link',
            'text': '其他常見問題',
            'url': 'https://sites.google.com/seda-gtech.com.tw/carereliefsystem/%E9%A6%96%E9%A0%81'
        })
        
        return related_options[:4]  # 確保最多4個選項
        
    except Exception as e:
        print(f"生成相關選項時發生錯誤: {str(e)}")
        # 回退方案：返回基本選項
        return [
            {
                'type': 'link',
                'text': '其他常見問題',
                'url': 'https://sites.google.com/seda-gtech.com.tw/carereliefsystem/%E9%A6%96%E9%A0%81'
            }
        ]

if __name__ == '__main__':
    # 在 Render 上使用環境變數的 PORT，本地使用 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port) 