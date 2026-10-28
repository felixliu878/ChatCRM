# Architecture

ChatCRM has one Python core (database access, authentication, and the LLM service) shared by two front ends: a terminal app (`main.py`) and a real-time web chat (`app.py`).

## Backend (Flask + Socket.IO)

```text
app.py
├── WebChatCRM            per-session wrapper around the shared core
│   ├── initialize()      connect to MySQL, load schema, create the LLM service
│   ├── authenticate()    log in against the `user` table
│   ├── process_message() classify, generate SQL, run reads or request confirmation
│   └── execute_sql()     run confirmed SQL and build the natural-language answer
├── REST endpoints
│   ├── GET  /            chat UI
│   ├── GET  /test        Socket.IO test page (tests/test_websocket.html)
│   ├── POST /api/init    create a session and connect its services
│   └── POST /api/login   authenticate a session
└── Socket.IO events
    ├── connect / disconnect
    ├── send_message      user message → bot_message | error
    └── user_action       confirm or cancel pending SQL → bot_message | error
```

Each browser session gets its own `WebChatCRM` instance, keyed by a server-generated session ID, so database connections and login state are isolated between users.

## Frontend (HTML + CSS + vanilla JavaScript)

```text
templates/index.html      page layout: login card, sidebar, chat area
static/css/style.css      styling and theme variables
static/js/app.js          ChatCRMApp class
                          ├── Socket.IO connection management
                          ├── login and session handling
                          ├── message rendering (text, SQL preview, result tables)
                          └── confirmation dialog for write operations
```

### Interface

- **Login card:** signs in with an account from the database `user` table.
- **Sidebar:** current user, server connection status, quick-action buttons for common tasks, and logout.
- **Chat area:** a welcome message with examples, user and assistant message bubbles, result tables, and suggestion tags under the input box ("add customer", "find customers", "update customer", "log a customer interaction").
- **Confirmation dialog:** for write operations, shows the operation type and the exact SQL before anything is executed.
- **Feedback:** loading indicators and toast notifications for success, warning, and error states.
- **Responsive layout:** the sidebar collapses on small screens.

## Request lifecycle

1. The browser calls `POST /api/init`, then `POST /api/login`, and opens a Socket.IO connection.
2. A `send_message` event arrives. `LLMService.analyze_operation_type` makes a keyword-based guess at the intent.
3. `LLMService.text_to_sql` builds a prompt from the live schema, the CRM business rules, and any geographic expansion, then calls the LLM with retries.
4. `DatabaseManager.operation_type_from_sql` classifies the generated SQL. If the SQL is read-only, it runs immediately. Otherwise the client receives a `confirmation_request` (see [QUERY_EXECUTION.md](QUERY_EXECUTION.md)).
5. After a `user_action` confirm event, the SQL runs and the LLM writes a natural-language summary, which is sent back with the result rows or affected-row count.

## LLM resilience

- `LLMService._call_llm_with_retry` retries up to three times with an increasing delay and a per-call timeout.
- If an SDK call fails, `_fallback_api_call` retries the same request over plain HTTP.
- If the API cannot produce SQL at all, `_generate_fallback_sql` produces rule-based SQL for common requests, such as listing customers or logging a communication.
- If the SDK client cannot be constructed at startup, `LLMServiceFallback` (a `requests`-only implementation) is used instead.

## Running in production

The development server (`python start_web.py`) runs with debug mode on port 5001. For a long-running deployment, use a production WSGI server with an async worker that supports WebSockets, for example:

```bash
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5001 app:app
```

Set `FLASK_SECRET_KEY` in the environment so sessions survive restarts.

## Theming

Colors are defined as CSS variables at the top of `static/css/style.css`:

```css
:root {
    --primary-color: #2563eb;
    --success-color: #10b981;
    --error-color: #ef4444;
    --background-color: #f8fafc;
}
```
