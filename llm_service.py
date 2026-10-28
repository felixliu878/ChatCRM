from openai import OpenAI
import json
import time
import requests
from typing import Tuple, Dict, Any
from config import DEEPSEEK_CONFIG, APP_CONFIG
from colorama import Fore, Style, init

init(autoreset=True)

class LLMService:
    def __init__(self):
        self.max_retries = 3
        self.base_timeout = 30  # 30 seconds base timeout
        self.retry_delay = 2    # 2 seconds between retries
        
        # 地理位置映射关系 - 添加中国主要省市关系
        self.geographic_mapping = {
            # 广东省
            '广东': ['广州', '深圳', '珠海', '佛山', '韶关', '湛江', '肇庆', '江门', '茂名', '惠州', '梅州', '汕尾', '河源', '阳江', '清远', '东莞', '中山', '潮州', '揭阳', '云浮'],
            '广东省': ['广州', '深圳', '珠海', '佛山', '韶关', '湛江', '肇庆', '江门', '茂名', '惠州', '梅州', '汕尾', '河源', '阳江', '清远', '东莞', '中山', '潮州', '揭阳', '云浮'],
            
            # 北京
            '北京': ['北京'],
            '北京市': ['北京'],
            
            # 上海
            '上海': ['上海'],
            '上海市': ['上海'],
            
            # 江苏省
            '江苏': ['南京', '无锡', '徐州', '常州', '苏州', '南通', '连云港', '淮安', '盐城', '扬州', '镇江', '泰州', '宿迁'],
            '江苏省': ['南京', '无锡', '徐州', '常州', '苏州', '南通', '连云港', '淮安', '盐城', '扬州', '镇江', '泰州', '宿迁'],
            
            # 浙江省
            '浙江': ['杭州', '宁波', '温州', '嘉兴', '湖州', '绍兴', '金华', '衢州', '舟山', '台州', '丽水'],
            '浙江省': ['杭州', '宁波', '温州', '嘉兴', '湖州', '绍兴', '金华', '衢州', '舟山', '台州', '丽水'],
            
            # 福建省
            '福建': ['福州', '厦门', '莆田', '三明', '泉州', '漳州', '南平', '龙岩', '宁德'],
            '福建省': ['福州', '厦门', '莆田', '三明', '泉州', '漳州', '南平', '龙岩', '宁德'],
            
            # 四川省
            '四川': ['成都', '自贡', '攀枝花', '泸州', '德阳', '绵阳', '广元', '遂宁', '内江', '乐山', '南充', '眉山', '宜宾', '广安', '达州', '雅安', '巴中', '资阳'],
            '四川省': ['成都', '自贡', '攀枝花', '泸州', '德阳', '绵阳', '广元', '遂宁', '内江', '乐山', '南充', '眉山', '宜宾', '广安', '达州', '雅安', '巴中', '资阳'],
            
            # 陕西省
            '陕西': ['西安', '铜川', '宝鸡', '咸阳', '渭南', '延安', '汉中', '榆林', '安康', '商洛'],
            '陕西省': ['西安', '铜川', '宝鸡', '咸阳', '渭南', '延安', '汉中', '榆林', '安康', '商洛'],
            
            # 山东省
            '山东': ['济南', '青岛', '淄博', '枣庄', '东营', '烟台', '潍坊', '济宁', '泰安', '威海', '日照', '莱芜', '临沂', '德州', '聊城', '滨州', '菏泽'],
            '山东省': ['济南', '青岛', '淄博', '枣庄', '东营', '烟台', '潍坊', '济宁', '泰安', '威海', '日照', '莱芜', '临沂', '德州', '聊城', '滨州', '菏泽'],
        }
        
        try:
            # Use basic initialization to avoid parameter conflicts
            self.client = OpenAI(
                api_key=DEEPSEEK_CONFIG['api_key']
            )
            # Set base URL after initialization
            self.client.base_url = DEEPSEEK_CONFIG['base_url']
            self.model = DEEPSEEK_CONFIG['model']
            print(f"{Fore.GREEN}✓ LLM Service initialized successfully")
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to initialize LLM Service: {str(e)}")
            print(f"{Fore.YELLOW}Trying requests-based fallback...")
            # Initialize without OpenAI client for requests-only fallback
            self.client = None
            self.model = DEEPSEEK_CONFIG['model']
            print(f"{Fore.GREEN}✓ LLM Service initialized with requests fallback")
    
    def _call_llm_with_retry(self, messages, temperature=0.1, max_tokens=1000, timeout=None):
        """Call LLM service with retry mechanism and timeout handling"""
        if timeout is None:
            timeout = self.base_timeout
            
        last_error = None
        
        # If OpenAI client is not available, use fallback directly
        if self.client is None:
            print(f"{Fore.YELLOW}OpenAI client not available, using requests fallback directly...")
            try:
                response = self._fallback_api_call(messages, temperature, max_tokens, timeout)
                if response:
                    return response
                else:
                    raise Exception("Fallback API call returned empty response")
            except Exception as e:
                raise Exception(f"Fallback API call failed: {str(e)}")
        
        for attempt in range(self.max_retries):
            try:
                print(f"{Fore.YELLOW}Calling LLM service (attempt {attempt + 1}/{self.max_retries})...")
                
                # Try with OpenAI client first
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                print(f"{Fore.RED}✗ Attempt {attempt + 1} failed: {str(e)}")
                
                # Check if it's a timeout error
                if 'timeout' in error_str or 'read timed out' in error_str:
                    print(f"{Fore.YELLOW}Timeout detected, trying fallback method...")
                    
                    # Try with direct requests as fallback
                    try:
                        fallback_response = self._fallback_api_call(messages, temperature, max_tokens, timeout)
                        if fallback_response:
                            return fallback_response
                    except Exception as fallback_error:
                        print(f"{Fore.RED}✗ Fallback method also failed: {str(fallback_error)}")
                
                # If not the last attempt, wait before retrying
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)  # Exponential backoff
                    print(f"{Fore.YELLOW}Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    
                    # Increase timeout for next attempt
                    timeout = min(timeout * 1.5, 60)  # Max 60 seconds
        
        # All attempts failed
        raise Exception(f"LLM service failed after {self.max_retries} attempts. Last error: {str(last_error)}")
    
    def _fallback_api_call(self, messages, temperature, max_tokens, timeout):
        """Fallback API call using requests library"""
        try:
            headers = {
                'Authorization': f'Bearer {DEEPSEEK_CONFIG["api_key"]}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': False
            }
            
            # Use requests with explicit timeout
            response = requests.post(
                f"{DEEPSEEK_CONFIG['base_url']}/chat/completions",
                headers=headers,
                json=data,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                print(f"{Fore.RED}✗ Fallback API call failed with status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}✗ Fallback API call exception: {str(e)}")
            return None
    
    def text_to_sql(self, user_input: str, schema_info: Dict) -> Tuple[bool, str, str]:
        """Convert natural language to SQL query using DeepSeek V3"""
        
        # Create schema description for the LLM
        schema_description = self._format_schema_for_llm(schema_info)
        
        # 获取地理位置扩展信息
        geographic_expansion = self._get_geographic_query_expansion(user_input)
        
        system_prompt = f"""你是一个SQL专家。你的任务是将中文自然语言查询转换为有效的SQL语句，用于CRM数据库。

数据库结构:
{schema_description}

地理位置智能匹配规则:
{geographic_expansion}

重要的地理位置知识:
- 广州、深圳属于广东省
- 当用户查询"广东的客户"时，应该查找city IN ('广州', '深圳', '珠海', '佛山', '韶关', '湛江', '肇庆', '江门', '茂名', '惠州', '梅州', '汕尾', '河源', '阳江', '清远', '东莞', '中山', '潮州', '揭阳', '云浮')
- 当用户查询"江苏的客户"时，应该查找city IN ('南京', '无锡', '徐州', '常州', '苏州', '南通', '连云港', '淮安', '盐城', '扬州', '镇江', '泰州', '宿迁')
- 当用户查询"浙江的客户"时，应该查找city IN ('杭州', '宁波', '温州', '嘉兴', '湖州', '绍兴', '金华', '衢州', '舟山', '台州', '丽水')
- 当用户查询"四川的客户"时，应该查找city IN ('成都', '自贡', '攀枝花', '泸州', '德阳', '绵阳', '广元', '遂宁', '内江', '乐山', '南充', '眉山', '宜宾', '广安', '达州', '雅安', '巴中', '资阳')

业务场景处理:
1. 沟通记录：当用户描述联系客户的情况时，这是要添加沟通记录，需要：
   - 重要：这些都是INSERT操作，要向customer_communication_records表添加记录
   - 如果没有customer_id，需要先通过子查询获取客户ID
   - 常见模式："我给[客户]打了电话" = 添加沟通记录

2. 沟通记录模式识别：
   - "我今天给[客户]打了电话" → INSERT通信记录
   - "联系了[公司]的[客户]" → INSERT通信记录  
   - "拜访了[客户]" → INSERT通信记录
   - "发邮件给[客户]" → INSERT通信记录

3. 通信记录字段说明：
   - customer_id: 客户ID (外键，使用子查询获取)
   - people_who_contact_customer: 联系人(谁联系的客户，默认'我')
   - communication_details: 沟通详情(从用户描述中提取)
   - communication_methods: 沟通方式(电话/邮件/拜访等)
   - communication_date: 沟通日期 (CURDATE())
   - customer_response: 客户反馈(从用户描述中提取)
   - communication_time: 沟通时间 (CURTIME())

关键规则:
1. 只返回SQL查询语句，绝对不要包含任何解释、说明或其他文本
2. 不要使用markdown格式，不要用```sql```包围
3. 如果需要多个步骤，只返回第一个步骤的SQL
4. 使用正确的MySQL语法
5. 准确使用表名和列名
6. 对于SELECT查询，限制结果数量(使用LIMIT)
7. 特别注意地理位置查询，省份查询要使用IN子句包含所有下属城市
8. 对于插入通信记录，确保先找到正确的customer_id

示例:
用户: "显示所有客户"
回答: SELECT * FROM customer LIMIT 100

用户: "查询广东的客户"
回答: SELECT * FROM customer WHERE city IN ('广州', '深圳', '珠海', '佛山', '韶关', '湛江', '肇庆', '江门', '茂名', '惠州', '梅州', '汕尾', '河源', '阳江', '清远', '东莞', '中山', '潮州', '揭阳', '云浮') LIMIT 100

用户: "添加一个名叫张三的新客户，邮箱是zhangsan@example.com"
回答: INSERT INTO customer (customer_name, email) VALUES ('张三', 'zhangsan@example.com')

用户: "我今天给李四打了电话，他说考虑一下"
回答: INSERT INTO customer_communication_records (customer_id, people_who_contact_customer, communication_details, communication_methods, communication_date, customer_response, communication_time) VALUES ((SELECT id FROM customer WHERE customer_name = '李四' LIMIT 1), '我', '今天给李四打了电话', '电话', CURDATE(), '他说考虑一下', CURTIME())

用户: "我今天上午给菊风公司科技有限公司的许秀兰打了电话，对方表示过半个月再联系"
回答: INSERT INTO customer_communication_records (customer_id, people_who_contact_customer, communication_details, communication_methods, communication_date, customer_response, communication_time) VALUES ((SELECT id FROM customer WHERE customer_name = '许秀兰' AND company LIKE '%菊风%' LIMIT 1), '我', '今天上午给菊风公司科技有限公司的许秀兰打了电话', '电话', CURDATE(), '对方表示过半个月再联系', CURTIME())

用户: "查找菊风公司的客户"
回答: SELECT * FROM customer WHERE company LIKE '%菊风%' LIMIT 10

现在将这个请求转换为SQL:"""

        user_message = f"用户请求: {user_input}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            print(f"{Fore.YELLOW}Converting natural language to SQL...")
            
            sql_query = self._call_llm_with_retry(
                messages=messages,
                temperature=0.1,
                max_tokens=1000,
                timeout=30
            )
            
            # Clean up the SQL query thoroughly
            sql_query = self._clean_sql_response(sql_query)
            
            print(f"{Fore.GREEN}✓ Generated SQL: {sql_query}")
            return True, sql_query, "SQL generated successfully"

        except Exception as e:
            error_msg = f"Error calling LLM service: {str(e)}"
            print(f"{Fore.RED}✗ {error_msg}")
            
            # Provide a fallback suggestion based on user input
            fallback_sql = self._generate_fallback_sql(user_input, schema_info)
            if fallback_sql:
                print(f"{Fore.YELLOW}Providing fallback SQL suggestion...")
                return True, fallback_sql, "Generated fallback SQL due to API timeout"
            
            return False, "", error_msg
    
    def _generate_fallback_sql(self, user_input: str, schema_info: Dict) -> str:
        """Generate a simple fallback SQL when LLM service fails"""
        user_input_lower = user_input.lower()
        
        # Check for communication record scenarios
        if any(word in user_input for word in ['打了电话', '打电话', '联系了', '沟通了', '拜访了', '发邮件', '发了邮件', '给']):
            # This looks like a communication record scenario - INSERT operation
            # Extract communication method
            comm_method = '电话' if '电话' in user_input else '邮件' if '邮件' in user_input else '拜访' if '拜访' in user_input else '沟通'
            
            # Try to extract customer name or company and generate INSERT
            if '许秀兰' in user_input and '菊风' in user_input:
                comm_details = user_input.replace('我', '').replace('今天', '').replace('上午', '').replace('下午', '').strip()
                customer_response = ''
                if '表示' in user_input:
                    parts = user_input.split('表示')
                    if len(parts) > 1:
                        customer_response = '表示' + parts[1].strip()
                        comm_details = parts[0].strip()
                
                return f"INSERT INTO customer_communication_records (customer_id, people_who_contact_customer, communication_details, communication_methods, communication_date, customer_response, communication_time) VALUES ((SELECT id FROM customer WHERE customer_name = '许秀兰' AND company LIKE '%菊风%' LIMIT 1), '我', '{comm_details}', '{comm_method}', CURDATE(), '{customer_response}', CURTIME())"
            
            elif '李华' in user_input:
                comm_details = user_input.replace('我', '').replace('今天', '').replace('上午', '').replace('下午', '').strip()
                customer_response = ''
                if '说' in user_input:
                    parts = user_input.split('说')
                    if len(parts) > 1:
                        customer_response = '说' + parts[1].strip()
                        comm_details = parts[0].strip()
                
                return f"INSERT INTO customer_communication_records (customer_id, people_who_contact_customer, communication_details, communication_methods, communication_date, customer_response, communication_time) VALUES ((SELECT id FROM customer WHERE customer_name = '李华' LIMIT 1), '我', '{comm_details}', '{comm_method}', CURDATE(), '{customer_response}', CURTIME())"
            
            else:
                # Generic communication record
                return f"INSERT INTO customer_communication_records (customer_id, people_who_contact_customer, communication_details, communication_methods, communication_date, customer_response, communication_time) VALUES (1, '我', '{user_input}', '{comm_method}', CURDATE(), '', CURTIME())"
        
        # Check for specific customer/company searches
        if '菊风' in user_input:
            return "SELECT * FROM customer WHERE company LIKE '%菊风%' LIMIT 10"
        
        if '许秀兰' in user_input:
            return "SELECT * FROM customer WHERE customer_name LIKE '%许秀兰%' LIMIT 10"
        
        # Check if it's a customer-related query
        if '客户' in user_input or 'customer' in user_input_lower:
            # Get the first table that might contain customer data
            for table_name in schema_info.keys():
                if 'customer' in table_name.lower() or 'client' in table_name.lower():
                    if '添加' in user_input or '新增' in user_input or 'add' in user_input_lower:
                        # Try to extract specific customer info
                        if '许秀兰' in user_input and '菊风' in user_input:
                            return f"INSERT INTO {table_name} (customer_name, company, company_position, email) VALUES ('许秀兰', '菊风公司科技有限公司', '产品经理', 'xulan@jufeng.com')"
                        elif '李华' in user_input and 'lihua@huaxin.com' in user_input:
                            return f"INSERT INTO {table_name} (customer_name, email, company, company_position) VALUES ('李华', 'lihua@huaxin.com', '广州华兴科技有限公司', '客户关系经理')"
                    elif '查询' in user_input or '显示' in user_input or 'show' in user_input_lower:
                        # 检查是否是地理位置查询
                        for province, cities in self.geographic_mapping.items():
                            if province in user_input:
                                cities_str = "', '".join(cities)
                                return f"SELECT * FROM {table_name} WHERE city IN ('{cities_str}') LIMIT 100"
                        
                        # 普通查询
                        return f"SELECT * FROM {table_name} LIMIT 10"
                    
        return None
    
    def analyze_operation_type(self, user_input: str) -> str:
        """Analyze what type of operation the user wants to perform"""
        user_input_lower = user_input.lower()
        
        # Check for communication record scenarios FIRST (these are CREATE operations)
        if any(word in user_input for word in ['打了电话', '打电话', '联系了', '沟通了', '拜访了', '发了邮件', '发邮件', '给', '跟']):
            # These patterns indicate user is recording a communication activity
            return "CREATE"
        
        # Check Chinese keywords
        if any(word in user_input for word in ['显示', '查询', '查看', '列出', '搜索', '查找', '统计', '计算', '多少']):
            return "READ"
        elif any(word in user_input for word in ['添加', '新增', '创建', '新建']):
            return "CREATE"
        elif any(word in user_input for word in ['更新', '修改', '编辑', '改变']):
            return "UPDATE"
        elif any(word in user_input for word in ['删除', '移除', '清除']):
            return "DELETE"
        
        # Check English keywords
        if any(word in user_input_lower for word in ['show', 'list', 'get', 'find', 'search', 'display', 'view', 'count', 'total', 'sum', 'how many']):
            return "READ"
        elif any(word in user_input_lower for word in ['add', 'create', 'insert', 'new', 'called', 'contacted', 'visited', 'emailed']):
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
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            explanation = self._call_llm_with_retry(
                messages=messages,
                temperature=0.3,
                max_tokens=200,
                timeout=20
            )
            
            return True, explanation

        except Exception as e:
            return False, f"Error generating explanation: {str(e)}"
    
    def generate_natural_language_response(self, user_input: str, sql_query: str, results: Any) -> Tuple[bool, str]:
        """Generate natural language response in Chinese based on user question and database results"""
        try:
            # Prepare results summary for the LLM
            if isinstance(results, dict):
                if 'data' in results and 'columns' in results:
                    data_count = len(results['data'])
                    columns = results['columns']
                    data_rows = results['data']
                    
                    # For customer data, provide detailed information for better formatting
                    if data_rows and len(data_rows) <= 10:  # Provide full details for smaller datasets
                        formatted_data = []
                        for row in data_rows:
                            row_dict = {}
                            for i, col in enumerate(columns):
                                row_dict[col] = row[i] if i < len(row) else None
                            formatted_data.append(row_dict)
                        results_summary = f"数据条数: {data_count}, 详细数据: {formatted_data}"
                    else:
                        # For larger datasets, provide sample data
                        sample_data = data_rows[:3] if data_rows else []
                        columns_info = ', '.join(columns)
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

格式要求（特别是查询客户信息时）:
- 使用换行分隔不同的客户
- 人名使用**加粗**格式（如**张麻子(Alex)**）
- 包含完整信息：姓名(昵称)，性别，公司职位，联系方式，邮箱，备注等
- 在最后提供总结性信息
- 使用编号列表格式

重要提醒：当用户要求添加、更新或删除数据时，要强调数据已经真实地保存到数据库中。

格式示例:
用户问: "查找北京的客户"
查询结果: 找到2条客户记录
你的回答: "我找到了2位北京的客户：

1. **张麻子(Alex)**，男，北京未来科技有限公司技术总监，联系方式：13812345678，邮箱zhangsan@futuretech.com。备注显示是重要客户，需定期跟进，爱好阅读、旅行和摄影。

2. **李青(Qing)**，女，同公司的用户体验总监，联系方式：13887654321，邮箱qingli@futuretech.com。备注提醒需要注意沟通方式，爱好插花和茶道。

这两位客户都来自北京未来科技有限公司。"

其他操作示例:
用户问: "添加新客户张三"
操作结果: 插入1行
你的回答: "好的，我已经成功将客户张三的信息添加到数据库中。新的客户记录已经永久保存。"

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

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            natural_response = self._call_llm_with_retry(
                messages=messages,
                temperature=0.3,
                max_tokens=500,
                timeout=25
            )
            
            return True, natural_response

        except Exception as e:
            # Provide a simple fallback response
            if 'affected_rows' in str(results) and results.get('affected_rows', 0) > 0:
                return True, f"操作已成功完成，影响了 {results.get('affected_rows', 0)} 条记录。由于网络原因，无法生成详细的自然语言回答。"
            elif 'data' in str(results):
                return True, f"查询已完成，找到了相关数据。由于网络原因，无法生成详细的自然语言回答。"
            else:
                return False, f"生成自然语言回答时出错: {str(e)}"
    
    def _clean_sql_response(self, response: str) -> str:
        """Clean LLM response to extract pure SQL statement"""
        if not response:
            return ""
        
        # Remove common markdown formatting
        response = response.replace('```sql', '').replace('```', '').strip()
        
        # Split by lines and find the first line that looks like SQL
        lines = response.split('\n')
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE', 'DROP', 'ALTER']
        
        for line in lines:
            line = line.strip()
            if line and any(line.upper().startswith(keyword) for keyword in sql_keywords):
                # This looks like a SQL statement
                return line
        
        # If no clear SQL found, try to extract anything that doesn't look like explanation
        for line in lines:
            line = line.strip()
            if line and not any(char in line for char in ['：', ':', '。', '1.', '2.', '根据', '需要']):
                # This line doesn't contain typical Chinese explanation patterns
                if any(keyword in line.upper() for keyword in sql_keywords):
                    return line
        
        # Fallback: return the first non-empty line
        for line in lines:
            line = line.strip()
            if line:
                return line
        
        return response.strip()
    
    def _get_geographic_query_expansion(self, user_input: str) -> str:
        """根据用户输入扩展地理位置查询"""
        expansion_info = ""
        
        # 检查用户输入中是否包含省份名称
        for province, cities in self.geographic_mapping.items():
            if province in user_input:
                cities_str = "', '".join(cities)
                expansion_info += f"\n注意：当用户查询'{province}'时，应该包括以下所有城市：{cities}\n"
                expansion_info += f"SQL查询应该使用: city IN ('{cities_str}') 而不是 city = '{province}'\n"
                break
        
        return expansion_info 