"""Дисциплины. Идентификаторы совпадают с WCA, список можно расширять."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    name: str
    result_type: str  # "time" или "moves", как в results.py
    default_format: str


EVENTS = {
    "333": Event(name="3×3", result_type="time", default_format="ao5"),
    "222": Event(name="2×2", result_type="time", default_format="ao5"),
    "333oh": Event(name="3×3 одной рукой", result_type="time", default_format="ao5"),
    "pyram": Event(name="Пирамидка", result_type="time", default_format="ao5"),
    "333fm": Event(name="Минимум ходов", result_type="moves", default_format="bo1"),
    "333bf": Event(name="3×3 вслепую", result_type="time", default_format="bo5"),
}
