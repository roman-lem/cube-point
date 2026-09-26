"""Series results, training averages and formatting for display.

This is the source of truth. The frontend repeats the same logic in
frontend/src/shared/lib/results/results.ts; both implementations are checked
by the shared cases in testdata/results_cases.json.

Time is an integer in hundredths of a second, FMC is a number of moves.
The FMC mean is in hundredths of a move. An attempt is a dict
{"value": int | None, "penalty": "none" | "plus2" | "dnf" | "dns"}.
"""

# DNF result (of an attempt or a series). DNS also gives DNF in calculations.
DNF = -1

PENALTIES = ("none", "plus2", "dnf", "dns")
RESULT_TYPES = ("time", "moves")
ATTEMPTS_COUNT = {"ao5": 5, "mo3": 3, "bo5": 5, "bo3": 3, "bo1": 1}

PLUS_TWO = 200  # +2 seconds in hundredths


def attempt_value(attempt, result_type):
    """Final value of an attempt: with the +2 penalty, or DNF."""
    _check_attempt(attempt, result_type)
    if attempt["penalty"] in ("dnf", "dns"):
        return DNF
    if attempt["penalty"] == "plus2":
        return attempt["value"] + PLUS_TWO
    return attempt["value"]


def calc_series(attempts, series_format, result_type):
    """Best result, average and counting attempts of a series.

    attempts are in order, no more than the format's number of attempts.
    An attempt not yet done is None or missing at the end of the list.

    Returns a dict:
      best     — best of the entered attempts, DNF, or None if there are no attempts;
      average  — average for ao5 and mo3, DNF, or None while the series is unfinished;
                 always None for bo formats;
      counting — a flag for each attempt of the format: False for the ones dropped
                 in ao5 (shown in parentheses). While the series is unfinished,
                 all are True.
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
        # Two DNFs make the average DNF right away, even if the series is unfinished.
        # The remaining attempts can still be done.
        if dnf_count >= 2:
            average = DNF
        if is_complete:
            # Stable sort: on ties the first of the best
            # and the last of the worst are dropped.
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
    """Average of the last n attempts (training ao5, ao12), or None if there are fewer than n.

    One best and one worst attempt are dropped, the rest are averaged.
    One DNF is dropped as the worst; two or more make the average DNF.
    """
    _check_window(n)
    if result_type not in RESULT_TYPES:
        raise ValueError(f"Неизвестный тип результата: {result_type}")
    if len(attempts) < n:
        return None
    values = [attempt_value(a, result_type) for a in attempts[-n:]]
    return _trimmed_mean(values, result_type)


def rolling_averages(attempts, n, result_type):
    """Rolling averages: for each attempt, the average of the n attempts
    ending with it (as average_of). The first n - 1 attempts get None.
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
    """Result for display: 9.87, 1:02.45, 1:05:23.45, 28, 28.33, DNF, —."""
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
    """Attempt for display: 9.87, 11.87 (+2), DNF, DNS, —."""
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
    # bool is a subclass of int in Python, so it is excluded explicitly.
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"Значение попытки должно быть целым больше нуля: {value}")


def _check_window(n):
    # Fewer than three attempts: nothing left to average after dropping the best and worst.
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError(f"Число попыток для среднего должно быть не меньше 3: {n}")


def _trimmed_mean(values, result_type):
    """Average without one best and one worst attempt; two or more DNFs give DNF."""
    if values.count(DNF) >= 2:
        return DNF
    kept = sorted(values, key=_sort_key)[1:-1]
    return _mean(kept, result_type)


def _sort_key(value):
    # DNF is worse than any time.
    return (value == DNF, value)


def _best(values):
    successful = [v for v in values if v != DNF]
    if successful:
        return min(successful)
    if values:
        return DNF
    return None


def _mean(values, result_type):
    # Round down to hundredths: thousandths are simply dropped.
    total = sum(values)
    if result_type == "moves":
        total *= 100  # the FMC mean is in hundredths of a move
    return total // len(values)


def _format_time(centiseconds):
    hours, rest = divmod(centiseconds, 360_000)
    minutes, rest = divmod(rest, 6000)
    seconds, hundredths = divmod(rest, 100)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}.{hundredths:02d}"
    if minutes:
        return f"{minutes}:{seconds:02d}.{hundredths:02d}"
    return f"{seconds}.{hundredths:02d}"
