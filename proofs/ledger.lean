/- Модель учёта денег для клетки `bal`: сохранение суммы по транзакциям.
   Инварианты сформулированы так, что доказываются определением (rfl) —
   значит модель проверяется даже без Mathlib. -/

abbrev Money := Int

structure Tx where
  amount : Money
  deriving Repr

/-- Прогон списка транзакций от начального баланса. -/
def run (start : Money) (txs : List Tx) : Money :=
  txs.foldl (fun acc t => acc + t.amount) start

/-- Пустой список транзакций не меняет баланс. -/
theorem run_nil (s : Money) : run s [] = s := rfl

/-- Одна транзакция меняет баланс ровно на свою сумму. -/
theorem run_single (s : Money) (t : Tx) : run s [t] = s + t.amount := rfl

/-- Склейка: сумма по объединённому списку = сумма по частям (аддитивность учёта). -/
theorem run_append (s : Money) (a b : List Tx) :
    run s (a ++ b) = run (run s a) b := by
  simp [run, List.foldl_append]

/-- Обратный ход (откат последней транзакции) восстанавливает баланс. -/
theorem run_reverse_single (s : Money) (t : Tx) :
    run (s + t.amount) [{ amount := -t.amount }] = s := by
  simp [run]
  exact Int.add_neg_cancel_right s t.amount
