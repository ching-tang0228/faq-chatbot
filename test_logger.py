#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
聊天記錄功能測試腳本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chat_logger import ChatLogger
from datetime import datetime, timedelta
import json

def test_chat_logger():
    """測試聊天記錄功能"""
    print("🧪 開始測試聊天記錄功能...")
    
    # 初始化記錄器
    logger = ChatLogger('test_chat_logs.csv', 'test_chatbot.db')
    
    # 測試1: 記錄聊天對話
    print("\n📝 測試1: 記錄聊天對話")
    test_data = [
        {
            'user_question': '如何申請長照服務？',
            'bot_response': '長照服務申請流程如下：1. 撥打1966專線 2. 準備相關文件 3. 等待評估',
            'session_id': 'test_session_001',
            'ip_address': '192.168.1.100',
            'response_source': 'FAQ資料庫',
            'category': '長照服務'
        },
        {
            'user_question': '臥床照護要注意什麼？',
            'bot_response': '臥床照護注意事項：1. 定期翻身 2. 保持皮膚清潔 3. 預防褥瘡',
            'session_id': 'test_session_002',
            'ip_address': '192.168.1.101',
            'response_source': 'GPT AI',
            'category': '照護技巧'
        },
        {
            'user_question': '營養品怎麼選擇？',
            'bot_response': '營養品選擇建議：1. 諮詢醫師 2. 考慮個人需求 3. 注意成分標示',
            'session_id': 'test_session_003',
            'ip_address': '192.168.1.102',
            'response_source': 'GPT AI',
            'category': '營養保健'
        }
    ]
    
    for data in test_data:
        logger.log_chat(**data)
        print(f"✅ 記錄對話: {data['user_question'][:20]}...")
    
    # 測試2: 匯入CSV到資料庫
    print("\n📊 測試2: 匯入CSV到資料庫")
    imported_count = logger.import_csv_to_db()
    print(f"✅ 成功匯入 {imported_count} 筆記錄")
    
    # 測試3: 獲取統計資料
    print("\n📈 測試3: 獲取統計資料")
    stats = logger.get_statistics(days=30)
    print(f"✅ 總對話數: {stats['total_chats']}")
    print(f"✅ 統計期間: {stats['period']}")
    print(f"✅ 常見問題數量: {len(stats['common_questions'])}")
    print(f"✅ 分類統計數量: {len(stats['category_stats'])}")
    
    # 測試4: 獲取未回答問題
    print("\n❓ 測試4: 獲取未回答問題")
    unanswered = logger.get_unanswered_questions(days=7)
    print(f"✅ 未回答問題數量: {len(unanswered)}")
    
    # 測試5: 匯出Excel
    print("\n📄 測試5: 匯出Excel")
    try:
        output_file = logger.export_to_excel('test_export.xlsx', days=30)
        print(f"✅ 成功匯出到: {output_file}")
    except Exception as e:
        print(f"❌ 匯出失敗: {e}")
    
    # 測試6: 清理舊記錄
    print("\n🧹 測試6: 清理舊記錄")
    deleted_count = logger.cleanup_old_records(days=1)  # 清理1天前的記錄
    print(f"✅ 清理了 {deleted_count} 筆舊記錄")
    
    print("\n🎉 所有測試完成！")
    
    # 清理測試檔案
    cleanup_test_files()

def cleanup_test_files():
    """清理測試檔案"""
    test_files = ['test_chat_logs.csv', 'test_chatbot.db', 'test_export.xlsx']
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ 已清理測試檔案: {file}")

def test_integration():
    """測試與主應用程式的整合"""
    print("\n🔗 測試與主應用程式的整合...")
    
    try:
        # 測試導入
        from chatbot_app import chat_logger
        print("✅ 成功導入 chat_logger")
        
        # 測試基本功能
        chat_logger.log_chat(
            user_question='整合測試問題',
            bot_response='整合測試回答',
            session_id='integration_test',
            ip_address='127.0.0.1',
            response_source='測試',
            category='測試'
        )
        print("✅ 成功記錄測試對話")
        
        # 測試統計功能
        stats = chat_logger.get_statistics(days=1)
        print(f"✅ 整合測試統計: {stats['total_chats']} 筆記錄")
        
    except Exception as e:
        print(f"❌ 整合測試失敗: {e}")

if __name__ == "__main__":
    print("🚀 聊天記錄功能測試")
    print("=" * 50)
    
    # 執行測試
    test_chat_logger()
    test_integration()
    
    print("\n" + "=" * 50)
    print("✅ 測試完成！") 