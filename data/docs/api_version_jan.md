# API Version Policy (Jan 2025)

Last confirmed: 2025-01-15

## Production API

Our public REST API is **v2**. All clients must call `https://api.example.com/v2`.

- Auth: Bearer JWT
- Deprecation: v1 was shut down on 2024-12-01
- Support contact: platform@example.com

Do not document or recommend `/v1` endpoints.
