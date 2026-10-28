from typing import Tuple
from colorama import Fore, Style, init
import getpass

init(autoreset=True)

class AuthManager:
    def __init__(self, database_manager=None):
        # Database-based authentication
        self.db_manager = database_manager
        self.current_user = None
    
    def login(self) -> Tuple[bool, str]:
        """Handle user login process following the flowchart logic"""
        print(f"\n{Fore.CYAN}=== ChatCRM 登录 ===")
        print(f"{Fore.YELLOW}请输入您的登录凭据以访问CRM系统")
        
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            try:
                # Ask user to input credentials
                username = input(f"{Fore.WHITE}用户名: ").strip()
                password = getpass.getpass(f"{Fore.WHITE}密码: ")
                
                # Validate credentials
                if self._validate_credentials(username, password):
                    self.current_user = username
                    print(f"{Fore.GREEN}✓ 登录成功! 欢迎您, {username}!")
                    return True, f"成功登录为 {username}"
                else:
                    attempts += 1
                    remaining = max_attempts - attempts
                    if remaining > 0:
                        print(f"{Fore.RED}✗ 登录凭据无效。还有 {remaining} 次尝试机会。")
                    else:
                        print(f"{Fore.RED}✗ 超过最大登录尝试次数。")
                        return False, "登录失败: 超过最大尝试次数"
                        
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}用户取消登录。")
                return False, "登录已取消"
            except Exception as e:
                print(f"{Fore.RED}✗ 登录错误: {str(e)}")
                return False, f"登录错误: {str(e)}"
        
        return False, "登录失败"
    
    def _validate_credentials(self, username: str, password: str) -> bool:
        """Validate user credentials against database"""
        if not self.db_manager or not self.db_manager.is_connected:
            print(f"{Fore.RED}数据库未连接，无法验证用户凭据")
            return False
        
        try:
            # Query the user table to find matching credentials
            query = "SELECT user_name, user_pwd FROM user WHERE user_name = %s"
            
            # Execute query safely with parameter binding
            success, result, msg = self.db_manager.execute_query_with_params(query, (username,))
            
            if not success:
                print(f"{Fore.RED}查询用户信息失败: {msg}")
                return False
            
            if not result or 'data' not in result or not result['data']:
                print(f"{Fore.RED}用户 '{username}' 不存在")
                return False
            
            # Check if password matches
            user_data = result['data'][0]
            stored_username = user_data[0]
            stored_password = user_data[1]
            
            if stored_username == username and stored_password == password:
                return True
            else:
                print(f"{Fore.RED}密码错误")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}验证用户凭据时出错: {str(e)}")
            return False
    
    def logout(self):
        """Logout current user"""
        if self.current_user:
            print(f"{Fore.YELLOW}再见, {self.current_user}!")
            self.current_user = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.current_user is not None
    
    def get_current_user(self) -> str:
        """Get current authenticated user"""
        return self.current_user or "Anonymous"
    
    def show_demo_credentials(self):
        """Show available users from database"""
        print(f"\n{Fore.CYAN}=== 可用用户账户 ===")
        
        if not self.db_manager or not self.db_manager.is_connected:
            print(f"{Fore.YELLOW}数据库未连接，无法显示用户信息")
            print(f"{Fore.YELLOW}请确保数据库连接正常后重试")
            print(f"{Fore.CYAN}===================\n")
            return
        
        try:
            # First check if user table exists
            check_table_query = "SHOW TABLES LIKE 'user'"
            table_success, table_result, table_msg = self.db_manager.execute_query(check_table_query)
            
            if not table_success or not table_result or 'data' not in table_result or not table_result['data']:
                print(f"{Fore.RED}错误: 数据库中未找到 'user' 表")
                print(f"{Fore.YELLOW}请确保数据库中存在包含以下列的 'user' 表:")
                print(f"{Fore.WHITE}  - user_name (用户名)")
                print(f"{Fore.WHITE}  - user_pwd (密码)")
                print(f"{Fore.CYAN}===================\n")
                return
            
            # Query all users from database
            query = "SELECT user_name FROM user LIMIT 10"
            success, result, msg = self.db_manager.execute_query(query)
            
            if success and result and 'data' in result and result['data']:
                print(f"{Fore.YELLOW}数据库中的用户账户:")
                for row in result['data']:
                    username = row[0]
                    print(f"{Fore.WHITE}用户名: {username}")
                print(f"{Fore.YELLOW}请使用对应的密码登录")
            else:
                print(f"{Fore.YELLOW}未找到用户账户或查询失败: {msg}")
                print(f"{Fore.YELLOW}请联系管理员检查用户表")
                
        except Exception as e:
            print(f"{Fore.RED}获取用户信息时出错: {str(e)}")
            print(f"{Fore.YELLOW}请联系管理员检查数据库配置")
        
        print(f"{Fore.CYAN}===================\n") 