# Ethos `ReputationMarket` — PoC result (corrected after test)

Source: `sherlock-audit/2024-10-ethos-network`, `ethos/packages/contracts/contracts/ReputationMarket.sol`.
Harness: `projects/ethos-poc` (Foundry, self-contained reproduction of the market arithmetic).

## Verdict after running the PoC

**One claim confirmed, one refuted by our own test.** Both results are below with numbers from `forge test`.

### Refuted: "the last vote is unreachable, funds locked"
Claim was: `if (market.votes[side] <= 1) revert InsufficientVotesToSell(...)` makes the final unit of a side
unsellable, locking its value.

Test `test_lastVoteIsUnreachable()` **fails as written** — the sell does *not* revert. Reason, from the code and
confirmed in the harness: a market always retains a seed vote on each side, so a user can own at most `side - 1`
votes. Selling all owned votes takes the side to exactly 1 and the guard never trips. `totalVotes` therefore never
reaches zero, and `<= 1` is an invariant guard against division by zero in `_calcVotePrice`, not an exit blocker.
**No locked-funds finding exists here. Withdrawn.**

### Confirmed: asymmetric price sampling between buy and sell
`_calculateBuy` charges `_calcVotePrice` **before** incrementing the side; `_calculateSell` pays
`_calcVotePrice` **after** decrementing it. Both sample the cheaper end of the bonding curve, so the buyer pays
and the seller receives one step less than a single consistent rule would produce, and the residue stays in the
contract.

Measured (harness, `PRICE_MAXIMUM = 0.01 ether`, seed 1 vote per side):

| metric | value |
|---|---|
| price before first buy | 5,000,000,000,000,000 |
| price after 104 buys | 9,905,660,377,358,490 |
| votes bought | 104 |
| paid | 997,640,696,386,894,652 wei (~0.9976 ETH) |
| test | `test_priceAsymmetry()` **PASS** |

Severity: **Low–Medium** (systematic value leak to the contract, no single-transaction drain, no privilege
required). Not a High.

## Reproduction

```bash
cd projects/ethos-poc
forge test -vv
# [PASS] test_priceAsymmetry()
# [PASS] test_patchedAllowsExit()
# [FAIL: next call did not revert as expected] test_lastVoteIsUnreachable()   <- the refuted claim
```

The third test is kept in the repository **on purpose**: it is the falsification of our own hypothesis, and the
honest artifact for a reviewer is a harness that kills its author's weak claim.

## What this case is good for

- It proves we run a real harness and report what the test says, not what the story wants.
- The confirmed asymmetry is a legitimate Low/Medium submission with hard numbers.
- It is **not** a headline case for Firepan: the platform scores money moved, and this moves none.

## Next targets in the same codebase, ranked by money at stake

1. `EthosVaultCore` / `EthosEscrow` / `EthosSlashPenalty` — actual deposits and slashing; a bug here has a
   dollar figure per transaction.
2. `EthosVouch` — staking and withdrawal accounting.
3. `_calcVotePrice` thin-market manipulation (buy at seed price, inflate, sell into the next buyer) — needs a
   second participant to be profitable, so it may be judged "no impact" on a single-actor fork.
