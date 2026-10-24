import Mathlib.Tactic

/-- Commutativity of natural number addition (onboarding warmup). -/
theorem proof : statementProp := by
  intro a b
  exact Nat.add_comm a b
