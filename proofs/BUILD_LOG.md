# Proofs: build verification log

Run: 2026-10-26 12:04 UTC
Toolchain: `Lean (version 4.36.0-rc1, x86_64-w64-windows-gnu, commit c9afcddf514a6772bd4d649f7cfc04eff0b9f15e, Release)`

Source: files from https://github.com/mak777uh/audits/tree/main/proofs (unchanged, downloaded at run time).

| file | exit | seconds | theorems/lemmas | sorry/admit | warnings |
|---|---:|---:|---:|---:|---|
| `escrow.lean` | 0 | 1.1 | 9 | 0 | no |
| `flows.lean` | 0 | 1.1 | 5 | 0 | no |
| `flows_info.lean` | 0 | 1.2 | 6 | 0 | yes (deprecation) |
| `ledger.lean` | 0 | 1.1 | 4 | 0 | no |
| `op_stack.lean` | 0 | 1.1 | 6 | 0 | no |
| `valuepath.lean` | 0 | 1.2 | 4 | 0 | yes (deprecation) |

**Totals:** 6 files, 6 compiled with exit 0, **34** theorems/lemmas, **0** occurrences of `sorry`/`admit`.

Reproduce:
```
git clone https://github.com/mak777uh/audits && cd audits/proofs
lean --version   # Lean 4.36.0-rc1
for f in *.lean; do lean "$f" || echo "FAIL $f"; done
grep -c -E 'sorry|admit' *.lean
```

## Limits
- `lean` compiles each file independently; this is a per-file kernel check, not a `lake build` of one project.
- A compile with exit 0 means the proofs in that file are accepted by Lean's kernel with no errors; it does not mean the *statements* are the right statements for any protocol.
- Two files emit deprecation warnings (`if_true`/`if_false` renamed to `ite_true`/`ite_false`); warnings do not affect correctness, only style.
- No `#print axioms` audit is included here, so 'depends only on standard axioms' is not shown in this log.
