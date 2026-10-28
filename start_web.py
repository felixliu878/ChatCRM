#!/usr/bin/env python3
"""
ChatCRM Web应用启动脚本
快速启动Web界面
"""

import os
import sys
import subprocess

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import flask
        import flask_socketio
        import pymysql
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def main():
    print("🚀 启动ChatCRM Web应用...")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 检查文件
    required_files = [
        'app.py',
        'templates/index.html',
        'static/css/style.css',
        'static/js/app.js',
        'database.py',
        'llm_service.py',
        'auth.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ 缺少文件:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return
    
    print("✅ 所有文件检查完成")
    print("✅ 依赖检查完成")
    print()
    print("🌐 启动Web服务器...")
    print("📱 访问地址: http://localhost:5001")
    print("🔧 开发模式已启用")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    # 启动Flask应用
    try:
        from app import app, socketio
        socketio.run(app, debug=True, host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n可能的解决方案:")
        print("1. 检查端口5000是否被占用")
        print("2. 检查数据库连接配置")
        print("3. 检查API密钥配置")

if __name__ == '__main__':
    main() 