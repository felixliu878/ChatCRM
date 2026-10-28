import requests
import json
from typing import Tuple, Dict, Any
from config import DEEPSEEK_CONFIG, APP_CONFIG
from colorama import Fore, Style, init

init(autoreset=True)

class LLMServiceFallback:
    """Fallback LLM service using requests library"""
    def __init__(self):
        self.api_key = DEEPSEEK_CONFIG['api_key']
        self.base_url = DEEPSEEK_CONFIG['base_url']
        self.model = DEEPSEEK_CONFIG['model']
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        print(f"{Fore.GREEN}✓ Fallback LLM Service initialized successfully")
    
    def text_to_sql(self, user_input: str, schema_info: Dict) -> Tuple[bool, str, str]:
        """Convert natural language to SQL query using DeepSeek V3"""
        
        # Create schema description for the LLM
        schema_description = self._format_schema_for_llm(schema_info)
        
        system_prompt = f"""你是一个SQL专家。你的任务是将中文自然语言查询转换为有效的SQL语句，用于CRM数据库。

数据库结构:
{schema_description}

规则:
1. 只返回SQL查询语句，不要其他内容
2. 使用正确的MySQL语法
3. 准确使用表名和列名
4. 对于SELECT查询，限制结果数量(使用LIMIT)
5. 始终使用安全的SQL实践
6. 如果请求不明确，如用户说要添加客户但没有给出信息，先询问用户相关信息

示例:
用户: "显示所有客户"
回答: SELECT * FROM customers LIMIT 100

用户: "添加一个名叫张三的新客户，邮箱是zhangsan@example.com"
回答: INSERT INTO customers (name, email) VALUES ('张三', 'zhangsan@example.com')

现在将这个请求转换为SQL:"""

        user_message = f"用户请求: {user_input}"

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            }

            print(f"{Fore.YELLOW}Converting natural language to SQL (using fallback method)...")
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=APP_CONFIG['timeout']
            )

            if response.status_code == 200:
                result = response.json()
                sql_query = result['choices'][0]['message']['content'].strip()
                
                # Clean up the SQL query (remove any markdown formatting)
                sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
                
                print(f"{Fore.GREEN}✓ Generated SQL: {sql_query}")
                return True, sql_query, "SQL generated successfully"
            else:
                error_msg = f"LLM API error: {response.status_code} - {response.text}"
                print(f"{Fore.RED}✗ {error_msg}")
                return False, "", error_msg

        except Exception as e:
            error_msg = f"Error calling LLM service: {str(e)}"
            print(f"{Fore.RED}✗ {error_msg}")
            return False, "", error_msg
    
    def analyze_operation_type(self, user_input: str) -> str:
        """Analyze what type of operation the user wants to perform"""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['show', 'list', 'get', 'find', 'search', 'display', 'view']):
            return "READ"
        elif any(word in user_input_lower for word in ['add', 'create', 'insert', 'new']):
            return "CREATE"
        elif any(word in user_input_lower for word in ['update', 'modify', 'change', 'edit']):
            return "UPDATE"
        elif any(word in user_input_lower for word in ['delete', 'remove', 'drop']):
            return "DELETE"
        else:
            return "UNKNOWN"
    
    def _format_schema_for_llm(self, schema_info: Dict) -> str:
        """Format database schema information for the LLM prompt"""
        if not schema_info:
            return "No schema information available."
        
        schema_text = ""
        for table_name, columns in schema_info.items():
            schema_text += f"\nTable: {table_name}\n"
            schema_text += "Columns:\n"
            for col in columns:
                key_info = f" ({col['key']})" if col['key'] else ""
                null_info = "NOT NULL" if col['null'] == 'NO' else "NULL"
                schema_text += f"  - {col['column']}: {col['type']} {null_info}{key_info}\n"
        
        return schema_text
    
    def generate_explanation(self, sql_query: str, results: Any) -> Tuple[bool, str]:
        """Generate human-readable explanation of what was done"""
        try:
            system_prompt = """You are a helpful assistant that explains database operations in simple terms.
Given a SQL query and its results, provide a brief, user-friendly explanation of what was accomplished.
Keep it concise and easy to understand."""

            user_message = f"SQL Query: {sql_query}\nResults summary: {str(results)[:500]}"

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.3,
                "max_tokens": 200
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=APP_CONFIG['timeout']
            )

            if response.status_code == 200:
                result = response.json()
                explanation = result['choices'][0]['message']['content'].strip()
                return True, explanation
            else:
                return False, "Could not generate explanation"

        except Exception as e:
            return False, f"Error generating explanation: {str(e)}"
    
    def generate_natural_language_response(self, user_input: str, sql_query: str, results: Any) -> Tuple[bool, str]:
        """Generate natural language response in Chinese based on user question and database results"""
        try:
            # Prepare results summary for the LLM
            if isinstance(results, dict):
                if 'data' in results and 'columns' in results:
                    data_count = len(results['data'])
                    columns_info = ', '.join(results['columns'])
                    
                    # Limit the data shown to LLM to avoid token limits
                    sample_data = results['data'][:5] if results['data'] else []
                    results_summary = f"数据条数: {data_count}, 列: {columns_info}, 样本数据: {sample_data}"
                elif 'affected_rows' in results:
                    results_summary = f"影响的行数: {results['affected_rows']}"
                else:
                    results_summary = str(results)
            else:
                results_summary = str(results)

            system_prompt = """你是一个友好的CRM助手。用户向你提出了关于CRM数据的问题，你已经执行了相应的SQL查询并获得了结果。
现在请用自然、友好的中文回答用户的问题。

要求:
1. 直接回答用户的问题，不要显示SQL查询
2. 用自然语言描述查询结果
3. 如果有数据，要提供有用的信息总结
4. 如果没有找到数据，要礼貌地告知
5. 如果是增删改操作，要明确确认操作已经成功执行并影响了数据库
6. 保持回答简洁明了，专业友好

重要提醒：当用户要求添加、更新或删除数据时，要强调数据已经真实地保存到数据库中。

示例:
用户问: "显示所有客户"
查询结果: 找到100条客户记录
你的回答: "我找到了100位客户。这些客户包括..."

用户问: "添加新客户张三"
操作结果: 插入1行
你的回答: "好的，我已经成功将客户张三的信息添加到数据库中。新的客户记录已经永久保存。"

用户问: "添加新客户"
你的回答: "好的，请提供用户信息。"

用户问: "更新客户信息"
操作结果: 更新2行
你的回答: "已成功更新了2位客户的信息，所有更改已保存到数据库中。"

用户问: "删除过期数据"
操作结果: 删除5行
你的回答: "已成功从数据库中删除了5条过期记录。"
"""

            user_message = f"""用户的问题: {user_input}
执行的SQL: {sql_query}
查询结果: {results_summary}

请用自然语言回答用户的问题:"""

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=APP_CONFIG['timeout']
            )

            if response.status_code == 200:
                result = response.json()
                natural_response = result['choices'][0]['message']['content'].strip()
                return True, natural_response
            else:
                return False, "生成自然语言回答失败"

        except Exception as e:
            return False, f"生成自然语言回答时出错: {str(e)}" 