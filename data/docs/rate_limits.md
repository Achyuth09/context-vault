# Rate Limits

Last confirmed: 2026-07-20

## Default quotas

| Tier | Requests / minute | Burst |
|------|-------------------|-------|
| Free | 60 | 100 |
| Starter | 300 | 500 |
| Team | 1200 | 2000 |

## Headers

Clients should respect:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `Retry-After` on HTTP 429

Agents must back off on 429 instead of retrying immediately.
