#!/usr/bin/env python3
"""
ChatCRM - AI-Native CRM System
Allows users to interact with CRM database using natural language
"""

import sys
import signal
from typing import Tuple, Dict, Any
from colorama import Fore, Style, init

# Import our modules
from database import DatabaseManager
from llm_service import LLMService
from auth import AuthManager
from config import APP_CONFIG

# Import fallback service
try:
    from llm_service_fallback import LLMServiceFallback
except ImportError:
    LLMServiceFallback = None

init(autoreset=True)

class ChatCRM:
    def __init__(self):
        self.db_manager = DatabaseManager()
        
        # Try to initialize LLM service with OpenAI SDK, fallback to requests if needed
        try:
            self.llm_service = LLMService()
        except Exception as e:
            print(f"{Fore.YELLOW}OpenAI SDK initialization failed: {str(e)}")
            if LLMServiceFallback:
                print(f"{Fore.YELLOW}Using fallback LLM service with requests library...")
                self.llm_service = LLMServiceFallback()
            else:
                print(f"{Fore.RED}No fallback service available. Please check your OpenAI SDK installation.")
                raise e
        
        self.auth_manager = AuthManager(self.db_manager)
        self.schema_info = {}
        self.running = True
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n{Fore.YELLOW}Shutting down ChatCRM...")
        self.shutdown()
        sys.exit(0)
    
    def run(self):
        """Main application loop following the flowchart logic"""
        self._show_welcome()
        
        # Step 1: Connect to Database
        if not self._connect_to_database():
            return
        
        # Step 2: Login - Ask user to input credentials
        if not self._handle_login():
            return
        
        # Step 3: Get database schema for LLM
        if not self._load_database_schema():
            return
        
        # Main operation loop
        while self.running:
            # Step 4: Ask User what type of operation need to be done
            user_input = self._get_user_operation_input()
            
            if user_input is None:  # User wants to exit
                break
            
            # Step 5: Process user input and operate database
            self._process_user_operation(user_input)
            
            # Step 6: Ask if further operation is needed
            if not self._ask_continue():
                break
        
        self.shutdown()
    
    def _show_welcome(self):
        """Show welcome message"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}          欢迎使用 ChatCRM - AI智能客户关系管理系统")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}本系统允许您使用自然语言与CRM数据库进行交互")
        print(f"{Fore.YELLOW}由人工智能技术驱动，支持中文对话。")
        print(f"{Fore.CYAN}{'='*60}\n")
    
    def _connect_to_database(self) -> bool:
        """Step 1: Connect to Database"""
        print(f"{Fore.CYAN}步骤 1: 连接数据库...")
        success, message = self.db_manager.connect()
        
        if not success:
            print(f"{Fore.RED}数据库连接失败: {message}")
            print(f"{Fore.YELLOW}请检查数据库配置后重试。")
            return False
        
        return True
    
    def _handle_login(self) -> bool:
        """Step 2: Login - Ask user to input credentials"""
        print(f"\n{Fore.CYAN}步骤 2: 用户身份验证")
        
        # Show available users from database
        self.auth_manager.show_demo_credentials()
        
        success, message = self.auth_manager.login()
        
        if not success:
            print(f"{Fore.RED}身份验证失败: {message}")
            return False
        
        return True
    
    def _load_database_schema(self) -> bool:
        """Load database schema for LLM context"""
        print(f"\n{Fore.CYAN}正在加载数据库结构...")
        success, schema_info, message = self.db_manager.get_database_schema()
        
        if success:
            self.schema_info = schema_info
            print(f"{Fore.GREEN}✓ 数据库结构加载成功")
            print(f"{Fore.YELLOW}在数据库中发现 {len(schema_info)} 个表")
            return True
        else:
            print(f"{Fore.RED}✗ 数据库结构加载失败: {message}")
            return False
    
    def _get_user_operation_input(self) -> str:
        """Step 4: Ask User what type of operation need to be done"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}您希望对CRM数据进行什么操作？")
        print(f"{Fore.YELLOW}支持的操作类型:")
        print(f"{Fore.GREEN}  📝 添加数据: 添加一个名叫张三的新客户，邮箱是zhangsan@email.com")
        print(f"{Fore.CYAN}  🔍 查询数据: 显示所有客户 / 查找来自北京的客户")
        print(f"{Fore.YELLOW}  ✏️  更新数据: 更新客户李四的邮箱地址为new@email.com")
        print(f"{Fore.RED}  🗑️  删除数据: 删除不活跃的客户")
        print(f"{Fore.MAGENTA}💾 注意: 所有数据操作都会真实地影响数据库!")
        print(f"{Fore.CYAN}{'='*60}")
        
        try:
            user_input = input(f"{Fore.WHITE}请输入您的需求: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye', '退出', '结束', '再见']:
                return None
            
            if not user_input:
                print(f"{Fore.YELLOW}请输入有效的请求。")
                return self._get_user_operation_input()
            
            return user_input
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}再见!")
            return None
        except Exception as e:
            print(f"{Fore.RED}输入错误: {str(e)}")
            return self._get_user_operation_input()
    
    def _process_user_operation(self, user_input: str):
        """Step 5: Process user input and operate database"""
        print(f"\n{Fore.CYAN}正在处理您的请求...")
        
        # Analyze operation type
        operation_type = self.llm_service.analyze_operation_type(user_input)
        print(f"{Fore.YELLOW}检测到的操作类型: {operation_type}")
        
        # Convert natural language to SQL
        success, sql_query, message = self.llm_service.text_to_sql(user_input, self.schema_info)
        
        if not success:
            print(f"{Fore.RED}✗ SQL生成失败: {message}")
            return
        
        # Trust the generated SQL over the keyword guess: only read-only SQL skips confirmation
        sql_operation_type = self.db_manager.operation_type_from_sql(sql_query)
        if sql_operation_type != 'READ':
            operation_type = sql_operation_type

        # 对于查询操作（READ类型），直接执行，无需确认
        if operation_type != 'READ':
            # 对于非查询操作，需要用户确认
            if not self._confirm_execution(sql_query, operation_type):
                print(f"{Fore.YELLOW}操作已被用户取消。")
                return
        else:
            print(f"{Fore.CYAN}🔍 这是一个查询操作，直接执行中...")
        
        # Execute the SQL query
        success, results, message = self.db_manager.execute_query(sql_query)
        
        if success:
            self._display_results(results, sql_query, user_input)
        else:
            print(f"{Fore.RED}✗ 查询执行失败: {message}")
    
    def _confirm_execution(self, sql_query: str, operation_type: str) -> bool:
        """Confirm with user before executing the query"""
        print(f"\n{Fore.YELLOW}生成的SQL查询:")
        print(f"{Fore.WHITE}{sql_query}")
        
        # For different operation types, show different warnings/confirmations
        if operation_type == 'CREATE':
            print(f"{Fore.GREEN}📝 这是一个添加新数据的操作")
            print(f"{Fore.GREEN}此操作将向数据库中插入新记录。")
        elif operation_type == 'UPDATE':
            print(f"{Fore.YELLOW}✏️  这是一个更新数据的操作")
            print(f"{Fore.YELLOW}此操作将修改数据库中现有的数据。")
        elif operation_type == 'DELETE':
            print(f"{Fore.RED}🗑️  警告: 这是一个删除数据的操作!")
            print(f"{Fore.RED}此操作将永久删除数据库中的数据！")
        elif operation_type == 'READ':
            print(f"{Fore.CYAN}🔍 这是一个查询数据的操作")
            print(f"{Fore.CYAN}此操作只会读取数据，不会修改数据库。")
        
        try:
            if operation_type == 'DELETE':
                confirm = input(f"{Fore.RED}确认要执行这个删除操作吗? 请输入 'DELETE' 确认: ").strip()
                return confirm == 'DELETE'
            else:
                confirm = input(f"{Fore.CYAN}执行此查询吗? (y/N): ").strip().lower()
                return confirm in ['y', 'yes', 'Y', '是', '确认', '执行']
        except KeyboardInterrupt:
            return False
    
    def _display_results(self, results: Dict, sql_query: str, user_input: str):
        """Display query results with feedback"""
        print(f"\n{Fore.GREEN}✓ 查询执行成功!")
        
        # Show operation details based on result type
        self._show_operation_details(results, sql_query)
        
        # Generate natural language response instead of showing raw data
        success, natural_response = self.llm_service.generate_natural_language_response(user_input, sql_query, results)
        if success:
            print(f"\n{Fore.CYAN}回答:")
            print(f"{Fore.WHITE}{natural_response}")
        else:
            # Fallback to formatted results if AI response fails
            formatted_results = self.db_manager.format_results(results)
            print(f"\n{Fore.CYAN}查询结果:")
            print(f"{Fore.WHITE}{formatted_results}")
            
            # Generate AI explanation as backup
            success, explanation = self.llm_service.generate_explanation(sql_query, results)
            if success:
                print(f"\n{Fore.YELLOW}说明:")
                print(f"{Fore.WHITE}{explanation}")
    
    def _show_operation_details(self, results: Dict, sql_query: str):
        """Show detailed information about what operation was performed"""
        query_upper = sql_query.strip().upper()
        
        if 'affected_rows' in results:
            affected_rows = results['affected_rows']
            
            if query_upper.startswith('INSERT'):
                if affected_rows > 0:
                    print(f"{Fore.GREEN}✅ 数据添加成功! 向数据库中插入了 {affected_rows} 条新记录")
                else:
                    print(f"{Fore.YELLOW}⚠️  未插入任何记录，请检查数据是否已存在或有约束冲突")
                    
            elif query_upper.startswith('UPDATE'):
                if affected_rows > 0:
                    print(f"{Fore.GREEN}✅ 数据更新成功! 修改了 {affected_rows} 条记录")
                else:
                    print(f"{Fore.YELLOW}⚠️  未更新任何记录，可能是因为未找到匹配的数据")
                    
            elif query_upper.startswith('DELETE'):
                if affected_rows > 0:
                    print(f"{Fore.GREEN}✅ 数据删除成功! 从数据库中删除了 {affected_rows} 条记录")
                else:
                    print(f"{Fore.YELLOW}⚠️  未删除任何记录，可能是因为未找到匹配的数据")
                    
        elif 'data' in results:
            data_count = len(results['data'])
            if data_count > 0:
                print(f"{Fore.GREEN}✅ 数据查询成功! 找到了 {data_count} 条记录")
            else:
                print(f"{Fore.YELLOW}⚠️  查询完成，但未找到匹配的数据")
        
        # Show a confirmation that the operation actually affected the database
        if 'affected_rows' in results and results['affected_rows'] > 0:
            print(f"{Fore.CYAN}💾 数据已永久保存到数据库中")
            
            # For INSERT operations, offer to show the newly inserted data
            if query_upper.startswith('INSERT') and results['affected_rows'] > 0:
                try:
                    verify = input(f"{Fore.CYAN}是否要查看刚刚添加的数据来确认? (y/N): ").strip().lower()
                    if verify in ['y', 'yes', '是', '确认']:
                        self._verify_insert_operation(sql_query)
                except KeyboardInterrupt:
                    pass
    
    def _verify_insert_operation(self, insert_query: str):
        """Verify INSERT operation by showing the newly inserted data"""
        try:
            # Extract table name from INSERT query
            import re
            match = re.search(r'INSERT\s+INTO\s+(\w+)', insert_query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                verify_query = f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 3"
                
                print(f"{Fore.YELLOW}正在查询表 {table_name} 中最新的记录...")
                success, results, message = self.db_manager.execute_query(verify_query)
                
                if success and results and 'data' in results and results['data']:
                    formatted_results = self.db_manager.format_results(results)
                    print(f"\n{Fore.GREEN}✅ 最新添加的记录:")
                    print(f"{Fore.WHITE}{formatted_results}")
                else:
                    print(f"{Fore.YELLOW}无法获取新添加的记录: {message}")
            else:
                print(f"{Fore.YELLOW}无法解析表名，跳过验证")
        except Exception as e:
            print(f"{Fore.YELLOW}验证时出现错误: {str(e)}")
    
    def _ask_continue(self) -> bool:
        """Step 6: Ask if further operation is needed"""
        print(f"\n{Fore.CYAN}{'='*60}")
        try:
            continue_choice = input(f"{Fore.CYAN}您还需要进行其他操作吗? (Y/n): ").strip().lower()
            return continue_choice not in ['n', 'no', 'exit', 'quit', '不', '否', '退出', '结束']
        except KeyboardInterrupt:
            return False
    
    def shutdown(self):
        """Clean shutdown"""
        print(f"\n{Fore.YELLOW}正在关闭ChatCRM...")
        if self.auth_manager.is_authenticated():
            self.auth_manager.logout()
        if self.db_manager.is_connected:
            self.db_manager.disconnect()
        print(f"{Fore.GREEN}感谢使用ChatCRM!")

def main():
    """Main entry point"""
    try:
        crm = ChatCRM()
        crm.run()
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 