# Cell: escrow-v1

A **cell** is the smallest unit this repository ships: a plain-language statement, a machine-checked model,
a check that can be re-run by a stranger, and a receipt bound to the statement. This one models a minimal
escrow: money goes in, and can leave exactly once — either paid to the payee or refunded to the payer.

## The statement (what is claimed)

For an escrow with a single deposit:

1. **Conservation.** At every step, `locked + paid + refunded = deposited`. Money is never created or lost.
2. **Single exit.** Once the escrow is settled (paid or refunded), no second payment or refund can change the balances.
3. **Guarded release.** `release` only moves money when the requested amount is covered by what is still locked.
4. **Guarded refund.** `refund` only returns what is still locked, and only while nothing has been paid.

## Why this shape

These four are the properties that actually fail in real escrows: double release (2), releasing more than was
deposited (3), refunding after payment (4), and arithmetic drift that makes the books disagree (1).
They are stated as a Lean model, so a reviewer can check the claim mechanically instead of reading prose.

## What the model is not

It is **not** a specification of any deployed contract, it has no access control, no fees, no timeouts, and no
reentrancy surface — those are exactly the things a real audit adds. The cell exists to show the format: the
Cairo cell built under the Starknet grant will have the same four parts (statement, model, check, receipt).
