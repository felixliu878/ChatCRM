#!/usr/bin/env python3
"""
测试新的交互逻辑
1. 自然语言确认（不显示SQL）
2. 用户输入保持可见
3. 处理中提示
"""
import os
import requests
import json
import socketio
import time

def test_new_interaction():
    """测试新的交互逻辑"""
    print("🎨 测试新的交互逻辑...")
    
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
    messages_received = []
    
    @sio.on('connect')
    def on_connect():
        print("✅ WebSocket连接成功")
    
    @sio.on('user_message')
    def on_user_message(data):
        print(f"📨 用户消息: {data['message']}")
        messages_received.append(('user_message', data))
    
    @sio.on('bot_message')
    def on_bot_message(data):
        msg_type = data.get('type', 'normal')
        if msg_type == 'confirmation':
            print(f"🤔 确认请求: {data['message']}")
            print(f"   按钮: {[btn['text'] for btn in data.get('buttons', [])]}")
            messages_received.append(('confirmation', data))
            
            # 自动确认（测试确认流程）
            time.sleep(1)
            print("4. 自动确认操作...")
            sio.emit('user_action', {
                'action': 'confirm',
                'pending_sql': data.get('pending_sql'),
                'session_id': session_id
            })
            
        elif msg_type == 'processing':
            print(f"⏳ 处理中: {data['message']}")
            messages_received.append(('processing', data))
            
        else:
            print(f"🤖 AI回复: {data['message'][:100]}...")
            if data.get('data'):
                print(f"   📊 数据记录: {data.get('data_count', 0)} 条")
            messages_received.append(('bot_message', data))
    
    @sio.on('error')
    def on_error(data):
        print(f"❌ 错误: {data['message']}")
        messages_received.append(('error', data))
    
    try:
        sio.connect('http://localhost:5001')
        time.sleep(1)
        
        # 4. 发送测试消息
        print("5. 发送测试消息...")
        test_message = "显示所有客户的姓名和电话"
        sio.emit('send_message', {
            'message': test_message,
            'session_id': session_id
        })
        
        # 等待响应
        print("6. 等待响应...")
        time.sleep(12)  # 等待12秒处理完成
        
        # 分析结果
        print("\n📋 收到的消息流程:")
        for i, (msg_type, data) in enumerate(messages_received, 1):
            print(f"  {i}. {msg_type}: {str(data.get('message', data))[:80]}...")
        
        # 检验新交互逻辑
        confirmations = [msg for msg_type, msg in messages_received if msg_type == 'confirmation']
        processing = [msg for msg_type, msg in messages_received if msg_type == 'processing']
        bot_responses = [msg for msg_type, msg in messages_received if msg_type == 'bot_message']
        errors = [msg for msg_type, msg in messages_received if msg_type == 'error']
        
        success = True
        
        print("\n🔍 检验新交互逻辑:")
        
        # 1. 检验自然语言确认
        if confirmations:
            print("✅ 1. 自然语言确认 - 成功")
            confirmation_msg = confirmations[0][1]['message']
            if 'SQL' not in confirmation_msg:
                print("✅ 1.1. 未显示SQL语句 - 成功")
            else:
                print("❌ 1.1. 仍然显示SQL语句 - 失败")
                success = False
        else:
            print("❌ 1. 自然语言确认 - 失败（未收到确认消息）")
            success = False
        
        # 2. 检验处理中提示
        if processing:
            print("✅ 2. 处理中提示 - 成功")
        else:
            print("❌ 2. 处理中提示 - 失败（未显示处理中提示）")
            success = False
        
        # 3. 检验最终响应
        if bot_responses and not errors:
            print("✅ 3. 最终响应 - 成功")
        elif errors:
            print(f"❌ 3. 最终响应 - 失败（有错误: {errors[-1][1]['message']}）")
            success = False
        else:
            print("❌ 3. 最终响应 - 失败（未收到响应）")
            success = False
        
        if success:
            print("\n🎉 新交互逻辑测试成功！")
            print("   ✓ 用自然语言确认代替SQL显示")
            print("   ✓ 显示处理中提示")
            print("   ✓ 完整的对话流程")
            return True
        else:
            print("\n❌ 新交互逻辑测试失败！")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket连接错误: {e}")
        return False
    finally:
        sio.disconnect()

if __name__ == '__main__':
    success = test_new_interaction()
    exit(0 if success else 1) 