# Database setup

ChatCRM reads the schema of whatever MySQL database it connects to and passes it to the LLM, so it can work with your own CRM tables. The built-in business rules expect at least the tables below.

Connection settings come from `.env` (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`). Use `utf8mb4` so Chinese text is stored correctly.

## Users (authentication)

Login is checked against a `user` table:

```sql
CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(50) NOT NULL UNIQUE,
    user_pwd VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- `user_name` is the login name.
- `user_pwd` is the password.

Add a test account:

```sql
INSERT INTO user (user_name, user_pwd) VALUES ('demo', 'choose-a-password');
```

## CRM data

The prompts are written for a CRM with these core tables:

| Table | Purpose |
|---|---|
| `customer` | Customer master data: name, company, title, phone, email, city, notes |
| `customer_communication_records` | Logged interactions (calls, emails, visits) linked to a customer by `customer_id` |

Additional tables, such as relationships, to-do items, or SQL examples, are picked up automatically through schema introspection.

## How login works

1. On startup the app connects to the database and checks that the `user` table exists.
2. The terminal app lists available user names (never passwords).
3. Credentials are checked with a parameterized query:
   `SELECT user_name, user_pwd FROM user WHERE user_name = %s`
4. If the stored password matches, the session is authenticated.

The app reports these errors explicitly: database connection failure, missing `user` table, unknown user name, wrong password, and query errors.

## Before a real deployment

1. **Hash passwords.** Store bcrypt (or similar) hashes instead of plain text, and compare hashes at login.
2. **Least privilege.** Connect with a database user limited to the CRM tables and operations you need.
3. **Richer user model.** Add roles, permissions, and last-login timestamps as needed.
4. **Sessions and auditing.** Add session timeouts and log login attempts and executed SQL.

## Troubleshooting

**"User table not found" (数据库中未找到'user'表)**
1. Confirm the database connection settings in `.env`.
2. Check that the `user` table exists in the configured database.
3. Check the table name's case (MySQL table names can be case-sensitive on Linux).
4. Create the table with the SQL above.

**Login fails**
1. Confirm the user name exists in the `user` table.
2. Check the password.
3. Check the database user's permissions on the `user` table.
4. Read the error message shown by the app for details.
