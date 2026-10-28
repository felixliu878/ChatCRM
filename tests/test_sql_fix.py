#!/usr/bin/env python3
"""
快速测试SQL序列化修复
"""
import os
import requests
import json
import socketio
import time

def test_sql_serialization():
    """测试SQL序列化修复"""
    print("🧪 开始测试SQL序列化修复...")
    
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
    received_messages = []
    
    @sio.on('connect')
    def on_connect():
        print("✅ WebSocket连接成功")
    
    @sio.on('user_message')
    def on_user_message(data):
        print(f"📨 用户消息: {data['message']}")
        received_messages.append(('user_message', data))
    
    @sio.on('sql_confirmation')
    def on_sql_confirmation(data):
        print(f"🔍 SQL确认: {data['operation_type']} - {data['sql_query'][:50]}...")
        received_messages.append(('sql_confirmation', data))
        
        # 自动确认SQL
        print("4. 自动确认SQL执行...")
        sio.emit('confirm_sql', {
            'confirmed': True,
            'sql_query': data['sql_query'],
            'original_message': data['original_message'],
            'session_id': session_id
        })
    
    @sio.on('bot_message')
    def on_bot_message(data):
        print(f"🤖 AI回复: {data['message'][:100]}...")
        if data.get('data'):
            print(f"📊 数据记录: {data.get('data_count', 0)} 条")
        received_messages.append(('bot_message', data))
    
    @sio.on('error')
    def on_error(data):
        print(f"❌ 错误: {data['message']}")
        received_messages.append(('error', data))
    
    try:
        sio.connect('http://localhost:5001')
        time.sleep(1)
        
        # 4. 发送测试消息
        print("5. 发送测试消息...")
        test_message = "显示所有客户信息"
        sio.emit('send_message', {
            'message': test_message,
            'session_id': session_id
        })
        
        # 等待响应
        print("6. 等待响应...")
        time.sleep(10)  # 等待10秒处理
        
        # 检查结果
        print("\n📋 收到的消息总结:")
        for i, (msg_type, data) in enumerate(received_messages, 1):
            print(f"  {i}. {msg_type}: {str(data)[:100]}...")
        
        # 检查是否成功
        bot_messages = [msg for msg_type, msg in received_messages if msg_type == 'bot_message']
        errors = [msg for msg_type, msg in received_messages if msg_type == 'error']
        
        if bot_messages and not errors:
            print("\n🎉 测试成功！SQL序列化问题已修复！")
            return True
        elif errors:
            print(f"\n❌ 测试失败！仍有错误: {errors[-1][1]['message']}")
            return False
        else:
            print("\n⚠️ 测试未完成，没有收到预期响应")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket连接错误: {e}")
        return False
    finally:
        sio.disconnect()

if __name__ == '__main__':
    success = test_sql_serialization()
    exit(0 if success else 1) 