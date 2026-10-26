# Cell: escrow-v1

A complete cell in the format this repository uses for every claim:

| part | file | what it is |
|---|---|---|
statement | `SPEC.md` | four properties, in plain language |
model | `Escrow.lean` | the escrow as a Lean 4 state machine, with those four properties proved |
check | `check.py` | compiles the model, forbids `sorry`/`admit`, audits axioms, writes a receipt |
receipt | `receipt.json` | deterministic JSON bound to the sha256 of the statement and the model |

## Run it

```bash
python cells/escrow-v1/check.py          # produce receipt.json
python cells/escrow-v1/check.py --check  # verify the existing receipt still matches the files (CI)
```

Requirements: Lean 4 (`lean --version`), Python 3.10+. Nothing else — no GPU, no network, no Mathlib.

## What the receipt says

`verdict: pass` means, mechanically: Lean exited 0, the model contains no `sorry`/`admit`, every theorem's
axioms are within `{propext, Classical.choice, Quot.sound}`, and the receipt was produced from exactly these
file hashes. Change one character in `SPEC.md` or `Escrow.lean` and `--check` fails until the receipt is rebuilt.

## Proven

`release_preserves`, `refund_preserves` (conservation), `release_all_then_release_noop` (single exit),
`release_over_balance_noop`, `refund_over_balance_noop` (guards), `paid_never_decreases`,
`settled_splits_deposit`.

## Not proven, and not claimed

- no access control, no fees, no timeouts, no reentrancy surface — a real audit adds these;
- it is a model of an escrow, not a specification of any deployed contract;
- the model uses `Nat`, so it says nothing about overflow in a fixed-width implementation;
- a `pass` here means the proofs are valid, not that the properties are the ones a given protocol needs.

The point of the cell is the **format**: the Cairo cell funded by the Starknet grant will have the same four
parts and the same one-command check.
