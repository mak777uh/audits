# Registry: verified Lean theorems (mak777uh audits)

This directory is a static export of a self-hosted **Proof Registry** (protocol v0.1, package `proof-engine-registry` 1.45.0)
covering every Lean theorem we publish in our audits.

- `index.json` - protocol index: one entry per theorem (`claim_hash`, `verdict`, `proof_url`, `badge_url`).
- Every entry is **PROVED**: the file compiled by the Lean 4 kernel (toolchain `leanprover/lean4:v4.30.0`) through the
  `leanback` MCP checker, with no `sorry` and no extra axioms.
- Entry per theorem records two facts in `evidence`: the source file and its SHA-256 (`A1`), and the kernel-check record (`A2`).

Coverage: Kairan's Seat (12), Jing shares/epochs (6), MezoGig escrow (30) - 48 theorems total.

How to use it: fetch `index.json`, compute `sha256` of your claim statement, and look up `claim_hash`. A match means the
statement is the exact one we proved; the `proof_url` points at the source and the check record.