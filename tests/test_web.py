#!/usr/bin/env python3
"""
ChatCRM Web应用功能测试脚本
测试各个API端点和功能
"""

import os
import requests
import json
import time

def test_web_application():
    """测试Web应用的各个功能"""
    
    base_url = "http://localhost:5001"
    
    print("🧪 开始测试ChatCRM Web应用...")
    print("=" * 50)
    
    # 测试1：主页面加载
    print("📄 测试1: 主页面加载...")
    try:
        response = requests.get(base_url)
        if response.status_code == 200 and "ChatCRM" in response.text:
            print("✅ 主页面加载成功")
        else:
            print("❌ 主页面加载失败")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False
    
    # 测试2：会话初始化API
    print("\n🔄 测试2: 会话初始化...")
    try:
        response = requests.post(f"{base_url}/api/init")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                session_id = data.get('session_id')
                available_users = data.get('available_users', [])
                print(f"✅ 会话初始化成功，Session ID: {session_id[:8]}...")
                print(f"📋 可用用户: {available_users}")
                return session_id
            else:
                print(f"❌ 会话初始化失败: {data.get('message')}")
                return False
        else:
            print(f"❌ API调用失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 会话初始化异常: {e}")
        return False

def test_login(session_id):
    """测试登录功能"""
    print("\n🔐 测试3: 用户登录...")
    
    base_url = "http://localhost:5001"
    
    # 尝试使用测试用户登录
    test_credentials = [
        {"username": os.getenv("CHATCRM_TEST_USER", ""), "password": os.getenv("CHATCRM_TEST_PASSWORD", "")}
    ]
    
    for cred in test_credentials:
        try:
            response = requests.post(f"{base_url}/api/login", 
                json={
                    "username": cred["username"],
                    "password": cred["password"],
                    "session_id": session_id
                })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ 用户 {cred['username']} 登录成功")
                    return True
                else:
                    print(f"⚠️ 用户 {cred['username']} 登录失败: {data.get('message')}")
            else:
                print(f"❌ 登录API调用失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ 登录测试异常: {e}")
    
    print("ℹ️ 所有测试用户登录失败，可能需要在数据库中创建用户")
    return False

def check_static_files():
    """检查静态文件是否正确加载"""
    print("\n📁 测试4: 静态文件检查...")
    
    base_url = "http://localhost:5001"
    static_files = [
        "/static/css/style.css",
        "/static/js/app.js"
    ]
    
    all_good = True
    for file_path in static_files:
        try:
            response = requests.get(f"{base_url}{file_path}")
            if response.status_code == 200:
                print(f"✅ {file_path} 加载成功")
            else:
                print(f"❌ {file_path} 加载失败，状态码: {response.status_code}")
                all_good = False
        except Exception as e:
            print(f"❌ {file_path} 检查异常: {e}")
            all_good = False
    
    return all_good

def check_dependencies():
    """检查依赖和配置"""
    print("\n⚙️ 测试5: 依赖和配置检查...")
    
    try:
        # 检查数据库模块
        from database import DatabaseManager
        print("✅ 数据库模块导入成功")
        
        # 检查LLM服务模块
        from llm_service import LLMService
        print("✅ LLM服务模块导入成功")
        
        # 检查认证模块
        from auth import AuthManager
        print("✅ 认证模块导入成功")
        
        # 检查配置
        from config import DB_CONFIG, DEEPSEEK_CONFIG
        print("✅ 配置文件导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 依赖检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 ChatCRM Web应用自动化测试")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请检查项目配置")
        return
    
    # 等待服务器启动
    print("\n⏳ 等待Web服务器启动...")
    time.sleep(3)
    
    # 执行测试
    session_id = test_web_application()
    if session_id:
        test_login(session_id)
    
    check_static_files()
    
    print("\n" + "=" * 60)
    print("🎯 测试完成！")
    print("🌐 请访问 http://localhost:5001 查看Web界面")
    print("📖 详细使用说明请查看 WEB_README.md")
    print("=" * 60)

if __name__ == '__main__':
    main() 