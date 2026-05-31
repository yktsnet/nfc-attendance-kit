import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from lib.attendance_store import (
    _iter_jsonl,
    append_event,
    append_jsonl,
    iter_events_month,
    month_events_path,
    month_payroll_path,
)

JST = ZoneInfo("Asia/Tokyo")


def dt(y, mo, d) -> datetime:
    return datetime(y, mo, d, 9, 0, tzinfo=JST)


# ---------------------------------------------------------------------------
# append_jsonl
# ---------------------------------------------------------------------------


class TestAppendJsonl:
    def test_creates_file_and_parent_dirs(self, tmp_path):
        p = tmp_path / "a" / "b" / "test.jsonl"
        assert not p.parent.exists()
        append_jsonl(p, {"key": "value"})
        assert p.exists()

    def test_written_line_is_readable(self, tmp_path):
        p = tmp_path / "test.jsonl"
        append_jsonl(p, {"key": "value"})
        results = list(_iter_jsonl(p))
        assert results == [{"key": "value"}]

    def test_multiple_appends(self, tmp_path):
        p = tmp_path / "test.jsonl"
        append_jsonl(p, {"n": 1})
        append_jsonl(p, {"n": 2})
        results = list(_iter_jsonl(p))
        assert len(results) == 2
        assert results[0]["n"] == 1
        assert results[1]["n"] == 2


# ---------------------------------------------------------------------------
# _iter_jsonl
# ---------------------------------------------------------------------------


class TestIterJsonl:
    def test_nonexistent_file_returns_empty(self, tmp_path):
        p = tmp_path / "nonexistent.jsonl"
        assert list(_iter_jsonl(p)) == []

    def test_empty_file_returns_empty(self, tmp_path):
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        assert list(_iter_jsonl(p)) == []

    def test_blank_lines_skipped(self, tmp_path):
        p = tmp_path / "test.jsonl"
        p.write_text('{"n":1}\n\n{"n":2}\n')
        results = list(_iter_jsonl(p))
        assert len(results) == 2

    def test_malformed_line_skipped_with_warning(self, tmp_path, caplog):
        p = tmp_path / "test.jsonl"
        p.write_text('{"valid":1}\nnot json\n{"valid":2}\n')
        with caplog.at_level(logging.WARNING, logger="lib.attendance_store"):
            results = list(_iter_jsonl(p))
        assert len(results) == 2
        assert any("malformed" in r.message for r in caplog.records)

    def test_non_dict_lines_skipped(self, tmp_path):
        p = tmp_path / "test.jsonl"
        p.write_text('{"ok":1}\n[1,2,3]\n{"ok":2}\n')
        results = list(_iter_jsonl(p))
        assert len(results) == 2


# ---------------------------------------------------------------------------
# path functions に副作用がないこと
# ---------------------------------------------------------------------------


class TestPathFunctionsNoSideEffects:
    def test_month_events_path_no_mkdir(self, tmp_path):
        p = month_events_path(tmp_path, dt(2026, 1, 10))
        assert not p.parent.exists()

    def test_month_payroll_path_no_mkdir(self, tmp_path):
        p = month_payroll_path(tmp_path, "2026-01")
        assert not p.parent.exists()

    def test_month_events_path_correct_location(self, tmp_path):
        p = month_events_path(tmp_path, dt(2026, 1, 10))
        assert p == tmp_path / "state" / "attendance" / "events" / "2026-01.jsonl"

    def test_month_payroll_path_correct_location(self, tmp_path):
        p = month_payroll_path(tmp_path, "2026-03")
        assert p == tmp_path / "state" / "attendance" / "payroll" / "2026-03.jsonl"


# ---------------------------------------------------------------------------
# append_event / iter_events_month の統合
# ---------------------------------------------------------------------------


class TestAppendEventRoundtrip:
    def test_append_and_iter_events(self, tmp_path):
        event_dt = dt(2026, 1, 10)
        ev = {
            "id": "abc123",
            "ts": event_dt,
            "uid": "AABBCCDD",
            "emp": "emp01",
            "act": "IN",
        }
        p = month_events_path(tmp_path, event_dt)
        append_event(p, ev)

        events = list(iter_events_month(tmp_path, "2026-01"))
        assert len(events) == 1
        assert events[0]["emp"] == "emp01"
        assert events[0]["act"] == "IN"
        # ts は ISO 文字列に変換されて保存される
        assert isinstance(events[0]["ts"], str)
        assert "2026-01-10" in events[0]["ts"]

    def test_datetime_ts_serialized_to_iso(self, tmp_path):
        event_dt = datetime(2026, 1, 10, 9, 0, tzinfo=JST)
        ev = {"id": "x", "ts": event_dt, "uid": "U", "emp": "e", "act": "IN"}
        p = month_events_path(tmp_path, event_dt)
        append_event(p, ev)

        events = list(iter_events_month(tmp_path, "2026-01"))
        assert events[0]["ts"] == "2026-01-10T09:00:00+09:00"

    def test_iter_nonexistent_month_returns_empty(self, tmp_path):
        events = list(iter_events_month(tmp_path, "2099-12"))
        assert events == []
