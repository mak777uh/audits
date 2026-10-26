import Lake
open Lake DSL

package «audits-proofs»

/-- Все модели лежат в proofs/ как отдельные модули; библиотека собирает их вместе. -/
@[default_target]
lean_lib Proofs where
  srcDir := "proofs"
  roots := #[`escrow, `flows, `flows_info, `ledger, `op_stack, `valuepath]
