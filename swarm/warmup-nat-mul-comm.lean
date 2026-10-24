import Mathlib.Tactic

theorem proof : statementProp := by
  intro a b
  exact Nat.mul_comm a b
