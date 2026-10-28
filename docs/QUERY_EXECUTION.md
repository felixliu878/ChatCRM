# Query execution rules

Read-only requests run immediately. Anything that changes data needs the user's confirmation first.

## How a request is classified

Classification happens in two steps:

1. **Intent guess from the request** (`LLMService.analyze_operation_type`). Keyword matching in Chinese and English:

   | Type | Chinese keywords | English keywords |
   |---|---|---|
   | READ | 显示 show, 查询 query, 查看 view, 列出 list, 搜索 search, 查找 find, 统计 count, 计算 calculate, 多少 how many | show, list, get, find, search, display, view, count, total, sum, how many |
   | CREATE | 添加 add, 新增 add new, 创建 create, 新建 new | add, create, insert, new |
   | UPDATE | 更新 update, 修改 modify, 编辑 edit, 改变 change | update, modify, change, edit |
   | DELETE | 删除 delete, 移除 remove, 清除 clear | delete, remove, drop |

   Sentences that describe an interaction, such as 打了电话 "made a call", 联系了 "contacted", 拜访了 "visited", or 发了邮件 "sent an email", are treated as CREATE, because they are logged as communication records.

2. **Check against the generated SQL** (`DatabaseManager.operation_type_from_sql`). Only statements that begin with `SELECT`, `SHOW`, or `DESCRIBE` count as read-only. If the generated SQL is a write (`INSERT`, `UPDATE`, `DELETE`, or anything else), the SQL's type overrides the keyword guess. A request phrased as a query therefore can never run a write statement without confirmation.

## What the user sees

**Read-only request**
1. User: 显示所有客户 ("show all customers")
2. The query runs and the results are returned immediately.

**Write request**
1. User: 添加新客户张三… ("add a new customer Zhang San…")
2. The assistant shows the operation type and the exact SQL and asks for confirmation.
3. The user confirms or cancels.
4. On confirmation, the SQL runs and the affected-row count and a summary are returned.

The same rules apply in the web app (`WebChatCRM.process_message` in `app.py`) and the terminal app (`ChatCRM._process_user_operation` in `main.py`).

## Examples

| Request | Classified as | Confirmation |
|---|---|---|
| 显示所有客户 / show all customers | READ | No |
| 查询北京的客户 / find customers in Beijing | READ | No |
| 统计客户数量 / how many customers | READ | No |
| 添加新客户 / add a new customer | CREATE | Yes |
| 我给张三打了电话 / I called Zhang San | CREATE (communication record) | Yes |
| 修改电话号码 / change a phone number | UPDATE | Yes |
| 删除客户 / delete a customer | DELETE | Yes |
