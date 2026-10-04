# SECURITY — Database & SQL

Last confirmed: 2026-09-20

## Required

- Use parameterized queries / ORM bind parameters for all dynamic SQL.
- Prefer repository helpers over ad-hoc string building.

## Forbidden

- String concatenation or f-strings that embed user input into SQL, e.g.
  - `f"SELECT * FROM users WHERE id = {user_id}"`
  - `"SELECT ... WHERE name = '" + name + "'"`
- Executing raw SQL from request bodies without a strict allowlist.

## Agent / PR review rule

Flag any diff that builds SQL via `+`, `%`, `.format`, or f-strings with request/user data. Suggest parameterized APIs (`?` / `%s` binds, or ORM filters).
