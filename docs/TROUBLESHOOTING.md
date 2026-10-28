# Troubleshooting

The app's user-facing messages are in Chinese. Each one is quoted below with its English meaning.

## Nothing happens after confirming SQL

Common causes:

1. **Session ID mismatch** between the browser and the server
2. **Socket.IO connection dropped**
3. **Login state lost**, for example after a server restart
4. **Database connection lost**, so the server cannot run the SQL

### Step 1: use the test page

1. Open `http://localhost:5001/test`.
2. Click, in order:
   - **初始化会话** ("initialize session") to get a session ID
   - **连接WebSocket** ("connect WebSocket") to open the real-time connection
   - **登录** ("log in") with an account from your `user` table
   - **发送消息** ("send message") with 显示所有客户 ("show all customers")
   - **确认执行** ("confirm and run"), then read the log output

### Step 2: check the browser console

1. Open `http://localhost:5001` and press F12 to open developer tools.
2. Look for errors in the **Console** tab.
3. Check the WebSocket connection in the **Network** tab.

### Step 3: hard refresh and log in again

1. Hard-refresh the page (Ctrl+F5, or Cmd+Shift+R on macOS).
2. Log in again.
3. Retry the request.

### Server logs

Start the server in the foreground to see its debug output:

```bash
python start_web.py
```

A healthy request produces log lines like these (English meaning on the right):

```text
收到消息: session_id=xxx, message=显示所有客户          # message received
处理结果: {'type': 'sql_confirmation', ...}            # processing result
收到SQL确认: session_id=xxx, confirmed=True, sql=...   # confirmation received
开始执行SQL查询...                                      # executing SQL
SQL执行结果: {'type': 'success', ...}                  # execution result
发送响应: {'message': '...', ...}                      # response sent
```

## Common errors

| Message | Meaning | Fix |
|---|---|---|
| 会话无效，请刷新页面 | Invalid session, please refresh | Refresh the page, which creates a new session, and log in again |
| 连接断开 (connection status) | Disconnected | Check the network, restart the server, clear the browser cache |
| 请先登录 | Please log in first | Log in again and confirm the account exists in the `user` table |
| SQL生成失败 | SQL generation failed | Check `DEEPSEEK_API_KEY` and network access, or simplify the request |
| 数据库连接失败 | Database connection failed | Check the `DB_*` values in `.env` and that MySQL is reachable |

## Full restart

```bash
pkill -f "start_web.py"
python start_web.py
# wait a few seconds, then open http://localhost:5001
```

## When reporting an issue

Include:

1. Browser console errors, server terminal output, and the exact steps taken
2. Operating system, browser and version, and Python version
3. The full log from `http://localhost:5001/test`
