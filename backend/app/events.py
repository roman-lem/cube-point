"""Events. The IDs match WCA; the list can be extended."""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Event:
    name: str
    result_type: str  # "time" or "moves", as in results.py
    default_format: str


# In the standard WCA order: this order is used everywhere in the API.
EVENTS = {
    "333": Event(name="3×3", result_type="time", default_format="ao5"),
    "222": Event(name="2×2", result_type="time", default_format="ao5"),
    "444": Event(name="4×4", result_type="time", default_format="ao5"),
    "555": Event(name="5×5", result_type="time", default_format="ao5"),
    "666": Event(name="6×6", result_type="time", default_format="mo3"),
    "777": Event(name="7×7", result_type="time", default_format="mo3"),
    "333bf": Event(name="3×3 вслепую", result_type="time", default_format="bo5"),
    "333fm": Event(name="Минимум ходов", result_type="moves", default_format="bo1"),
    "333oh": Event(name="3×3 одной рукой", result_type="time", default_format="ao5"),
    "clock": Event(name="Clock", result_type="time", default_format="ao5"),
    "minx": Event(name="Мегаминкс", result_type="time", default_format="ao5"),
    "pyram": Event(name="Пирамидка", result_type="time", default_format="ao5"),
    "skewb": Event(name="Скьюб", result_type="time", default_format="ao5"),
    "sq1": Event(name="Square-1", result_type="time", default_format="ao5"),
    "444bf": Event(name="4BLD", result_type="time", default_format="bo3"),
    "555bf": Event(name="5BLD", result_type="time", default_format="bo3"),
}

# Position of an event in the WCA order, for sorting.
EVENT_ORDER = {event_id: index for index, event_id in enumerate(EVENTS)}

# Time limit for an FMC attempt; each attempt has its own hour.
FMC_TIME_LIMIT = timedelta(minutes=60)


def is_fmc(event_id):
    return EVENTS[event_id].result_type == "moves"
