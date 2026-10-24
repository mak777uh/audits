import Mathlib.Tactic

theorem proof : statementProp := by
  intro a b c
  exact Nat.left_distrib a b c
