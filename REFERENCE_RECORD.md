# Verifiable record (reference substitute)

Some forms ask for "a primary reference who can speak to the quality of your work". This applicant works
alone with AI agents: there is no supervisor, no employer and no grantee peer who could vouch honestly.
Instead of inventing a person, this file lists what can be **checked without trusting anyone**.

## 1. The rule the work follows

> A number appears only together with the measurement id, the command that produced it, and a link to the
> log. No artifact — no claim.

It is not a slogan: `lab/check-text-clean.sh` fails CI when a bare number appears in the text, and a
claims matrix (`manuscript/CLAIMS.md`) states, per claim, the maximum wording that the evidence licenses.

## 2. What is checkable in a terminal today

| what | how to check | what a reviewer gets |
|---|---|---|
Kernel-checked invariants (money, escrow, value path, information/attention) | `lean proofs/flows.lean`, `proofs/escrow.lean`, `proofs/valuepath.lean`, `proofs/op_stack.lean` on `leanprover/lean4:v4.30.0` | exit 0 = the invariants hold in the model; no `sorry`, axioms reported |
A deterministic verifier that emits receipts | `proof_market/verifier.py --kind lean_proof --artifact <file> --budget 120` | a receipt with verdict, toolchain, axioms, timings, hashes; negative and timeout vectors included |
Test vectors for that verifier | `proof_market/vectors.json` | three vectors: pass, fail (`sorry`), timeout — expected verdicts recorded |
Claims matrix with wording limits | `manuscript/CLAIMS.md` | per claim: status, artifact, section, maximum admissible wording |
Refutation registry | `lab/` experiment cards and the refuted-mechanism list | negative results kept as results, not erased |
Run manifests | `lab/runs/` and `reports/` | each experiment has a manifest; a claim traces to a run by hash |

## 3. Numbers, with their source of truth

Reported by the science team on 25.10.2026 and used in all application texts:

| quantity | value |
|---|---|
experiments | **31** |
runs with manifests | **477** |
reports | **80** |
long-form articles | **26** |
Lean files | **7** (17 hypotheses, 31 theorems) |
test functions | **334** (612 tests) |
commits | **763** |
files in git | **1570** |

If any of these disagrees with a later count, **the repository wins** and this file is corrected.

## 4. What is deliberately NOT claimed

- no journal publications (there are none);
- no "93 experiment cards" (that number belongs to a different project and was removed from our texts);
- no p-values at n = 3;
- no claims about life, consciousness or intelligence;
- no claim that the model equals the implementation: the model is a model, and the gap is stated.

## 5. If a person is still required

The applicant can name a reference **if and when** a real one exists. Until then the honest substitute is
this record: the reviewer runs four commands and sees whether the claims hold.
