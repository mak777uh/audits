# audits
Independent smart-contract and protocol audits

## What is checkable here, and by which command

| claim | command | what it proves |
|---|---|---|
| all Lean models compile as one library | `lake build` | the six files are a single Lean package, not six unrelated snippets |
| no `sorry` / `admit` | `grep -nE '(^|[^A-Za-z_])(sorry|admit)([^A-Za-z_]|$)' proofs/*.lean` | no unfinished proofs |
| no hidden axioms | `python3 proofs/axioms_check.py` | every theorem's axioms are within `propext`, `Classical.choice`, `Quot.sound`; fails on `sorryAx` or a custom axiom |
| each theorem is accounted for in the coverage matrix | `python3 proofs/coverage.py --check` | the matrix cannot silently go stale |
| the verifier rejects bad receipts, not just accepts good ones | `python3 proof_market/verifier.py --selftest` | tampered artifact hash, `pass` with non-zero exit, missing field are all rejected |

All five run in CI on every push that touches `proofs/` or `proof_market/`
([workflow](.github/workflows/proofs.yml)).

### What is *not* claimed

- the coverage matrix is a **keyword labelling** of theorem names and bodies (`proofs/coverage.py`), not a proof
  that the statements model any protocol; it exists so nothing is silently missing, and the method is printed with it;
- `lake build` success means Lean accepts the proofs, not that the specification is the right one;
- the verifier selftest checks receipt **integrity and consistency**, not that Lean ran — the kernel step is separate;
- there is no Cairo code yet: that is what the Starknet grant is for.
