"""
Unit tests for app/utils/helpers.py

Tests: get_week_range, get_first_day_of_current_week, get_week_days,
       handle_response, get_content
Pure unit tests without a database.
"""

from datetime import date, datetime
from unittest.mock import Mock

import httpx
import pytest

from app.utils.helpers import (
    get_content,
    get_first_day_of_current_week,
    get_week_days,
    get_week_range,
    handle_response,
)


@pytest.mark.unit
class TestGetWeekRange:
    """Tests for the week range function."""

    def test_returns_tuple_of_two_strings(self):
        # Arrange & Act
        result = get_week_range(2024, 10)
        # Assert
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    def test_end_is_exactly_6_days_after_start(self):
        start, end = get_week_range(2024, 20)
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        delta = end_date - start_date
        assert delta.days == 6

    def test_dates_are_in_correct_format(self):
        start, end = get_week_range(2024, 5)
        # Must be in YYYY-MM-DD format
        datetime.strptime(start, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")

    def test_week_1_of_2024_starts_on_monday(self):
        # ISO week 1 of 2024 starts on January 1st (Monday)
        start, _end = get_week_range(2024, 1)
        start_date = datetime.strptime(start, "%Y-%m-%d")
        assert start_date.weekday() == 0  # 0 = Monday

    def test_week_end_is_sunday(self):
        _start, end = get_week_range(2024, 15)
        end_date = datetime.strptime(end, "%Y-%m-%d")
        assert end_date.weekday() == 6  # 6 = Sunday

    def test_consecutive_weeks_are_adjacent(self):
        _, end_week10 = get_week_range(2024, 10)
        start_week11, _ = get_week_range(2024, 11)
        end_date = datetime.strptime(end_week10, "%Y-%m-%d")
        start_date = datetime.strptime(start_week11, "%Y-%m-%d")
        delta = start_date - end_date
        assert delta.days == 1


@pytest.mark.unit
class TestGetFirstDayOfCurrentWeek:
    """Tests for the first day of current week function."""

    def test_returns_string_in_date_format(self):
        result = get_first_day_of_current_week()
        assert isinstance(result, str)
        # Must be in YYYY-MM-DD format
        datetime.strptime(result, "%Y-%m-%d")

    def test_returned_date_is_monday(self):
        result = get_first_day_of_current_week()
        day = datetime.strptime(result, "%Y-%m-%d")
        assert day.weekday() == 0  # 0 = Monday

    def test_returned_date_is_within_current_week(self):
        today = datetime.today()
        result = get_first_day_of_current_week()
        result_date = datetime.strptime(result, "%Y-%m-%d")
        # Difference between today and Monday is at most 6 days
        delta = today - result_date
        assert 0 <= delta.days <= 6


@pytest.mark.unit
class TestGetWeekDays:
    """Tests for the get all week days function."""

    def test_returns_list_of_7_days(self):
        result = get_week_days("2024-10")
        assert len(result) == 7

    def test_first_day_is_monday(self):
        days = get_week_days("2024-10")
        first = date.fromisoformat(days[0])
        assert first.weekday() == 0  # Monday

    def test_last_day_is_sunday(self):
        days = get_week_days("2024-10")
        last = date.fromisoformat(days[6])
        assert last.weekday() == 6  # Sunday

    def test_days_are_consecutive(self):
        days = get_week_days("2024-15")
        dates = [date.fromisoformat(d) for d in days]
        for i in range(1, 7):
            delta = dates[i] - dates[i - 1]
            assert delta.days == 1

    def test_all_days_in_iso_format(self):
        days = get_week_days("2024-1")
        for day in days:
            # Should not raise an exception
            date.fromisoformat(day)

    def test_returns_strings_not_date_objects(self):
        days = get_week_days("2024-20")
        for day in days:
            assert isinstance(day, str)

    def test_week_string_with_single_digit_week(self):
        # Week with a single-digit number
        days = get_week_days("2024-1")
        assert len(days) == 7
        first = date.fromisoformat(days[0])
        assert first.weekday() == 0


@pytest.mark.unit
class TestHandleResponse:
    """Tests for the HTTP response handling function."""

    def test_successful_200_json_response_returns_dict(self):
        # Arrange
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = b'{"key": "value"}'
        mock_resp.json.return_value = {"key": "value"}
        # Act
        result = handle_response(mock_resp)
        # Assert
        assert result == {"key": "value"}

    def test_204_no_content_response_returns_none(self):
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.status_code = 204
        mock_resp.raise_for_status.return_value = None
        result = handle_response(mock_resp)
        assert result is None

    def test_http_error_returns_error_dict(self):
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_resp
        )
        mock_resp.content = b"Not Found"
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "Not Found"
        result = handle_response(mock_resp)
        assert isinstance(result, dict)
        assert "error" in result
        assert "content" in result

    def test_http_error_contains_error_message(self):
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=Mock(), response=mock_resp
        )
        mock_resp.content = b"Server Error"
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "Server Error"
        result = handle_response(mock_resp)
        assert "500 Server Error" in result["error"]

    def test_text_response_returns_string(self):
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = b"plain text"
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "plain text"
        result = handle_response(mock_resp)
        assert result == "plain text"


@pytest.mark.unit
class TestGetContent:
    """Tests for the response content extraction function."""

    def test_json_content_returns_dict(self):
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.content = b'{"result": true}'
        mock_resp.json.return_value = {"result": True}
        result = get_content(mock_resp)
        assert result == {"result": True}

    def test_empty_content_returns_none(self):
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.content = b""
        result = get_content(mock_resp)
        assert result is None

    def test_non_json_content_returns_text_string(self):
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.content = b"plain text response"
        mock_resp.json.side_effect = ValueError("not valid json")
        mock_resp.text = "plain text response"
        result = get_content(mock_resp)
        assert result == "plain text response"

    def test_list_json_content_returns_list(self):
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.content = b"[1, 2, 3]"
        mock_resp.json.return_value = [1, 2, 3]
        result = get_content(mock_resp)
        assert result == [1, 2, 3]

    def test_none_content_returns_none(self):
        # content can be falsy (empty byte string)
        mock_resp = Mock(spec=httpx.Response)
        mock_resp.content = None
        result = get_content(mock_resp)
        assert result is None
