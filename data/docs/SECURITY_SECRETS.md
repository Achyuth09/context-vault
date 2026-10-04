# SECURITY — Secrets & Credentials

Last confirmed: 2026-09-20

## Required

- Secrets live in environment variables or a secret manager — never in source.
- `.env` files are local-only and must remain gitignored.

## Forbidden in code / PRs

- Hard-coded `password = "..."`, `api_key = "sk-..."`, `AWS_SECRET_ACCESS_KEY = "..."`
- Committing `.env`, `credentials.json`, private keys (`*.pem`), or token dumps
- Printing secrets to logs in plaintext

## Agent / PR review rule

Flag additions that look like secrets in source, or new files named `.env` / `*.pem` / `credentials*`. Suggest env vars and redacted logging.
