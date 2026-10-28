#!/usr/bin/env python3
"""
ChatCRM Web API Server
Flask后端服务器，为Web界面提供API接口
"""

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import uuid
import threading
import time
from datetime import datetime
import json
import os
import secrets
from decimal import Decimal

# 导入现有的ChatCRM模块
from database import DatabaseManager
from llm_service import LLMService
from auth import AuthManager

# 尝试导入fallback服务
try:
    from llm_service_fallback import LLMServiceFallback
except ImportError:
    LLMServiceFallback = None

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量存储用户会话
user_sessions = {}

def serialize_for_json(obj):
    """JSON序列化辅助函数，处理datetime和Decimal类型"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj

class WebChatCRM:
    def __init__(self, session_id):
        self.session_id = session_id
        self.db_manager = DatabaseManager()
        self.auth_manager = None
        self.llm_service = None
        self.schema_info = {}
        self.is_authenticated = False
        self.current_user = None
        self.connected = False
        
    def initialize(self):
        """初始化ChatCRM实例"""
        try:
            # 连接数据库
            success, message = self.db_manager.connect()
            if not success:
                return False, f"数据库连接失败: {message}"
            
            self.connected = True
            
            # 初始化认证管理器
            self.auth_manager = AuthManager(self.db_manager)
            
            # 初始化LLM服务
            try:
                self.llm_service = LLMService()
            except Exception as e:
                if LLMServiceFallback:
                    self.llm_service = LLMServiceFallback()
                else:
                    return False, f"LLM服务初始化失败: {str(e)}"
            
            # 加载数据库结构
            success, schema_info, message = self.db_manager.get_database_schema()
            if success:
                self.schema_info = schema_info
            
            return True, "ChatCRM初始化成功"
            
        except Exception as e:
            return False, f"初始化失败: {str(e)}"
    
    def authenticate(self, username, password):
        """用户认证"""
        if not self.auth_manager:
            return False, "认证管理器未初始化"
        
        success = self.auth_manager._validate_credentials(username, password)
        if success:
            self.is_authenticated = True
            self.current_user = username
            self.auth_manager.current_user = username
            return True, f"用户 {username} 登录成功"
        else:
            return False, "用户名或密码错误"
    

    
    def process_message(self, message):
        """处理用户消息"""
        if not self.is_authenticated:
            return {
                'type': 'error',
                'message': '请先登录后再进行操作'
            }
        
        try:
            # 分析操作类型
            operation_type = self.llm_service.analyze_operation_type(message)
            
            # 生成SQL查询
            success, sql_query, error_msg = self.llm_service.text_to_sql(message, self.schema_info)
            
            if not success:
                return {
                    'type': 'error',
                    'message': f'SQL生成失败: {error_msg}'
                }
            
            # Trust the generated SQL over the keyword guess: only read-only SQL skips confirmation
            sql_operation_type = DatabaseManager.operation_type_from_sql(sql_query)
            if sql_operation_type != 'READ':
                operation_type = sql_operation_type

            # 对于查询操作（READ类型），直接执行，无需确认
            if operation_type == 'READ':
                return self.execute_sql(sql_query, message)
            
            # 对于其他操作类型，需要用户确认
            # 生成自然语言确认消息
            confirmation_message = self._generate_confirmation_message(message, operation_type, sql_query)
            
            return {
                'type': 'confirmation_request',
                'confirmation_message': confirmation_message,
                'sql_query': sql_query,
                'operation_type': operation_type,
                'original_message': message
            }
            
        except Exception as e:
            return {
                'type': 'error',
                'message': f'处理消息时出错: {str(e)}'
            }
    
    def _generate_confirmation_message(self, original_message, operation_type, sql_query):
        """生成自然语言确认消息"""
        query_upper = sql_query.strip().upper()
        
        if query_upper.startswith('SELECT'):
            if 'COUNT(' in query_upper:
                return f"我将为您统计相关数据。是否继续？"
            else:
                return f"我将为您查询相关信息。是否继续？"
        elif query_upper.startswith('INSERT'):
            return f"我将向数据库中添加新记录。这个操作会修改数据，是否确认执行？"
        elif query_upper.startswith('UPDATE'):
            return f"我将修改现有数据记录。这个操作会更改数据，是否确认执行？"
        elif query_upper.startswith('DELETE'):
            return f"我将删除相关数据记录。⚠️ 注意：删除操作不可恢复，是否确认执行？"
        else:
            return f"我将执行数据库操作来处理您的请求。是否继续？"
    
    def execute_sql(self, sql_query, original_message):
        """执行SQL查询"""
        try:
            success, results, message = self.db_manager.execute_query(sql_query)
            
            if not success:
                return {
                    'type': 'error',
                    'message': f'查询执行失败: {message}'
                }
            
            # 序列化结果以避免JSON序列化错误
            serialized_results = serialize_for_json(results)
            
            # 生成自然语言回答
            success, natural_response = self.llm_service.generate_natural_language_response(
                original_message, sql_query, serialized_results
            )
            
            response_data = {
                'type': 'success',
                'message': natural_response if success else '操作已完成',
                'sql_query': sql_query,
                'results': serialized_results
            }
            
            # 添加操作详情
            if 'affected_rows' in serialized_results:
                response_data['affected_rows'] = serialized_results['affected_rows']
                response_data['operation_details'] = self._get_operation_details(sql_query, serialized_results)
            elif 'data' in serialized_results:
                response_data['data_count'] = len(serialized_results['data'])
                # 暂时不发送表格数据，LLM已经在自然语言回答中包含了详细信息
                # response_data['data'] = serialized_results['data'][:5]  # 只返回前5条数据用于显示
                # response_data['columns'] = serialized_results.get('columns', [])
            
            return response_data
            
        except Exception as e:
            return {
                'type': 'error',
                'message': f'执行查询时出错: {str(e)}'
            }
    
    def _get_operation_details(self, sql_query, results):
        """获取操作详情"""
        query_upper = sql_query.strip().upper()
        affected_rows = results.get('affected_rows', 0)
        
        if query_upper.startswith('INSERT'):
            return f"向数据库中插入了 {affected_rows} 条新记录"
        elif query_upper.startswith('UPDATE'):
            return f"修改了 {affected_rows} 条记录"
        elif query_upper.startswith('DELETE'):
            return f"从数据库中删除了 {affected_rows} 条记录"
        else:
            return f"操作影响了 {affected_rows} 条记录"
    
    def cleanup(self):
        """清理资源"""
        if self.db_manager and self.db_manager.is_connected:
            self.db_manager.disconnect()

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/test')
def test_page():
    """测试页面"""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests', 'test_websocket.html'), 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/init', methods=['POST'])
def init_session():
    """初始化用户会话"""
    session_id = str(uuid.uuid4())
    
    chatcrm = WebChatCRM(session_id)
    success, message = chatcrm.initialize()
    
    if success:
        user_sessions[session_id] = chatcrm
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 500

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id or session_id not in user_sessions:
        return jsonify({'success': False, 'message': '会话无效，请刷新页面'}), 400
    
    chatcrm = user_sessions[session_id]
    username = data.get('username')
    password = data.get('password')
    
    success, message = chatcrm.authenticate(username, password)
    
    return jsonify({
        'success': success,
        'message': message,
        'user': username if success else None
    })

@socketio.on('connect')
def handle_connect():
    """处理WebSocket连接"""
    print('客户端已连接')
    emit('status', {'message': '已连接到ChatCRM服务器'})

@socketio.on('disconnect')
def handle_disconnect():
    """处理WebSocket断开连接"""
    print('客户端已断开连接')

@socketio.on('send_message')
def handle_message(data):
    """处理用户消息"""
    session_id = data.get('session_id')
    message = data.get('message', '').strip()
    
    print(f"收到消息: session_id={session_id}, message={message}")  # 调试信息
    
    if not session_id or session_id not in user_sessions:
        print(f"会话无效: session_id={session_id}, 可用会话: {list(user_sessions.keys())}")
        emit('error', {'message': '会话无效，请刷新页面'})
        return
    
    if not message:
        emit('error', {'message': '请输入有效的消息'})
        return
    
    chatcrm = user_sessions[session_id]
    
    if not chatcrm.is_authenticated:
        emit('error', {'message': '请先登录'})
        return
    
    # 用户消息已在前端显示，无需重复发送
    # emit('user_message', {'message': message, 'timestamp': datetime.now().isoformat()})
    
    # 处理消息
    try:
        result = chatcrm.process_message(message)
        print(f"处理结果: {result}")  # 调试信息
        
        if result['type'] == 'error':
            emit('error', result)
        elif result['type'] == 'confirmation_request':
            # 发送自然语言确认消息
            emit('bot_message', {
                'message': result['confirmation_message'],
                'timestamp': datetime.now().isoformat(),
                'type': 'confirmation',
                'buttons': [
                    {'text': '确认执行', 'action': 'confirm', 'style': 'primary'},
                    {'text': '取消', 'action': 'cancel', 'style': 'secondary'}
                ],
                'pending_sql': {
                    'sql_query': result['sql_query'],
                    'original_message': result['original_message'],
                    'operation_type': result['operation_type']
                }
            })
        elif result['type'] == 'success':
            # 对于直接执行的查询操作，发送成功响应
            response_data = serialize_for_json({
                'message': result['message'],
                'timestamp': datetime.now().isoformat(),
                'type': 'success',
                'details': result.get('operation_details'),
                'affected_rows': result.get('affected_rows'),
                'data_count': result.get('data_count'),
                'data': result.get('data'),
                'columns': result.get('columns')
            })
            print(f"发送查询结果: {response_data}")
            emit('bot_message', response_data)
    except Exception as e:
        print(f"处理消息时出错: {e}")
        emit('error', {'message': f'处理消息时出错: {str(e)}'})

@socketio.on('user_action')
def handle_user_action(data):
    """处理用户操作（确认/取消）"""
    session_id = data.get('session_id')
    action = data.get('action')  # 'confirm' 或 'cancel'
    pending_sql = data.get('pending_sql', {})
    
    print(f"收到用户操作: session_id={session_id}, action={action}")  # 调试信息
    
    if not session_id or session_id not in user_sessions:
        print(f"操作时会话无效: session_id={session_id}")
        emit('error', {'message': '会话无效'})
        return
    
    chatcrm = user_sessions[session_id]
    
    if action == 'cancel':
        print("用户取消了操作")
        emit('bot_message', {
            'message': '好的，操作已取消。有什么其他需要帮助的吗？',
            'timestamp': datetime.now().isoformat(),
            'type': 'info'
        })
        return
    
    if action == 'confirm' and pending_sql:
        sql_query = pending_sql.get('sql_query', '')
        original_message = pending_sql.get('original_message', '')
        
        print("开始执行SQL查询...")
        
        # 先发送处理中消息
        emit('bot_message', {
            'message': '请稍等，正在处理...',
            'timestamp': datetime.now().isoformat(),
            'type': 'processing'
        })
        
        # 执行SQL查询
        try:
            result = chatcrm.execute_sql(sql_query, original_message)
            print(f"SQL执行结果: {result}")  # 调试信息
            
            if result['type'] == 'error':
                emit('error', result)
            else:
                # 发送成功响应，确保所有数据都已序列化
                response_data = serialize_for_json({
                    'message': result['message'],
                    'timestamp': datetime.now().isoformat(),
                    'type': 'success',
                    'details': result.get('operation_details'),
                    'affected_rows': result.get('affected_rows'),
                    'data_count': result.get('data_count'),
                    'data': result.get('data'),
                    'columns': result.get('columns')
                })
                print(f"发送响应: {response_data}")
                emit('bot_message', response_data)
        except Exception as e:
            print(f"执行SQL时出错: {e}")
            emit('error', {'message': f'执行SQL时出错: {str(e)}'})

# 移除teardown handler，改为手动管理会话
# @app.teardown_appcontext
# def cleanup_session(exception):

if __name__ == '__main__':
    print("🚀 ChatCRM Web服务器启动中...")
    print("🌐 请访问: http://localhost:5001")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001) 