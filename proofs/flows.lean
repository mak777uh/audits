/- Модель «софт как защита потока ресурса».

   Сущности:
     Vault    — место хранения под защитой (кошелёк, эскроу, счёт, казна);
     Flow     — поток ресурса из одного хранилища в другое;
     Boundary — граница нашей ответственности: внешний софт или пользователь.

   Правило: изменение остатка хранилища возможно только одним из трёх
   разрешённых событий — deposit (вход извне), withdraw (выход вовне),
   transfer (переход между хранилищами). Никаких «просто поменять баланс». -/

abbrev Resource := Int

structure Vault where
  balance : Resource
  deriving Repr

/-- Вход ресурса из-за границы (external inflow). -/
def deposit (v : Vault) (r : Resource) : Vault :=
  { balance := v.balance + r }

/-- Выход ресурса за границу (external outflow). -/
def withdraw (v : Vault) (r : Resource) : Vault :=
  { balance := v.balance - r }

/-- Переход ресурса между двумя хранилищами: списание и зачисление одной операцией. -/
def transfer (src dst : Vault) (r : Resource) : Vault × Vault :=
  (withdraw src r, deposit dst r)

/-- I1 (частный случай): вход и выход одной и той же величины не меняют хранилище. -/
theorem deposit_withdraw_cancel (v : Vault) (r : Resource) :
    withdraw (deposit v r) r = v := by
  simp [withdraw, deposit]

/-- I1 для перехода: сумма двух хранилищ сохраняется. -/
theorem transfer_conserves (src dst : Vault) (r : Resource) :
    (transfer src dst r).1.balance + (transfer src dst r).2.balance
      = src.balance + dst.balance := by
  show src.balance - r + (dst.balance + r) = src.balance + dst.balance
  have h1 : dst.balance + r = r + dst.balance := Int.add_comm _ _
  rw [h1]
  have h2 : src.balance - r + (r + dst.balance) = (src.balance - r + r) + dst.balance :=
    (Int.add_assoc _ _ _).symm
  rw [h2]
  have h3 : src.balance - r + r = src.balance := Int.sub_add_cancel src.balance r
  rw [h3]

/-- I5: выход не больше остатка ⇒ баланс не станет отрицательным. -/
theorem withdraw_keeps_nonnegative (v : Vault) (r : Resource) (h : r <= v.balance) :
    0 <= (withdraw v r).balance := by
  have hb : 0 <= v.balance - r := Int.sub_nonneg_of_le h
  simpa [withdraw] using hb

/-- Граница ответственности: события, которые мы разрешаем менять ресурс. -/
inductive Event where
  | deposit  (r : Resource)
  | withdraw (r : Resource)
  | transfer (r : Resource)
  deriving Repr

/-- Применение разрешённого события к хранилищу (внешние входы/выходы учтены). -/
def apply (v : Vault) : Event -> Vault
  | Event.deposit r  => deposit v r
  | Event.withdraw r => withdraw v r
  | Event.transfer r => withdraw v r   -- со стороны источника

/-- Каждое разрешённое событие меняет остаток ровно на объявленную величину:
     deposit увеличивает, withdraw уменьшает. Посторонних изменений нет. -/
theorem deposit_changes_by (v : Vault) (r : Resource) :
    (apply v (Event.deposit r)).balance = v.balance + r := by
  simp [apply, deposit]

theorem withdraw_changes_by (v : Vault) (r : Resource) :
    (apply v (Event.withdraw r)).balance = v.balance - r := by
  simp [apply, withdraw]
