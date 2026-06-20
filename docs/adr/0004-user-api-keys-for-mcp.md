# User API keys for the MCP server

## Status

accepted

## Context

We want to drive grocy-nutrients from Claude Code via an MCP server (v1: a single
read-only `search_product` tool). A headless, non-browser client needs a credential,
but the app's browser auth is short-lived HttpOnly cookie JWTs (refreshed via a
browser flow) — unusable from a headless client. The instance is multi-user, so the
credential must identify a user.

Two design tensions had to be resolved:

1. **How to authenticate and store the key.** Keys are hashed at rest, but a salted
   hash (bcrypt) cannot be looked up — you would scan every row. And the key must
   authenticate the user *without* their password.
2. **What the key can and cannot do.** Per-user Grocy API keys are encrypted with
   Themis SCellSeal keyed by the user's bcrypt `hashed_password` (see ADR-0002). The
   MCP auth path never has the password, so it cannot decrypt the Grocy key. This is
   acceptable only because `search_product` reads the **local** `products` table and
   never calls Grocy.

## Decision

- **`Authorization: Bearer <api_key>` for the MCP path; cookies stay for the browser.**
  The cookie-auth migration freed the `Authorization` header, so the two transports do
  not collide. A new `get_user_from_api_key` dependency (and a reusable
  `authenticate_api_key` function the MCP tool calls directly) validates the key.

- **Key format `gnk_<prefix>_<secret>`; store `key_prefix` (plaintext, indexed) +
  `key_hash = sha256(secret)`.** Lookup is by prefix, then a constant-time
  (`hmac.compare_digest`) hash comparison. SHA-256 (not bcrypt) is sufficient because
  the secret is high-entropy random — there is nothing to brute-force. The plaintext
  key is shown exactly once at creation and never persisted.

- **The key authenticates the user but cannot decrypt the Grocy key.** This is a
  deliberate boundary, not a gap: read-only search needs no Grocy access. Any future
  write tool (`log_consumption`, which hits Grocy) must first solve "decrypt the
  per-user Grocy key without the password" — the same unsolved problem framed in
  ADR-0002. It is explicitly out of scope here.

- **Household scope comes from server config (`MCP_HOUSEHOLD_ID`), not the key.** The
  key carries the user; the configured household says which catalog to search. The
  tool still asserts the authenticated user is an **active member** of that household
  (reusing the existing membership check) so the read path stays bound to the user, not
  just to the server's configuration.

## Considered options

- **Reuse the cookie/JWT for MCP** — rejected. JWTs are short-lived and refresh via a
  browser flow; a headless client has no good way to maintain them.
- **bcrypt-hashed keys, scan all rows on auth** — rejected. O(n) bcrypt comparisons per
  request; prefix+SHA-256 is both faster and simpler for a high-entropy secret.
- **Bind the household to the key at creation** (instead of server config) — viable and
  arguably cleaner for a multi-household client; deferred to keep v1 small. Revisit if a
  single client needs to search more than one household.
- **Solve the write-path Grocy decryption now** — rejected as scope creep; search never
  touches Grocy, so it is unnecessary for v1.

## Consequences

- New `user_api_keys` table + `032` migration (which also enables `pg_trgm` and builds
  the trigram index used by fuzzy search).
- The MCP server is mounted inside the FastAPI process (Streamable HTTP, stateless mode)
  and is exempt from the CSRF Origin check — justified because it uses Bearer auth, not
  cookie-ambient authority. nginx must proxy `/mcp` to the backend (it previously
  proxied only `/api/`).
- The "cannot decrypt the Grocy key" boundary means the MCP feature set is read-only
  until the ADR-0002 key-custody problem is solved. That is recorded as the gating open
  question for any write tool.
- Keys are revocable (delete row) but not rotated automatically; `last_used_at` is
  updated best-effort on each use for visibility.

## Amendment (2026-06-20): household binds to the key, not server config

The MCP tool set grew beyond `search_product` (recipe search, a per-day calculated
view, product/recipe detail, consumption history). With more tools, the
"household from server config" decision above (`MCP_HOUSEHOLD_ID`) became the wrong
default: a single server can serve many households, and the right scope is the one
the user chose for that key. We therefore **overturn the deferred option** and bind
the household to the key at creation.

- `user_api_keys` gains a nullable `household_id` FK (migration `033`). The create
  endpoint verifies the caller is an active member before setting it. Keys are minted
  per-membership from the Households UI.
- `MCP_HOUSEHOLD_ID` is removed; `MCP_ENABLED` (boolean) now gates the mount, since the
  household is no longer known at boot. `authenticate_api_key` returns
  `(user, household_id)`, and the MCP layer rejects a `None` household.
- **Breaking:** pre-existing keys have `household_id = NULL` and are rejected by MCP
  (401). They must be re-minted from the Households UI.
- All tools remain local-DB-only and per-user scoped — the read-only boundary and the
  ADR-0002 key-custody gate on any write tool are unchanged.
