"""Tests for snapshot_grocy_ids_for_window / fetch_new_grocy_rows_window.

These guard the post-POST candidate-identification step: with multiple users
writing concurrently against Grocy, the tuple-only match could attribute
another user's row to the local batch. row_created_timestamp filtering
narrows the candidate set to only rows actually created after we took the
pre-batch snapshot.
"""

from datetime import date
from unittest.mock import MagicMock

from app.services.meal_plan import (
    fetch_new_grocy_rows_window,
    snapshot_grocy_ids_for_window,
)


def _grocy(*, id_: int, day: str, ts: str | None) -> dict:
    return {
        "id": id_,
        "day": day,
        "section_id": 1,
        "type": "product",
        "product_id": 10,
        "product_amount": "1",
        "product_qu_id": 2,
        "row_created_timestamp": ts,
    }


def test_snapshot_returns_ids_and_max_timestamp() -> None:
    api = MagicMock()
    api.get_meal_plan.return_value = [
        _grocy(id_=1, day="2026-05-12", ts="2026-05-12 09:00:00"),
        _grocy(id_=2, day="2026-05-12", ts="2026-05-12 11:45:00"),
        _grocy(id_=3, day="2026-05-12", ts="2026-05-12 10:00:00"),
    ]

    ids, max_ts = snapshot_grocy_ids_for_window(api, date(2026, 5, 12), date(2026, 5, 12))

    assert ids == {1, 2, 3}
    assert max_ts == "2026-05-12 11:45:00"


def test_snapshot_returns_none_max_when_empty() -> None:
    api = MagicMock()
    api.get_meal_plan.return_value = []

    ids, max_ts = snapshot_grocy_ids_for_window(api, date(2026, 5, 12), date(2026, 5, 12))

    assert ids == set()
    assert max_ts is None


def test_fetch_new_excludes_rows_with_id_in_snapshot() -> None:
    api = MagicMock()
    api.get_meal_plan.return_value = [
        _grocy(id_=1, day="2026-05-12", ts="2026-05-12 09:00:00"),
        _grocy(id_=5, day="2026-05-12", ts="2026-05-12 12:00:00"),
    ]

    candidates = fetch_new_grocy_rows_window(
        api,
        date(2026, 5, 12),
        date(2026, 5, 12),
        snapshot_ids={1},
        snapshot_max_ts="2026-05-12 09:00:00",
    )

    assert [c["id"] for c in candidates] == [5]


def test_fetch_new_excludes_rows_with_timestamp_le_snapshot_max() -> None:
    """A row not in snapshot_ids but with timestamp <= snapshot_max was created
    by someone else *before* we snapshotted (it must have been added between
    list and our timestamp read — extremely unlikely, but the filter is the
    safety net). We must exclude it."""
    api = MagicMock()
    api.get_meal_plan.return_value = [
        # Not in snapshot, but timestamp predates the snapshot max → exclude.
        _grocy(id_=2, day="2026-05-12", ts="2026-05-12 08:00:00"),
        # Not in snapshot AND newer → include.
        _grocy(id_=3, day="2026-05-12", ts="2026-05-12 12:30:00"),
    ]

    candidates = fetch_new_grocy_rows_window(
        api,
        date(2026, 5, 12),
        date(2026, 5, 12),
        snapshot_ids={1},
        snapshot_max_ts="2026-05-12 10:00:00",
    )

    assert [c["id"] for c in candidates] == [3]


def test_fetch_new_without_snapshot_max_falls_back_to_id_only_diff() -> None:
    """When the snapshot was empty (no max ts), only id-not-in-set filter
    applies — preserving prior behavior for first-time batches."""
    api = MagicMock()
    api.get_meal_plan.return_value = [
        _grocy(id_=1, day="2026-05-12", ts=None),
        _grocy(id_=2, day="2026-05-12", ts=None),
    ]

    candidates = fetch_new_grocy_rows_window(
        api,
        date(2026, 5, 12),
        date(2026, 5, 12),
        snapshot_ids=set(),
        snapshot_max_ts=None,
    )

    assert [c["id"] for c in candidates] == [1, 2]
