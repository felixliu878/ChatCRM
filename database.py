import pymysql
import json
from typing import List, Dict, Any, Optional, Tuple
from config import DB_CONFIG, APP_CONFIG
from colorama import Fore, Style, init

init(autoreset=True)

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.is_connected = False
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to the database"""
        try:
            print(f"{Fore.YELLOW}正在连接数据库...")
            self.connection = pymysql.connect(**DB_CONFIG)
            self.is_connected = True
            print(f"{Fore.GREEN}✓ 数据库连接成功!")
            return True, "数据库连接成功"
        except Exception as e:
            error_msg = f"Failed to connect to database: {str(e)}"
            print(f"{Fore.RED}✗ {error_msg}")
            return False, error_msg
    
    def disconnect(self):
        """Disconnect from the database"""
        if self.connection:
            self.connection.close()
            self.is_connected = False
            print(f"{Fore.YELLOW}已断开数据库连接")
    
    @staticmethod
    def is_read_only(query: str) -> bool:
        """Return True if the SQL statement only reads data."""
        return query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'DESC'))

    @staticmethod
    def operation_type_from_sql(query: str) -> str:
        """Classify a SQL statement as READ, CREATE, UPDATE, DELETE, or UNKNOWN."""
        if DatabaseManager.is_read_only(query):
            return 'READ'
        first_word = query.strip().split(None, 1)[0].upper() if query.strip() else ''
        return {'INSERT': 'CREATE', 'UPDATE': 'UPDATE', 'DELETE': 'DELETE'}.get(first_word, 'UNKNOWN')

    def execute_query(self, query: str) -> Tuple[bool, Any, str]:
        """Execute a SQL query and return results"""
        if not self.is_connected or not self.connection:
            return False, None, "Not connected to database"
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                
                # Check if this is a SELECT query or SHOW/DESCRIBE commands
                query_upper = query.strip().upper()
                if query_upper.startswith(('SELECT', 'SHOW', 'DESCRIBE', 'DESC')):
                    results = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    return True, {'columns': columns, 'data': results}, "Query executed successfully"
                else:
                    # For INSERT, UPDATE, DELETE queries
                    self.connection.commit()
                    affected_rows = cursor.rowcount
                    return True, {'affected_rows': affected_rows}, f"Query executed successfully. {affected_rows} rows affected."
                    
        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            print(f"{Fore.RED}✗ {error_msg}")
            return False, None, error_msg
    
    def execute_query_with_params(self, query: str, params: tuple = None) -> Tuple[bool, Any, str]:
        """Execute a SQL query with parameters to prevent SQL injection"""
        if not self.is_connected or not self.connection:
            return False, None, "Not connected to database"
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                
                # Check if this is a SELECT query or SHOW/DESCRIBE commands
                query_upper = query.strip().upper()
                if query_upper.startswith(('SELECT', 'SHOW', 'DESCRIBE', 'DESC')):
                    results = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    return True, {'columns': columns, 'data': results}, "Query executed successfully"
                else:
                    # For INSERT, UPDATE, DELETE queries
                    self.connection.commit()
                    affected_rows = cursor.rowcount
                    return True, {'affected_rows': affected_rows}, f"Query executed successfully. {affected_rows} rows affected."
                    
        except Exception as e:
            error_msg = f"Error executing parameterized query: {str(e)}"
            print(f"{Fore.RED}✗ {error_msg}")
            return False, None, error_msg
    
    def get_database_schema(self) -> Tuple[bool, Dict, str]:
        """Get database schema information for the LLM"""
        if not self.is_connected:
            return False, {}, "Not connected to database"
        
        try:
            schema_info = {}
            
            # Test basic connection first
            test_query = "SELECT 1 as test"
            test_success, test_result, test_msg = self.execute_query(test_query)
            if not test_success:
                return False, {}, f"Database connection test failed: {test_msg}"
            
            print(f"{Fore.GREEN}✓ 数据库连接测试通过")
            
            # Get all tables
            tables_query = "SHOW TABLES"
            print(f"{Fore.YELLOW}正在执行: {tables_query}")
            success, result, msg = self.execute_query(tables_query)
            
            if not success or result is None:
                return False, {}, f"Failed to get tables: {msg}"
            
            # Check if result has the expected structure
            if 'data' not in result:
                return False, {}, f"Unexpected result structure: {result}"
            
            tables = [row[0] for row in result['data']]
            print(f"{Fore.YELLOW}发现 {len(tables)} 个表: {', '.join(tables)}")
            
            # Get structure for each table
            for table in tables:
                describe_query = f"DESCRIBE {table}"
                success, result, msg = self.execute_query(describe_query)
                
                if success and result is not None and 'data' in result:
                    columns = []
                    for row in result['data']:
                        columns.append({
                            'column': row[0],
                            'type': row[1],
                            'null': row[2],
                            'key': row[3],
                            'default': row[4],
                            'extra': row[5]
                        })
                    schema_info[table] = columns
                    print(f"{Fore.YELLOW}  - {table}: {len(columns)} 列")
                else:
                    print(f"{Fore.RED}  - 获取表 {table} 结构失败: {msg}")
            
            return True, schema_info, "数据库结构获取成功"
            
        except Exception as e:
            error_msg = f"Error getting schema: {str(e)}"
            print(f"{Fore.RED}✗ {error_msg}")
            return False, {}, error_msg
    
    def format_results(self, results: Dict) -> str:
        """Format query results for display"""
        if 'columns' in results and 'data' in results:
            if not results['data']:
                return "No data found."
            
            # Create formatted table
            from tabulate import tabulate
            return tabulate(results['data'], headers=results['columns'], tablefmt='grid')
        elif 'affected_rows' in results:
            return f"Operation completed. {results['affected_rows']} rows affected."
        else:
            return str(results) 