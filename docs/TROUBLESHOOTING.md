# Troubleshooting

The app's interface and log messages are in Chinese. They are given below by their English meaning.

## Nothing happens after confirming SQL

Common causes:

1. **Session ID mismatch** between the browser and the server
2. **Socket.IO connection dropped**
3. **Login state lost**, for example after a server restart
4. **Database connection lost**, so the server cannot run the SQL

### Step 1: use the test page

1. Open `http://localhost:5001/test`.
2. Click the buttons from left to right:
   - **Initialize session**, to get a session ID
   - **Connect WebSocket**, to open the real-time connection
   - **Log in**, with an account from your `user` table
   - **Send message**, with a request such as "Show all customers"
   - **Confirm and run**, then read the log output

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

A healthy request logs these steps, in order:

1. Message received (session ID and message text)
2. Processing result (for example, a SQL confirmation request)
3. SQL confirmation received (confirmed flag and SQL)
4. Executing the SQL query
5. SQL execution result
6. Response sent

If the log stops partway through, the last step shown tells you where the request failed.

## Common errors

| Message (English meaning) | Fix |
|---|---|
| Invalid session, please refresh | Refresh the page, which creates a new session, and log in again |
| Disconnected (connection status) | Check the network, restart the server, clear the browser cache |
| Please log in first | Log in again and confirm the account exists in the `user` table |
| SQL generation failed | Check `DEEPSEEK_API_KEY` and network access, or simplify the request |
| Database connection failed | Check the `DB_*` values in `.env` and that MySQL is reachable |

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
