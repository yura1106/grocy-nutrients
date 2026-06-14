# Grocy API key encryption is compartment isolation, not at-rest protection

## Status

accepted

## Context

Each user's Grocy API key is stored in `HouseholdUser.grocy_api_key`, encrypted with
Themis SCellSeal keyed by that user's bcrypt `hashed_password`
(`core/encryption.py`). The intent, as originally conceived, was to stop a DB/server
admin from reading plaintext Grocy keys.

Reviewing the threat model honestly (security audit, 2026-06) shows this property is
**not** achieved, and cannot be achieved by the current design:

- The encryption key is `hashed_password`, which lives in the **same database**, in
  the `user` table. Anyone with a full DB dump has both the ciphertext and its key,
  so a DB dump alone decrypts every Grocy key.
- The decrypt path runs in **background Celery tasks** (`build_grocy_api` →
  `decrypt_api_key` at `services/grocy_api.py`), invoked by `celery_beat` at 04:00
  for `sync_products` and by `execute_consumption` — with **no user present and no
  password in memory**. This only works because `hashed_password` sits next to the
  ciphertext in the DB. Any scheme that truly withheld the key from the DB would
  break unattended background sync.

A deeper conclusion fell out of the analysis: against an adversary who holds **both**
the database **and** the server environment (a root/server admin — the stated target
threat), **no symmetric scheme with a process-accessible key can protect the keys.**
A master key in env, or a hybrid `H(master_key ‖ hashed_password)`, are both
decryptable by whoever controls the process. The only design that withholds plaintext
from a server admin is one where the decryption secret comes **from the user** (derived
from their password/session) and never rests on the server — which is mutually
exclusive with unattended 04:00 sync.

The hybrid `H(master_key ‖ hashed_password)` idea was specifically considered and
rejected: against a DB-only dump it is equivalent to a plain master key, and against a
master-key-holding adversary the `hashed_password` component adds **no secrecy** (that
adversary already sees the hash) while retaining the re-encrypt-on-password-change
machinery. It pays complexity for nothing.

## Decision

**Keep the current Themis encryption as-is for now, and document its true scope:** it
provides **compartment isolation only** — protection against a partial leak of *just*
the `householduser` table without the `user` table. It is **not** encryption-at-rest
against a full DB dump, and **not** protection against a root/server admin.

The real protections for Grocy keys are operational, not cryptographic: DB network
isolation, restricted DB/backup access, and server access control.

A future improvement (not done here) is to migrate to an **app-level master key**
(`APP_ENCRYPTION_KEY` in env / Docker secret, never in the DB). That honestly raises
the bar from "DB dump = all keys exposed" to "DB dump without the server env is
useless", and — because the key lives in the process env — it **does not break**
background sync. It does not, and is not expected to, defend against a root admin.

## Considered options

- **App-level master key in env (the planned future state)** — real defense against a
  DB-only dump; background tasks keep working (key is in process env, not user
  session); removes the re-encrypt-on-password-change coupling entirely. Deferred, not
  rejected — see "future improvement" above.
- **Hybrid `H(master_key ‖ hashed_password)`** — rejected. Equivalent to a plain
  master key against a DB dump; the `hashed_password` term adds no secrecy against a
  master-key holder and keeps the re-encrypt-on-password-change complexity.
- **Per-user key derived from the user's password, never stored server-side** — the
  only design that withholds plaintext from a server admin, but it makes unattended
  04:00 sync impossible (no secret available without an active session). Rejected
  because background sync is a hard requirement.
- **External KMS / Vault** — strongest key custody, but contradicts the simple
  self-hosted Docker-compose deployment this project targets. Rejected as
  disproportionate.

## Consequences

- The code is unchanged; only the understanding is corrected. The Themis dependency
  and the `hashed_password`-keyed scheme remain — effectively a working experiment
  with the Themis library that does not deliver the security property it implies.
- Anyone reading `core/encryption.py` must not assume the Grocy keys are protected
  against a DB dump or an admin. This ADR and the CONTEXT.md glossary entry are the
  canonical statement of the real boundary.
- When the app-level master key migration happens, it will need a one-time
  re-encryption of all stored keys and a new managed env var; the
  re-encrypt-on-password-change path (`reencrypt_user_api_keys`) can then be removed
  for Grocy keys.
