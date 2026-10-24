# Jing sBTC/USDCx suite — reasoned review (fork audit)

Scope: `contracts/sbtc-usdcx/` at `f01bffc` (7 contracts, 7,879 lines), fork of the live
`sbtc-stx` v6-4 set. Read as a diff against `863921d` (renames landed alone in `24467aa`).

This is a **reasoned review without a confirmed exploit**: I report what I verified, what I
could not close, and the one place where I would keep looking. No claim is made that a bug exists.

## Verified and holding

1. **No STX residue.** In `markets-sbtc-usdcx-jing-v6-4` and both rungs, every former
   `stx-transfer?` / `with-stx` site is an `USDCX` ft transfer guarded by the matching
   `with-ft USDCX USDCX_NAME <amount>`; grep for `stx-transfer|with-stx|stx-get-balance`
   returns nothing in the fork contracts.
2. **Token binding on the deposit path.** `deposit-token-y` asserts
   `(is-eq (contract-of t) (var-get token-y)) ERR_WRONG_TRAIT` before any accounting, and both
   branches pull USDCx from `tx-sender` (never from the dispatch contract), so the ladder
   cannot be used to deposit a look-alike token.
3. **Decimal handling is symmetric.** Both rungs carry the same constants
   (`PRICE_NUMERATOR 1e18`, `SCALE 1e12`, `PROCEEDS_SCALE 1e18`, `RESCALE 1e3`) and the same
   share/proceeds math; a diff of the two rungs shows only three intentional differences
   (`SOLD_OUT_DUST`, `MIN_DEPOSIT`, and the guard sign). sBTC 8 dp and USDCx 6 dp are the same
   8/6 split the parent set used (sBTC 8 / STX 6), so no rescale was needed and none was added.
4. **Side/token coupling is consistent.** `market-size` reads `min-token-y` in
   `jing-buy-sbtc-bps` (which rests USDCx) and `min-token-x` in `jing-sell-sbtc-bps` (which
   rests sBTC); the market's `still-seated-x/y` and `sync-seat` call the new ladder's
   `is-band-x` / `is-band-y` respectively.
5. **DLMM orientation flipped correctly.** `dlmm-sell` sends
   `swap-x-for-y(... SBTC USDCX ...)` when selling sBTC and `swap-y-for-x(... SBTC USDCX ...)`
   on the other side; pool ids 1/2/17 replace the old 6/15/16.
6. **DIA guard fails closed.** `current-cap = mid * (10000+2000)/10000`,
   `current-floor = mid * (10000-2000)/10000`; the staleness check returns `u0` when the DIA
   timestamp is more than 24 h old, and both `push-to-market` and `refresh-guard` then abort
   with `ERR_ZERO_PRICE` — the rung stops rather than pushing without a guard.
7. **Dispatch moves nothing.** `deposit-buy` / `deposit-sell` validate that allocations sum to
   `total`, then fold `deposit` into each rung; inside the rung `tx-sender` is still the user,
   so the rung pulls the correct token directly. `ERR_DIRECT_CALL` blocks a direct call.

## Not closed, and where I would keep looking

- **DLMM router argument order.** `dlmm-sell` passes `(SBTC USDCX)` for both directions, with
  the direction carried only by the function name (`swap-x-for-y` vs `swap-y-for-x`). That is
  correct only if `dlmm-swap-router` takes `(token-x, token-y)` in pool order and the new
  `sbtc-usdcx` pools really have `x = sBTC`. The in-repo simulations cover the happy path, but
  I could not reproduce a pool with the opposite orientation to prove the router would reject
  it rather than mis-price it. A pool whose `x` token is USDCx (or a pool id typo mapping to
  another pair) is the failure mode I could not exclude from source alone.
- **`0 bps` rung on both sides.** Documented as by-design (refunded at mid), so out of scope,
  but the refund path re-enters `deposit-token-y` accounting and is worth a fork test.
- **`refresh-guard` permissionless call.** Anyone can refresh the guard; the value is derived
  from DIA, so this looks safe, but a keeper racing a push is the kind of interaction the unit
  tests do not cover.

## Method / reproducibility

- Sources: `codeload.github.com/Rapha-btc/jing-contracts-v3/tar.gz/f01bffc` and `.../863921d`;
  diff with `git diff --no-index --unified=2`.
- Checks: targeted greps for `stx-transfer|with-stx`, token/trait binding, scale constants,
  `min-token-x` vs `min-token-y`, `swap-x-for-y` vs `swap-y-for-x`, `current-cap` /
  `current-floor` and the staleness branch.
- Also worth noting: a Lean model of the two invariants this suite relies on
  (conservation of funds and single refund) is public at
  github.com/mak777uh/audits — the same method applied to a sibling contract.
