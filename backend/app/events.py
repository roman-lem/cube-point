"""Events. The IDs match WCA; the list can be extended."""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Event:
    name: str
    result_type: str  # "time" or "moves", as in results.py
    default_format: str


EVENTS = {
    "333": Event(name="3×3", result_type="time", default_format="ao5"),
    "222": Event(name="2×2", result_type="time", default_format="ao5"),
    "333oh": Event(name="3×3 одной рукой", result_type="time", default_format="ao5"),
    "pyram": Event(name="Пирамидка", result_type="time", default_format="ao5"),
    "333fm": Event(name="Минимум ходов", result_type="moves", default_format="bo1"),
    "333bf": Event(name="3×3 вслепую", result_type="time", default_format="bo5"),
}

# Time limit for an FMC attempt; each attempt has its own hour.
FMC_TIME_LIMIT = timedelta(minutes=60)


def is_fmc(event_id):
    return EVENTS[event_id].result_type == "moves"
