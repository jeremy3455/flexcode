import re

from tools.datetime_tool import get_current_datetime


def test_default_format():
    result = get_current_datetime()
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result)


def test_custom_format():
    result = get_current_datetime("%Y")
    assert re.match(r"\d{4}", result)
    assert len(result) == 4


def test_date_only():
    result = get_current_datetime("%Y-%m-%d")
    assert re.match(r"\d{4}-\d{2}-\d{2}", result)


def test_time_only():
    result = get_current_datetime("%H:%M:%S")
    assert re.match(r"\d{2}:\d{2}:\d{2}", result)
