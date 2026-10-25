/- Модель потоков не-денежных ресурсов: информация, секреты, внимание.

   Идея: защищаемый ресурс — не только деньги. У каждого потока свои инварианты:

   IFC (информация)     : секрет не покидает границу без явного разрешения;
   Provenance (данные)  : значение нельзя «переписать», можно только получить новое с меткой источника;
   Attention (внимание) : число сообщений не превышает лимит, повтор с тем же ключом не дублируется. -/

structure Secret where
  value  : Nat
  secret : Bool
  deriving Repr

/-- Публикация за границу: секрет не публикуется никогда. -/
def publish (s : Secret) : Option Nat :=
  if s.secret then none else some s.value

/-- IFC: секрет не уходит за границу. -/
theorem secret_never_published (v : Nat) : publish { value := v, secret := true } = none := by
  simp [publish]

/-- IFC: публичное значение уходит как есть. -/
theorem public_published (v : Nat) : publish { value := v, secret := false } = some v := by
  simp [publish]

structure Labeled where
  value  : Nat
  origin : Nat   -- метка источника (кто/что породил значение)
  deriving Repr

/-- Производное значение сохраняет метку источника (provenance). -/
def derive (l : Labeled) (delta : Nat) : Labeled :=
  { value := l.value + delta, origin := l.origin }

/-- Provenance: производное значение помнит, откуда оно. -/
theorem derive_keeps_origin (l : Labeled) (d : Nat) : (derive l d).origin = l.origin := rfl

structure Attention where
  limit : Nat
  sent  : Nat
  keys  : List Nat
  deriving Repr

/-- Отправка сообщения: только если лимит не исчерпан и ключа ещё не было. -/
def notify (a : Attention) (key : Nat) : Attention :=
  if a.sent < a.limit ∧ a.keys.contains key = false then
    { limit := a.limit, sent := a.sent + 1, keys := a.keys ++ [key] }
  else a

/-- Внимание: повтор с тем же ключом не увеличивает счётчик (дедуп). -/
theorem notify_dedup (a : Attention) (k : Nat) (hkey : a.keys.contains k = true) :
    (notify a k).sent = a.sent := by
  have hnot : ¬ (a.sent < a.limit ∧ a.keys.contains k = false) := by
    intro h; rw [hkey] at h; simp at h
  simp only [notify, hnot, if_false]

/-- Внимание: когда лимит исчерпан, счётчик не растёт. -/
theorem notify_limited (a : Attention) (k : Nat) (hfull : ¬ a.sent < a.limit) :
    (notify a k).sent = a.sent := by
  have hnot : ¬ (a.sent < a.limit ∧ a.keys.contains k = false) := by
    intro h; exact absurd h.1 hfull
  simp only [notify, hnot, if_false]

/-- Внимание: после отправки ключ попадает в журнал (дедуп на будущее). -/
theorem notify_records_key (a : Attention) (k : Nat) (hlen : a.sent < a.limit)
    (hkey : a.keys.contains k = false) : (notify a k).keys.contains k = true := by
  have hyes : a.sent < a.limit ∧ a.keys.contains k = false := ⟨hlen, hkey⟩
  simp only [notify, hyes]
  simp
