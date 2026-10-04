# SECURITY — Authentication & Authorization

Last confirmed: 2026-09-20

## Required auth

- All production HTTP handlers that read or mutate user/tenant data **must** require a valid **Bearer JWT**.
- Do not ship new routes that skip auth "for testing" in the same PR as production code.
- RBAC: privileged actions (admin, billing, delete-user) require an explicit role check (`admin`, `owner`, etc.).

## Forbidden patterns

- Hard-coded bypasses: `if user == "test": allow`
- Trusting client-supplied `user_id` / `role` without verifying the JWT claims
- Logging raw access tokens or refresh tokens

## Agent / PR review rule

Flag any new endpoint or middleware change that accepts requests without JWT verification, or that sets auth from query params / body fields alone.
