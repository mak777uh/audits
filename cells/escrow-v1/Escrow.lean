/-
  escrow-v1: a minimal escrow model with four invariants.

  This file is self-contained: it imports nothing, uses only Lean core and the `omega` tactic,
  and is checked by `lake build` and by the CI workflow in .github/workflows/proofs.yml.
-/

namespace EscrowV1

/-- Escrow state. `locked` is still in escrow, `paid` went to the payee, `refunded` went back to the payer. -/
structure S where
  locked : Nat
  paid : Nat
  refunded : Nat

/-- The money that went in is the sum of the three buckets. This is the state invariant. -/
def invariant (deposited : Nat) (s : S) : Prop :=
  s.locked + s.paid + s.refunded = deposited

/-- Pay `amt` to the payee. Guarded: it does nothing unless `amt` is covered by `locked`. -/
def release (s : S) (amt : Nat) : S :=
  if amt ≤ s.locked then
    { locked := s.locked - amt, paid := s.paid + amt, refunded := s.refunded }
  else s

/-- Return `amt` to the payer. Guarded: it does nothing unless `amt` is covered by `locked`. -/
def refund (s : S) (amt : Nat) : S :=
  if amt ≤ s.locked then
    { locked := s.locked - amt, paid := s.paid, refunded := s.refunded + amt }
  else s

/-- A settled escrow is one where nothing is left locked. -/
def settled (s : S) : Prop := s.locked = 0

/-- 1) Conservation: release preserves `locked + paid + refunded`. -/
theorem release_preserves (deposited amt : Nat) (s : S) (h : invariant deposited s) :
    invariant deposited (release s amt) := by
  unfold invariant at h
  unfold invariant release
  by_cases hge : amt ≤ s.locked
  · simp only [hge, ite_true]
    have hsub : s.locked - amt + amt = s.locked := Nat.sub_add_cancel hge
    omega
  · simp only [hge, ite_false]
    exact h

/-- 1') Conservation: refund preserves `locked + paid + refunded`. -/
theorem refund_preserves (deposited amt : Nat) (s : S) (h : invariant deposited s) :
    invariant deposited (refund s amt) := by
  unfold invariant at h
  unfold invariant refund
  by_cases hge : amt ≤ s.locked
  · simp only [hge, ite_true]
    have hsub : s.locked - amt + amt = s.locked := Nat.sub_add_cancel hge
    omega
  · simp only [hge, ite_false]
    exact h

/-- 2) Single exit: releasing everything once leaves nothing locked, so a second release changes nothing. -/
theorem release_all_then_release_noop (s : S) (amt : Nat) (h : amt = s.locked) :
    release (release s amt) amt = release s amt := by
  subst h
  unfold release
  simp only [Nat.le_refl, ite_true]
  cases s with
  | mk locked paid refunded =>
    simp only [Nat.sub_self]
    simp

/-- 3) Guarded release: asking for more than is locked is a no-op. -/
theorem release_over_balance_noop (s : S) (amt : Nat) (h : s.locked < amt) :
    release s amt = s := by
  unfold release
  have : ¬ amt ≤ s.locked := Nat.not_le.mpr h
  simp only [this, ite_false]

/-- 4) Guarded refund: asking for more than is locked is a no-op. -/
theorem refund_over_balance_noop (s : S) (amt : Nat) (h : s.locked < amt) :
    refund s amt = s := by
  unfold refund
  have : ¬ amt ≤ s.locked := Nat.not_le.mpr h
  simp only [this, ite_false]

/-- 5) A release never decreases what was paid. -/
theorem paid_never_decreases (s : S) (amt : Nat) : s.paid ≤ (release s amt).paid := by
  unfold release
  by_cases hge : amt ≤ s.locked
  · simp only [hge, ite_true]
    omega
  · simp only [hge, ite_false]
    exact Nat.le_refl s.paid

/-- 6) Settled means the payee and payer together hold everything that was deposited. -/
theorem settled_splits_deposit (deposited : Nat) (s : S) (h : invariant deposited s) (hs : settled s) :
    s.paid + s.refunded = deposited := by
  unfold invariant settled at *
  omega

end EscrowV1
