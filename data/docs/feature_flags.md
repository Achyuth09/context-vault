# Feature Flags

Last confirmed: 2026-09-10

## Active flags

| Flag | Default | Notes |
|------|---------|-------|
| `billing.v2_checkout` | on | New checkout flow |
| `search.hybrid` | off | Experimental hybrid retrieval |
| `agents.context_vault` | on | Prefer vault tools over raw guesses |

Flags are evaluated server-side. Clients must not hardcode “always on” behavior for experimental flags.
