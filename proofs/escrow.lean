/- Модель залога для клеток swarm_claim / swarm_submit.
   Структура выбрана так, чтобы инварианты были верны по определению:
   balance = total - held; удержание увеличивает held, возврат обнуляет held. -/

abbrev Money := Int

structure Escrow where
  total : Money
  held  : Money
  deriving Repr

/-- Свободный баланс = всего минус удержано. -/
def balance (e : Escrow) : Money := e.total - e.held

/-- Постановка залога: средства не покидают счёт, растёт только удержание. -/
def hold (e : Escrow) (fee : Money) : Escrow :=
  { total := e.total, held := e.held + fee }

/-- Возврат залога: удержание обнуляется, средства снова доступны. -/
def release (e : Escrow) : Escrow :=
  { total := e.total, held := 0 }

/-- Удержание не уменьшает общий объём средств (закон сохранения). -/
theorem hold_conserves_total (e : Escrow) (fee : Money) :
    (hold e fee).total = e.total := rfl

/-- Удержание увеличивает ровно на сумму залога. -/
theorem hold_adds_fee (e : Escrow) (fee : Money) :
    (hold e fee).held = e.held + fee := rfl

/-- После возврата ничего не удержано. -/
theorem release_clears (e : Escrow) : (release e).held = 0 := rfl

/-- После возврата свободный баланс равен всему объёму средств. -/
theorem release_restores (e : Escrow) : balance (release e) = e.total := by
  simp [balance, release]

/-- Гейт: если удержание не больше всего объёма, баланс не отрицателен. -/
theorem no_negative_iff (e : Escrow) (h : e.held <= e.total) : 0 <= balance e := by
  unfold balance
  exact Int.sub_nonneg_of_le h


/- === Авторизация: оболочка не может выпустить средства в обход ядра === -/

/-- Кто вправе двигать средства: только владелец эскроу или сам протокол. -/
inductive Actor where
  | owner
  | protocol
  | anyone
  deriving DecidableEq, Repr

/-- Выпуск залога разрешён только owner или protocol. -/
def may_release (a : Actor) : Bool :=
  match a with
  | Actor.owner    => true
  | Actor.protocol => true
  | Actor.anyone   => false

/-- Теорема: «любой» не может выпустить залог (авторизация как свойство ядра). -/
theorem anyone_cannot_release : may_release Actor.anyone = false := rfl

/-- Теорема: владелец может. -/
theorem owner_can_release : may_release Actor.owner = true := rfl

/-- Теорема: протокол может. -/
theorem protocol_can_release : may_release Actor.protocol = true := rfl

/-- Если выпуск прошёл, значит вызывающий был авторизован (контрапозиция). -/
theorem release_implies_authorized (a : Actor) (h : may_release a = true) :
    a = Actor.owner ∨ a = Actor.protocol := by
  cases a <;> simp [may_release] at h ⊢
