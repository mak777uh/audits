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

---

## Повторный проход: сборка в clarinet 3.25.0 (Clarity 4 / epoch 3.3)

# Kairan's Seat — аудит Clarity-контракта (24.10.2026)

Объект: `kairan-seat-lab-ocifarsito-v2.clar` (487 строк, 23.9 КБ, недеплоенный)
Источник: `github.com/Rapha-btc/jing-contracts-v3` → `contracts/charity/kairan-seat-lab-ocifarsito-v2.clar`
Инструмент: **clarinet 3.25.0**, Clarity 4 / epoch 3.3, локальные моки USDCx и sBTC.

## 0. Проверка сборки

Контракт **проходит анализ типов** (`as-contract?` — фича Clarity 4; на epoch 2.5/3.0 анализатор
её не знает, поэтому проверять надо именно Clarity 4). Замечания анализатора — только линты
(`unwrap-panic` вместо `try!`, неиспользуемые константы). Вывод: **синтаксис и типы в порядке**,
искать надо в логике.

## 1. Findings

### K-1 (Medium, дизайн/деньги). LAB может забрать резерв, не выдав место
Сценарий: TARGET собран → LAB **не** подаёт seat-request (или подаёт, но owner не подтверждает) →
через `SEAT_WINDOW` (12 960 блоков ≈ 90 дней) открываются возвраты → LAB вызывает `claim-reserve`
и получает **весь STX + sBTC резерв** (~$200 по условиям), донорам возвращается USDCx.

То есть LAB получает резерв (в Builder Fund pool) **без исполнения обязательства** — место не выдано.
Термсы это формально допускают («Reserve on failure: … LAB may claim the reserve»), но экономически
это стимул не выдавать место: 2 000 USDCx вернутся донорам, а ~$200 резерва останутся у LAB.
Для жертвователя это выглядит как «резерв ушёл, место не появилось».

Проверка: `claim-reserve` (стр. 417–439) требует только `block >= failure-at` и `claim = none`;
условия «место было выдано» нет. `refund-many` работает независимо, поэтому доноры не теряют USDCx —
страдает именно смысл резерва.

Рекомендация: либо запретить `claim-reserve`, пока `seat-request = some`, либо добавить явный
флаг «seat не выдан по вине LAB» и отправлять резерв обратно FUNDRAISER в этом случае.

### K-2 (Low/Info). `deposit-reserve` проверяет не тот срок, что обещано в комментарии
Комментарий (стр. 320–322): «once, **before DEADLINE** and before failure-at».
Код (стр. 331–332): `check-raising` (в нём есть проверка `< DEADLINE`) + `< failure-at`.
Комментарий не врёт, но проверка `failure-at` избыточна и вводит в заблуждение: если TARGET собран,
`failure-at = reached-at + SEAT_WINDOW` может быть **позже** DEADLINE, и FUNDRAISER внесёт резерв
уже после формального дедлайна. Логика не ломается, но документированное поведение и код расходятся.

### K-3 (Medium, риск блокировки). `OWNER` = `tx-sender` в момент деплоя
`(define-constant OWNER tx-sender)` (стр. 18): владелец фиксируется на деплое.
Если контракт развернуть **не напрямую с кошелька, а деплой-контрактом** (частая практика в Stacks),
`OWNER` станет principal'ом этого контракта, и `release-seat` (стр. 392: `contract-caller == OWNER`)
сможет вызвать только сам деплой-контракт. Если он такой функции не имеет — **`release-seat`
невозможен навсегда**, а значит успешный сценарий (выдача места) не реализуется: всё уйдёт в возвраты.
Это не эксплойт, но реальный риск потери функции контракта.

Рекомендация: сделать владельца явным параметром (`initialize(owner)`) или проверять
`(is-eq tx-sender OWNER)` при `contract-caller`-семантике, и добавить тест «деплой через контракт».

### K-4 (Info). `get-status.closed` считает не то
`closed` = `seat-claimed || (claim is-some && unrefunded == 0)`. После `claim-reserve` с
непустыми возвратами `closed = false`, хотя контракт уже ничего не может выплатить, кроме возвратов.
Влияние только на UI/интеграции. Рекомендация: `closed = (claim is-some) && (!refunds-open)`.

### K-5 (Info, газ). `refund-many` можно гонять с пустыми списками
Любой может вызывать `refund-many` со списком из 100 не-доноров сколько угодно раз: `paid = 0`,
состояние не меняется, но транзакция оплачивается. Не влияет на деньги, только шум в истории. Рекомендация: `asserts! (> paid u0)`.

## 2. Что проверил и НЕ нашёл

- переполнение `(- TARGET total)`: `total ≤ TARGET` поддерживается `ERR_OVER_TARGET` — ок;
- `extra = balance - unrefunded` в `claim-reserve`: недопустимого underflow нет, т.к. возвраты
  уменьшают баланс и `unrefunded` одинаково;
- двойной возврат одному донору: `gift` обнуляется (`map-set gifts who u0`) — ок;
- передонат после TARGET: `remaining = 0` → `ERR_AMOUNT_ZERO`/`ERR_OVER_TARGET` — ок;
- `reached-at` выставляется ровно один раз при `total == TARGET` — ок;
- гонка `request-seat` / `release-seat`: последний request побеждает, owner платит всё LAB — по замыслу;
- `pay` с нулевыми суммами: `and (> x u0)` пропускает нули, `as-contract?` с allowance — ок;
- «чужие» USDCx (прямо на контракт) уходят LAB: и при успехе, и через `extra` при провале — как в термсах.

## 3. Предлагаемая подача

Приоритет: **K-1** (деньги/стимулы) и **K-3** (риск навсегда потерять `release-seat`).
K-2/K-4/K-5 — как «minor / info» приложением.

Формат: 3 пункта с номерами строк + минимальные патчи, без PoC (контракт недеплоенный, эксплойта нет).
Если автор захочет PoC — соберу `clarinet`-тест на K-3 (деплой через контракт) за ~30 минут.
