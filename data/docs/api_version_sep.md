# API Version Policy (Sep 2026) — UPDATED

Last confirmed: 2026-09-01

## Production API

Our public REST API is now **v3**. All new integrations must use `https://api.example.com/v3`.

- Auth: Bearer JWT (same issuer as before)
- Migration: v2 remains available until 2026-12-31, then removed
- Support contact: platform@example.com

Agents and docs that still say "API is v2 only" are **out of date**.
