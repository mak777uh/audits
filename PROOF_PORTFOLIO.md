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

## Coverage matrix: what is guaranteed, on what basis, and under which assumptions

Proofs, audits and certifications are **different grounds of trust**, and they cannot be substituted for
one another. This table separates them per invariant: what the guarantee actually is, what it rests on,
which assumptions it needs, and what the buyer still has to justify themselves.

| invariant | what is guaranteed | basis of trust | assumptions | what remains to justify |
|---|---|---|---|---|
| **I1** conservation | in the model, the sum of funds is unchanged across the hop | **kernel-checked proof** (Lean 4) + **conformance test** vs journal and balances | toolchain `v4.30.0` is faithful; the model matches the real data flow | that the production code follows the modelled data flow (tier 3 checks, tier 1 does not) |
| **I2** atomicity | debit and credit are one operation | **construction** (single transaction) + code review | the runtime really provides atomic transactions | behaviour under partial failures, retries and reorgs on the target chain |
| **I3** idempotency | a retried request does not debit twice | **kernel-checked proof** of the keyed journal + **test** | the idempotency key is unique and is checked before the debit | that clients actually pass the key, and that no other path writes balances |
| **I4** authorization | only the owner or the protocol may release | **kernel-checked proof** over the actor model | the actor set is complete; roles cannot be escalated outside the core | key custody, signer compromise, governance takeover |
| **I5** bounds and ordering | release happens inside the window and under the cap | **model + property tests** per engagement | clock/block source is honest within its tolerance | oracle manipulation, chain reorgs, deadline drift |
| **I6** shell isolation | the untrusted shell cannot move funds directly | **architectural rule + review checklist** — *not* a proof | single-writer discipline is enforced in code review | everything outside the reviewed surface |

Read this as: **I1, I3, I4 rest on a machine-checked basis; I2 on construction; I5 on testing; I6 on process.**
If a buyer needs all six on a proof basis, that is tier 2-3 work and still cannot cover key custody.

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
