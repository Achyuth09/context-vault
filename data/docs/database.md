# Database & Persistence

Last confirmed: 2026-08-01

## Production

- Primary datastore: **PostgreSQL 16** in `us-east-1`
- Connection pooling via PgBouncer
- Nightly logical backups to S3 (retained 30 days)

## What agents should assume

- User profiles and billing live in Postgres.
- Vector search for this vault is **local Chroma** in the Context Vault service — not the production Postgres yet.
- Do not invent a “Mongo is primary” answer; that was a 2024 prototype only.
