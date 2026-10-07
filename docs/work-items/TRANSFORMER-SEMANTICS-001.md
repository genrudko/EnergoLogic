# TRANSFORMER-SEMANTICS-001

Status: **Accepted and merged to `main`**
Issue: #9
Draft PR: #10


## Final repository reconciliation

Merged via PR #10 as `9edc59a` on 2026-10-03.

Any unchecked owner/Ready/Merge boxes or pre-merge wording later in this file are **historical candidate-state evidence** and do not override this final repository status.

## Цель

Научить EnergoLogic корректно понимать двухобмоточный трансформатор как один аппарат с разными напряжениями на сторонах ВН и НН.

Первый квалифицированный объект — native VTD master `ТСН2`.

## Главное решение

Для обычного оборудования напряжение по-прежнему хранится на всём элементе:

`element.attributes.nominal_voltage_v`

Для `transformer_2w` напряжение хранится отдельно на выводах:

- `hv`;
- `lv`.

Каждый вывод содержит либо:

- точное положительное целое `nominal_voltage_v`; либо
- квалифицированный `voltage_class`.

Voltage classes не разрешены на обычных элементах: они введены именно для терминальных случаев, где источник данных не даёт точного значения.

## Первый voltage class

`below_3000_v`

означает строго:

`0 < U < 3000 V`

Поэтому:

- 400 В совместимы;
- 2999 В совместимы;
- 3000 В не совместимы;
- 6 кВ не совместимы.

## Схема соединения обмоток

На каждом выводе `transformer_2w` также хранится `winding_connection`.

Поддержаны:

- delta;
- open_delta;
- three_single_phase;
- star;
- star_with_neutral;
- star_grounded_neutral;
- zigzag;
- zigzag_with_neutral.

Значение VTD «не определено» считается недостаточным и импортируется с явной ошибкой.

## Проверка сторон ВН/НН

Проверка электрических соединений теперь использует напряжение **конкретного endpoint**.

Кроме того, если данные однозначно показывают, что `hv` имеет меньшее напряжение, чем `lv`, модель отклоняется как ошибочная.

Если из широкого voltage class порядок нельзя определить однозначно, модель не делает предположений.

## Живое исследование Visio

Источник:

`KRU-35_normal_scheme_v2_energologic_switching_v1.vsdx`

Проверены реальные `ТСН2`:

- `MCP-v2 #166`;
- `Страница-1 #353`.

Обе фигуры структурированно хранят:

- `U1 = INDEX(10) = 35 кВ`;
- `U2 = INDEX(16) = ниже 3 кВ`;
- `S1 = INDEX(1) = треугольник`;
- `S2 = INDEX(4) = звезда`.

На старой странице имеется подпись `35/0,4 кВ`, но **0,4 кВ не является Shape Data трансформатора** и находится в отдельном текстовом блоке.

Следовательно, импорт `ТСН2` сохраняет:

- hv = 35000 V;
- lv = `below_3000_v`;

и не выдумывает 400 V.

## Точное 400 В

Canonical model может хранить точные 400 В, если они пришли из надёжного источника.

Такие 400 В считаются совместимыми с выводом класса `below_3000_v`.

Но текущая VTD-фигура `ТСН2` не умеет представить точные 400 В — только «ниже 3 кВ». Поэтому обратный render точных 400 В в этот master завершается явной ошибкой вместо незаметной потери точности.

## Visio mapping

Поддержан native master:

`Трансформаторы.vss / ТСН2`

Импорт:

- Prop.u → hv voltage;
- Prop.u2 → lv voltage/class;
- Prop.s1 → hv winding connection;
- Prop.s2 → lv winding connection.

Обратная проекция формирует те же U1/U2/S1/S2 и квалифицированные native defaults для направления U2 и цвета обмоток.

Для transformer:

- BeginX / Connections.1 → hv;
- EndX / Connections.2 → lv.

Полный автоматический rebuild сложной связанной трансформаторной ячейки пока не заявлен; квалифицирован точный standalone round-trip параметров native `ТСН2`.

## Live-квалификация

В документе была создана отдельная страница:

`EnergoLogic-Transformer-V1`

На неё помещён native `ТСН2 #1` и выставлены:

- U1 = 35 кВ;
- U2 = ниже 3 кВ;
- U1 = треугольник;
- U2 = звезда;
- U2 вывод вниз;
- цвет обмоток по классу напряжения.

Все значения прочитаны обратно из Shape Data и совпали.

Обязательный rendered visual gate показал штатный символ:

- верхняя обмотка — треугольник;
- нижняя — звезда;
- стороны визуально окрашены по своим классам напряжения.

PNG SHA-256 страницы:

`24b41c0a744b78abf16e2a6191f589721924cc36afdbc327d784d55249ff30fe`

После SaveAs этот же hash получен повторно.

Исходная `MCP-v2` после всех операций сохранила исторический PNG SHA-256:

`71eaa6244aef0dfe478ed052cf25b6ec8da58bd6d6cb32de7f83713e32f91648`

То есть исходная страница не изменилась.

Operator notes на контрольных точках были пусты.

Сохранена отдельная пятистраничная копия:

`C:\Users\Gennadiy\AppData\Local\OpenAI\VisioMCP\workspace\KRU-35_normal_scheme_v2_energologic_transformer_v1.vsdx`

## Тесты

Кодовый candidate:

`32bc7520bbc1249b6039234f93521dfa4b43544a`

CI:

https://github.com/genrudko/EnergoLogic/actions/runs/37114192586

Linux representative job: **70 tests PASS**.

Проверено, в частности:

- точный 35 кВ на hv;
- класс below-3-kV на lv;
- 400 В совместимы с below-3-kV;
- 6 кВ не совместимы;
- exact 400 V допустимы в canonical model;
- exact 400 V не деградируют молча при VTD render;
- неизвестный voltage class отклоняется;
- «не определено» в VTD отклоняется;
- схемы соединения обмоток валидируются;
- напряжения проверяются по конкретным выводам;
- перепутанные ВН/НН отклоняются, когда это можно доказать;
- switching-state profile остаётся совместим с трансформатором;
- ordinary equipment не получает расплывчатый voltage_class.

Canonical fingerprint примера:

`ae1156fe0898e6941109dd11af97a5fe3c6ec952657072b5b22cec5412c0f73b`

## Что сознательно не делаем

- РПН / ступени регулирования;
- номинальную мощность из свободного текста;
- uk%, потери, сопротивления;
- трёхобмоточные трансформаторы;
- автотрансформаторы;
- автоматическое угадывание 0,4 кВ по соседней подписи;
- расчёт потокораспределения;
- определение запитанных участков сети;
- РЗА;
- CIM.

## Acceptance

- [x] отдельная ветка и Draft PR;
- [x] transformer_2w в electrical-v1;
- [x] напряжение по конкретным выводам;
- [x] exact voltage / voltage class compatibility;
- [x] VTD U1/U2 mapping;
- [x] VTD S1/S2 mapping;
- [x] 400 В совместимы с below_3000_v;
- [x] импорт Visio не выдумывает 400 В;
- [x] перепутанные ВН/НН детектируются, когда порядок однозначен;
- [x] standalone VTD round-trip;
- [x] live Visio qualification;
- [x] visual gate;
- [x] reference page unchanged;
- [x] code candidate CI green;
- [x] final PR-head CI gate обязателен; фактический результат фиксируется в Issue/PR metadata;
- [ ] owner acceptance;
- [x] merge только по явной команде владельца.
