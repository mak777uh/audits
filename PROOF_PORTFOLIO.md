# Proof Portfolio — machine-checked invariants for money paths

This repository collects the formal models we ship with audits. Every model here compiles
against a pinned Lean 4 toolchain (`leanprover/lean4:v4.30.0`) with **no `sorry`, no extra
axioms** in the delivered theorems. The client can re-run the check themselves:

```bash
lean proofs/valuepath.lean     # exit 0 = the invariants hold in the model
```

## What we model

A money path is a chain of **responsible nodes** (a person, an exchange, a contract, a treasury)
connected by **hops** (transfers). Each hop carries four questions, and each question maps to an
invariant we can state and check:

| # | invariant | question it answers | status in our models |
|---|---|---|---|
| **I1** | conservation | does the sum of funds stay the same across the hop? | `ledger.run_append`, conformance test vs ledger and on-chain balances |
| **I2** | atomicity | can the debit happen without the credit? | enforced by construction (one transaction), checked by conformance |
| **I3** | idempotency | does a retried request debit twice? | `valuepath.step_dup`, `key_present_after`; refund idempotency in the Clarity case |
| **I4** | authorization | may this principal move these funds at all? | `valuepath.mayInitiate`, `no_source_no_auth`, `owner_may_initiate`; `escrow.may_release`, `release_implies_authorized` |
| **I5** | bounds and ordering | is the release not earlier than T, not later than T+window, amount within limits? | modelled per engagement (windows in the Clarity escrow case) |
| **I6** | shell isolation | can the untrusted shell bypass the core and move funds directly? | architectural rule (single writer) plus a review checklist; not machine-checked |

**I6 is deliberately not claimed as proved.** A model cannot prove that code outside it does
nothing; that is a build and review property. We say so in every offer.

## Models in this repository

| file | what it proves |
|---|---|
| `proofs/valuepath.lean` | authorization of a hop, idempotency of the journal, presence of the idempotency key |
| `proofs/escrow.lean` | hold conserves the total, release returns the held amount exactly once, no negative balance, only owner/protocol may release |
| `proofs/ledger.lean` | replay of transaction list is additive, empty list is a no-op, reversing a transaction restores the balance |

## Coverage matrix (what a buyer gets in tier 1)

| invariant | proved in Lean | checked by conformance | not covered |
|---|---|---|---|
| I1 conservation | ✅ | ✅ (journal vs on-chain) | multi-chain bridges beyond the modelled chain |
| I2 atomicity | — (by construction) | ✅ | cross-contract calls we did not model |
| I3 idempotency | ✅ | ✅ | external retries outside the idempotency key |
| I4 authorization | ✅ | — | key compromise (the key holder is authorised by definition) |
| I5 bounds/ordering | per engagement | per engagement | oracle failures |
| I6 shell isolation | — | — | **explicitly out of scope** |

## What this does not cover

Key compromise, supply-chain attacks on frontends, social engineering and oracle manipulation are
outside any accounting model. In the four weeks to 23 Oct 2026 the public hacks database recorded
about $534M across 19+ incidents, and the largest ones (Bitget $387M, Ledger $93M) were exactly
these classes. We say that plainly instead of implying a proof covers them.

## Engagement tiers

| tier | deliverable | price | turnaround |
|---|---|---|---|
| **T1 spec decomposition** | model, proved theorems, theorem-to-code map, coverage matrix, reproducible check | 250 USDC | 3 days |
| **T2 core implementation** | T1 plus the implementation of the core and a conformance test against your ledger and balances | 900 USDC | 10 days |
| **T3 audit with core extraction** | findings with line references, extracted core, proved invariants, shell-versus-contract review | 2500 USDC | 4 weeks |

Payment in USDC on Base, 50% upfront and 50% on delivery. Contact: knock on the hashn listing
`verified-invariants-audit`, or open an issue in this repository.
