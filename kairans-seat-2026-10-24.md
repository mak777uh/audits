# Kairan's Seat (kairan-seat-lab-ocifarsito-v2) — аудит

Контракт: `contracts/charity/kairan-seat-lab-ocifarsito-v2.clar` (487 строк, **не задеплоен**).
Баунти AIBTC `mvllpuv02f876aa9c4be`: 6 000 sats, до 06.11.2026, на момент старта 1 заявка.
Метод: чтение кода + сверка TERMS/DONOR_TERMS с поведением. Тесты авторов: 15/15 unit + 842/842 stxer.

## Что проверено и держится

1. **Двойной рефанд невозможен.** `refund-one` обнуляет `gifts[who]` после перевода, `unrefunded` уменьшается на фактически выплаченное; повторный вызов с тем же донором платит 0.
2. **Утечки средств в сторону нет.** `pay` вызывается только в `release-seat` (LAB) и `claim-reserve` (LAB); `claim-reserve` берёт `extra = balance − unrefunded`, то есть не трогает донорские деньги.
3. **Auth.** `request-seat`/`claim-reserve`/`deposit-reserve` проверяют `contract-caller` (не `tx-sender`) — обойти через прокси-контракт нельзя. `release-seat` — только OWNER.
4. **Окно успеха.** `failure-at` = `reached-at + SEAT_WINDOW` (если цель собрана), иначе `DEADLINE`; `check-seat` запрещает выпуск после `failure-at`; `check-refunds` — до. Пересечения нет.
5. **Переполнение цели.** `donate` ограничен `remaining`, поэтому `total` не может превысить `TARGET`, а `reached-at` фиксируется ровно один раз.

## Находки

### F-1 (Low/QA): `deposit-reserve` не требует «полной суммы», хотя TERMS обещает «in full minus STX network fees»
TERMS (стр. 63) и DONOR_TERMS (стр. 63): резерв депонируется «once, in full minus STX network fees».
Код (стр. 323–345) принимает **любые** `stx`/`sats > 0` и ставит `reserve-deposited = true` после первого вызова.
Следствие: FUNDRAISER может (случайно или по ошибке) депонировать 1 микро-STX, и **резерв навсегда останется почти пустым** — второй попытки нет (`ERR_RESERVE_DEPOSITED`).
Impact: резерв (≈$200) не доходит до LAB; донорские USDCx не затронуты.
Рекомендация: либо требовать минимума/полной суммы, либо разрешить доклад при `reserve-deposited` (флаг «полностью» отдельно).

### F-2 (Low/QA): `release-seat` не проверяет `total == TARGET` в момент выпуска
`release-seat` (стр. 387) полагается на инвариант «`seat-request` существует ⇒ цель собрана», который держится только за счёт проверки в `request-seat` (стр. 361). Прямой защиты в самом `release-seat` нет.
Impact: при будущей правке (например, разрешить `request-seat` до цели или добавить ветку) OWNER сможет выпустить недобранный раунд LAB и **обнулить `unrefunded`** (стр. 399), лишив доноров возврата.
Рекомендация: добавить `(asserts! (is-eq (var-get total) TARGET) ERR_TARGET_NOT_REACHED)` в `release-seat`.

### F-3 (Low): `claim-reserve` может откатываться при `balance < unrefunded` (underflow `(- (usdcx-balance) (var-get unrefunded))`, стр. 424)
Сейчас недостижимо (баланс всегда ≥ подарков), но любая fee-on-transfer/rebasing-семантика USDCx или будущая ветка (частичный `release-seat`) сделает вызов `claim-reserve` **всегда падающим**, и резерв LAB останется заблокированным до `refund-many` всех доноров.
Рекомендация: `(if (>= bal unrefunded) (- bal unrefunded) u0)`.

### F-4 (Info): `refund-many` без доноров (пустой список) бесполезен и стоит комиссии
`(list 100 principal)` позволяет передать пустой список: вызов пройдёт `check-refunds`, сделает `as-contract?`/`with-ft` и вернёт 0. Мелочь, но при пакетном кране это лишние неудачные попытки.

### F-5 (Info): `get-status.refunds-open` не учитывает `claim` резерва
`refunds-open` (стр. 202) = `height >= failure-at && !seat-claimed`. После `claim-reserve` статус всё ещё «refunds open» — это верно по коду, но UI может прочитать как «ещё ничего не забрано». Рекомендуется добавить поле `reserve-claimed`.

## Чего не нашёл
Двойных рефандов, обхода подписей, переполнения цели, утечки донорских средств, блокировки рефандов после claim-reserve (проверяется только `seat-claimed`), обхода `contract-caller` через прокси-контракт.

## Формат подачи
AIBTC: short report + reproduction. Для F-1/F-2 репро делается unit-тестом Clarinet (без сети): вызвать `deposit-reserve` с `stx = 1`, затем проверить, что второй вызов даёт `ERR_RESERVE_DEPOSITED`; для F-2 — вызвать `release-seat` на состоянии с `total < TARGET` (требует временной правки контракта, поэтому в отчёте это «reasoned review», а не PoC).

---

## Machine-checked invariants (Lean 4)

Модель: `projects/kairan-lean/Kairan.lean` (5 теорем) и `KairanFlow.lean` (7 теорем).
Оба компилируются: `lean Kairan.lean` и `lean KairanFlow.lean` -> EXIT=0, 0 sorry, без аксиом.

Доказано (для модели учёта, не байткода):

1. `donate_safe`, `refund_safe`, `claim_reserve_safe` — долг донорам никогда не превышает
   собранное ни в одном переходе.
2. `deposit_conserved`, `payLab_conserved`, `payDonor_conserved` — сохранение средств:
   `toLab + toDonor + held = inflow` до и после каждого перехода.
3. `no_third_party` — оба payout-перехода увеличивают ровно одну из двух разрешённых статей
   (LAB или донор) и ничего не оставляют на сторону. Машинная проверка утверждения TERMS
   «Funds may only ever go to LAB or back to donors».
4. `refund_zeroes`, `refund_idempotent`, `refund_pays_zero_second_time` — возврат обнуляет долг
   и ставит флаг; второй возврат ничего не меняет, то есть двойной рефанд невозможен.
5. `shortfall_release_wipes_donors` — контрпример: при недобранной цели (total = 100,
   unrefunded = 100) release-seat обнуляет долг донорам целиком. Значит проверка
   `(is-eq (var-get total) TARGET)` в request-seat несущая: без неё F-2 становится путём
   потери средств.

Границы модели: доказано для арифметики учёта и переходов; соответствие модели и Clarity-кода
не верифицировано; переводы токенов считаются успешными; переполнение uint и cost limits вне модели.

Зачем это в отчёте: обычно аудит пишет «класс атак X закрыт». Здесь это утверждение проверено
машиной для двух ключевых классов — «третье лицо не получает средств» и «двойной возврат»,
плюс показано, почему конкретный assert обязателен.
