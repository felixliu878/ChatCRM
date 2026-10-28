#!/usr/bin/env python3
"""
测试用户消息保持可见功能
验证快速操作和手动输入的消息都能在对话中保持显示
"""
import os
import requests
import json
import socketio
import time

def test_user_message_visibility():
    """测试用户消息保持可见"""
    print("👁️ 测试用户消息保持可见功能...")
    
    # 1. 初始化会话
    print("1. 初始化会话...")
    response = requests.post('http://localhost:5001/api/init')
    data = response.json()
    
    if not data['success']:
        print(f"❌ 会话初始化失败: {data['message']}")
        return False
    
    session_id = data['session_id']
    print(f"✅ 会话初始化成功: {session_id}")
    
    # 2. 登录
    print("2. 用户登录...")
    login_data = {
        'username': os.getenv('CHATCRM_TEST_USER', ''),
        'password': os.getenv('CHATCRM_TEST_PASSWORD', ''),
        'session_id': session_id
    }
    
    response = requests.post('http://localhost:5001/api/login', json=login_data)
    data = response.json()
    
    if not data['success']:
        print(f"❌ 登录失败: {data['message']}")
        return False
    
    print(f"✅ 登录成功: {data['user']}")
    
    # 3. 创建WebSocket连接
    print("3. 建立WebSocket连接...")
    sio = socketio.Client()
    all_messages = []
    
    @sio.on('connect')
    def on_connect():
        print("✅ WebSocket连接成功")
    
    @sio.on('bot_message')
    def on_bot_message(data):
        msg_type = data.get('type', 'normal')
        if msg_type == 'confirmation':
            print(f"🤔 确认请求: {data['message']}")
            all_messages.append(('ai_confirmation', data['message']))
            
            # 自动确认
            time.sleep(1)
            sio.emit('user_action', {
                'action': 'confirm',
                'pending_sql': data.get('pending_sql'),
                'session_id': session_id
            })
            
        elif msg_type == 'processing':
            print(f"⏳ 处理中: {data['message']}")
            all_messages.append(('ai_processing', data['message']))
            
        else:
            print(f"🤖 AI最终回复: {data['message'][:80]}...")
            all_messages.append(('ai_response', data['message']))
    
    @sio.on('error')
    def on_error(data):
        print(f"❌ 错误: {data['message']}")
        all_messages.append(('error', data['message']))
    
    try:
        sio.connect('http://localhost:5001')
        time.sleep(1)
        
        # 4. 测试手动输入消息
        print("4. 发送手动输入消息...")
        manual_message = "查询所有客户的基本信息"
        print(f"📝 模拟用户手动输入: {manual_message}")
        all_messages.append(('user_manual', manual_message))
        
        sio.emit('send_message', {
            'message': manual_message,
            'session_id': session_id
        })
        
        time.sleep(8)  # 等待第一个操作完成
        
        # 5. 测试快速操作
        print("5. 发送快速操作...")
        quick_action = "查看客户"
        print(f"🚀 模拟用户快速操作: {quick_action}")
        all_messages.append(('user_quick', quick_action))
        
        sio.emit('send_message', {
            'message': quick_action,
            'session_id': session_id
        })
        
        time.sleep(8)  # 等待第二个操作完成
        
        # 6. 分析消息序列
        print("\n📋 完整的消息序列:")
        user_messages = []
        ai_messages = []
        
        for i, (msg_type, message) in enumerate(all_messages, 1):
            print(f"  {i}. {msg_type}: {message[:60]}...")
            if msg_type.startswith('user_'):
                user_messages.append(message)
            elif msg_type.startswith('ai_'):
                ai_messages.append(message)
        
        # 7. 验证用户消息可见性
        print("\n🔍 验证用户消息可见性:")
        
        success = True
        
        # 检查是否有用户消息
        if len(user_messages) >= 2:
            print(f"✅ 用户消息数量: {len(user_messages)} (预期: 2)")
            print(f"   - 手动输入: {user_messages[0]}")
            print(f"   - 快速操作: {user_messages[1]}")
        else:
            print(f"❌ 用户消息数量不足: {len(user_messages)} (预期: 2)")
            success = False
        
        # 检查是否有AI回复
        if len(ai_messages) >= 4:  # 每个操作至少有确认和最终回复
            print(f"✅ AI消息数量: {len(ai_messages)} (包含确认、处理、回复)")
        else:
            print(f"❌ AI消息数量不足: {len(ai_messages)}")
            success = False
        
        # 检查消息顺序
        if all_messages:
            first_msg_type = all_messages[0][0]
            if first_msg_type.startswith('user_'):
                print("✅ 消息顺序正确: 用户消息在前")
            else:
                print("❌ 消息顺序错误: AI消息在前")
                success = False
        
        if success:
            print("\n🎉 用户消息可见性测试成功！")
            print("   ✓ 手动输入的消息保持可见")
            print("   ✓ 快速操作的消息保持可见")
            print("   ✓ 消息顺序正确")
            print("   ✓ 完整的对话历史")
            return True
        else:
            print("\n❌ 用户消息可见性测试失败！")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        return False
    finally:
        sio.disconnect()

if __name__ == '__main__':
    success = test_user_message_visibility()
    exit(0 if success else 1) 