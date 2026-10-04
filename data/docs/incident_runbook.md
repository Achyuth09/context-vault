# Incident Runbook — API 5xx Spike

Last confirmed: 2026-08-28

## Symptoms

- Elevated 5xx on `/v3/*`
- Latency p99 > 1s
- On-call page fires

## First 10 minutes

1. Check status page + deploy region health (`us-east-1`).
2. Confirm whether a deploy landed in the last hour.
3. If auth errors dominate, check JWT issuer `auth.example.com`.
4. Page platform on-call if Sev-1 lasts > 15 minutes.

## Do not

- Do not roll forward API version advice during an incident without checking Context Vault freshness.
- Do not tell customers “use /v2 only” — that guidance is outdated unless vault marks v3 contested with a newer policy.
