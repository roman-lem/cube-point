"""Подсчёт результатов серии, средних тренировки и форматирование для отображения.

Это источник правды. Фронтенд повторяет ту же логику в
frontend/src/shared/lib/results/results.ts, обе реализации проверяются
общими тестами из testdata/results_cases.json.

Время — целое число в сотых долях секунды, FMC — число ходов.
Среднее FMC — в сотых долях хода. Попытка — словарь
{"value": int | None, "penalty": "none" | "plus2" | "dnf" | "dns"}.
"""

# Результат DNF (попытки или серии). DNS в подсчёте тоже даёт DNF.
DNF = -1

PENALTIES = ("none", "plus2", "dnf", "dns")
RESULT_TYPES = ("time", "moves")
ATTEMPTS_COUNT = {"ao5": 5, "mo3": 3, "bo5": 5, "bo3": 3, "bo1": 1}

PLUS_TWO = 200  # +2 секунды в сотых долях


def attempt_value(attempt, result_type):
    """Итоговое значение попытки: со штрафом +2 или DNF."""
    _check_attempt(attempt, result_type)
    if attempt["penalty"] in ("dnf", "dns"):
        return DNF
    if attempt["penalty"] == "plus2":
        return attempt["value"] + PLUS_TWO
    return attempt["value"]


def calc_series(attempts, series_format, result_type):
    """Лучший результат, среднее и учитываемые попытки серии.

    attempts — попытки по порядку, не больше числа попыток формата.
    Несобранная попытка — None или отсутствует в конце списка.

    Возвращает словарь:
      best     — лучшая из введённых попыток, DNF или None, если попыток нет;
      average  — среднее для ao5 и mo3, DNF или None, пока серия не закончена;
                 для bo-форматов всегда None;
      counting — по флагу на каждую попытку формата: False у отброшенных
                 в ao5 (показываются в скобках). Пока серия не закончена,
                 все True.
    """
    if series_format not in ATTEMPTS_COUNT:
        raise ValueError(f"Неизвестный формат: {series_format}")
    if result_type not in RESULT_TYPES:
        raise ValueError(f"Неизвестный тип результата: {result_type}")
    count = ATTEMPTS_COUNT[series_format]
    if len(attempts) > count:
        raise ValueError(f"В формате {series_format} не больше {count} попыток")

    values = [attempt_value(a, result_type) for a in attempts if a is not None]
    is_complete = len(values) == count
    dnf_count = values.count(DNF)

    average = None
    counting = [True] * count

    if series_format == "ao5":
        # Два DNF — среднее DNF сразу, даже если серия не закончена.
        # Остальные попытки при этом всё равно можно дособрать.
        if dnf_count >= 2:
            average = DNF
        if is_complete:
            # Стабильная сортировка: при равенстве отбрасывается
            # первая из лучших и последняя из худших.
            order = sorted(range(count), key=lambda i: _sort_key(values[i]))
            dropped = {order[0], order[-1]}
            counting = [i not in dropped for i in range(count)]
            average = _trimmed_mean(values, result_type)

    elif series_format == "mo3":
        if dnf_count >= 1:
            average = DNF
        elif is_complete:
            average = _mean(values, result_type)

    return {"best": _best(values), "average": average, "counting": counting}


def average_of(attempts, n, result_type):
    """Среднее последних n попыток (ao5, ao12 тренировки) или None, если их меньше n.

    Отбрасываются одна лучшая и одна худшая попытка, остальные усредняются.
    Один DNF отбрасывается как худшая, два и более — среднее DNF.
    """
    _check_window(n)
    if result_type not in RESULT_TYPES:
        raise ValueError(f"Неизвестный тип результата: {result_type}")
    if len(attempts) < n:
        return None
    values = [attempt_value(a, result_type) for a in attempts[-n:]]
    return _trimmed_mean(values, result_type)


def rolling_averages(attempts, n, result_type):
    """Скользящие средние: для каждой попытки — среднее n попыток, которыми
    она заканчивается (как average_of). У первых n - 1 попыток — None.
    """
    _check_window(n)
    if result_type not in RESULT_TYPES:
        raise ValueError(f"Неизвестный тип результата: {result_type}")
    values = [attempt_value(a, result_type) for a in attempts]
    return [
        _trimmed_mean(values[i + 1 - n:i + 1], result_type) if i + 1 >= n else None
        for i in range(len(values))
    ]


def format_result(value, result_type, is_average=False):
    """Результат для отображения: 9.87, 1:02.45, 28, 28.33, DNF, —."""
    if result_type not in RESULT_TYPES:
        raise ValueError(f"Неизвестный тип результата: {result_type}")
    if value is None:
        return "—"
    if value == DNF:
        return "DNF"
    if result_type == "moves":
        if is_average:
            return f"{value // 100}.{value % 100:02d}"
        return str(value)
    return _format_time(value)


def format_attempt(attempt, result_type):
    """Попытка для отображения: 9.87, 11.87 (+2), DNF, DNS, —."""
    if attempt is None:
        return "—"
    value = attempt_value(attempt, result_type)
    if attempt["penalty"] == "dns":
        return "DNS"
    text = format_result(value, result_type)
    if attempt["penalty"] == "plus2":
        text += " (+2)"
    return text


def _check_attempt(attempt, result_type):
    penalty = attempt["penalty"]
    value = attempt["value"]
    if penalty not in PENALTIES:
        raise ValueError(f"Неизвестный штраф: {penalty}")
    if penalty == "plus2" and result_type == "moves":
        raise ValueError("В FMC нет штрафа +2")
    if value is None:
        if penalty in ("none", "plus2"):
            raise ValueError("У попытки без DNF/DNS должно быть значение")
        return
    # bool — подкласс int в Python, его отсекаем явно.
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"Значение попытки должно быть целым больше нуля: {value}")


def _check_window(n):
    # Меньше трёх попыток: после отбрасывания лучшей и худшей нечего усреднять.
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError(f"Число попыток для среднего должно быть не меньше 3: {n}")


def _trimmed_mean(values, result_type):
    """Среднее без одной лучшей и одной худшей попытки; два DNF и более — DNF."""
    if values.count(DNF) >= 2:
        return DNF
    kept = sorted(values, key=_sort_key)[1:-1]
    return _mean(kept, result_type)


def _sort_key(value):
    # DNF хуже любого времени.
    return (value == DNF, value)


def _best(values):
    successful = [v for v in values if v != DNF]
    if successful:
        return min(successful)
    if values:
        return DNF
    return None


def _mean(values, result_type):
    # Округление вниз до сотых: тысячные просто отбрасываются.
    total = sum(values)
    if result_type == "moves":
        total *= 100  # среднее FMC — в сотых долях хода
    return total // len(values)


def _format_time(centiseconds):
    minutes, rest = divmod(centiseconds, 6000)
    seconds, hundredths = divmod(rest, 100)
    if minutes:
        return f"{minutes}:{seconds:02d}.{hundredths:02d}"
    return f"{seconds}.{hundredths:02d}"
