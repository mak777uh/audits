/- OP Stack: инварианты учёта для L1StandardBridge и OptimismPortal2.
   Цель — модель, а не копия кода: проверяем, что «через мост уходит только то, что было внесено»
   и «вывод исполняется не более одного раза».

   Соответствие коду (ethereum-optimism/optimism, packages/contracts-bedrock/src/L1):
     bridgeDepositETH / bridgeETHTo       — депозит ETH с L1 на L2;
     finalizeBridgeETH                    — вывод ETH с L2 на L1 (только через messenger);
     proveWithdrawalTransaction /
     finalizeWithdrawalTransaction        — вывод через портал, защита от повтора по хешу. -/

abbrev Wei := Int

/-- Мост держит залог: сколько ETH заблокировано на L1 под выводы. -/
structure Bridge where
  locked : Wei        -- заблокировано на L1
  escrowed : Wei      -- учтено как обязательство перед L2
  deriving Repr

/-- Депозит: средства приходят на L1-мост и блокируются. -/
def deposit (b : Bridge) (amount : Wei) : Bridge :=
  { locked := b.locked + amount, escrowed := b.escrowed + amount }

/-- Вывод: обязательство гасится ровно на сумму вывода. -/
def finalize (b : Bridge) (amount : Wei) : Bridge :=
  { locked := b.locked - amount, escrowed := b.escrowed - amount }

/-- I1: депозит увеличивает залог ровно на сумму (нет «скрытого» ETH). -/
theorem deposit_adds_locked (b : Bridge) (a : Wei) :
    (deposit b a).locked = b.locked + a := rfl

/-- I1: депозит увеличивает обязательство ровно на ту же сумму. -/
theorem deposit_adds_escrowed (b : Bridge) (a : Wei) :
    (deposit b a).escrowed = b.escrowed + a := rfl

/-- I1: вывод уменьшает залог ровно на сумму вывода. -/
theorem finalize_reduces_locked (b : Bridge) (a : Wei) :
    (finalize b a).locked = b.locked - a := rfl

/-- I1: вывод уменьшает обязательство ровно на сумму вывода. -/
theorem finalize_reduces_escrowed (b : Bridge) (a : Wei) :
    (finalize b a).escrowed = b.escrowed - a := rfl

/-- I2: депозит с последующим выводом той же суммы возвращает исходное состояние. -/
theorem deposit_finalize_cancel (b : Bridge) (a : Wei) :
    finalize (deposit b a) a = b := by
  simp [deposit, finalize]

/-- I5: если залог покрывает вывод, остаток неотрицателен. -/
theorem finalize_bounded (b : Bridge) (a : Wei) (h : a <= b.locked) :
    0 <= (finalize b a).locked := by
  have hl : (finalize b a).locked = b.locked - a := rfl
  rw [hl]
  exact Int.sub_nonneg_of_le h

/- Портал (OptimismPortal2): модель журнала исполненных выводов — следующий шаг.
   Здесь оставлены только инварианты моста, они проверены ядром и компилируются. -/
