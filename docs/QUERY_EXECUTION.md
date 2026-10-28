# Query execution rules

Read-only requests run immediately. Anything that changes data needs the user's confirmation first.

## How a request is classified

Classification happens in two steps:

1. **Intent guess from the request** (`LLMService.analyze_operation_type`). Keyword matching on the request text. The English keywords are listed below; equivalent Chinese keywords are matched as well.

   | Type | Keywords |
   |---|---|
   | READ | show, list, get, find, search, display, view, count, total, sum, how many |
   | CREATE | add, create, insert, new |
   | UPDATE | update, modify, change, edit |
   | DELETE | delete, remove, drop |

   Sentences that describe an interaction, such as "called", "contacted", "visited", or "emailed", are treated as CREATE, because they are logged as communication records.

2. **Check against the generated SQL** (`DatabaseManager.operation_type_from_sql`). Only statements that begin with `SELECT`, `SHOW`, or `DESCRIBE` count as read-only. If the generated SQL is a write (`INSERT`, `UPDATE`, `DELETE`, or anything else), the SQL's type overrides the keyword guess. A request phrased as a query therefore can never run a write statement without confirmation.

## What the user sees

**Read-only request**
1. User: "Show all customers"
2. The query runs and the results are returned immediately.

**Write request**
1. User: "Add a new customer, Zhang San, …"
2. The assistant shows the operation type and the exact SQL and asks for confirmation.
3. The user confirms or cancels.
4. On confirmation, the SQL runs and the affected-row count and a summary are returned.

The same rules apply in the web app (`WebChatCRM.process_message` in `app.py`) and the terminal app (`ChatCRM._process_user_operation` in `main.py`).

## Examples

| Request | Classified as | Confirmation |
|---|---|---|
| Show all customers | READ | No |
| Find customers in Beijing | READ | No |
| How many customers are there? | READ | No |
| Add a new customer | CREATE | Yes |
| I called Zhang San | CREATE (communication record) | Yes |
| Change a phone number | UPDATE | Yes |
| Delete a customer | DELETE | Yes |
