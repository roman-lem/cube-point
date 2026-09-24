"""Проверка подсчёта результатов по общим случаям с фронтендом."""

import json
from pathlib import Path

import pytest

from app.results import calc_series, format_attempt, format_result

CASES_PATH = Path(__file__).parents[2] / "testdata" / "results_cases.json"
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))


def case_id(case):
    return case.get("name") or json.dumps(case, ensure_ascii=False)


@pytest.mark.parametrize("case", CASES["calcSeries"], ids=case_id)
def test_calc_series(case):
    result = calc_series(case["attempts"], case["format"], case["resultType"])

    assert result == case["expected"]


@pytest.mark.parametrize("case", CASES["calcSeriesErrors"], ids=case_id)
def test_calc_series_errors(case):
    with pytest.raises(ValueError):
        calc_series(case["attempts"], case["format"], case["resultType"])


@pytest.mark.parametrize("case", CASES["formatResult"], ids=case_id)
def test_format_result(case):
    text = format_result(case["value"], case["resultType"], case["isAverage"])

    assert text == case["expected"]


@pytest.mark.parametrize("case", CASES["formatAttempt"], ids=case_id)
def test_format_attempt(case):
    assert format_attempt(case["attempt"], case["resultType"]) == case["expected"]
