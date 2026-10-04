# Authentication Policy

Last confirmed: 2026-08-15

## Tokens

- Production auth uses **Bearer JWT** issued by `auth.example.com`.
- Access token TTL: **15 minutes**
- Refresh token TTL: **30 days**
- Algorithm: RS256

## Rules for agents

- Never embed long-lived API keys in client apps.
- Service accounts use short-lived JWTs from the identity provider.
- Password login for humans only; machines use OAuth client credentials.
