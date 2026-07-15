from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from lib.attendance_rules import State, apply_rules, sweep_errors

JST = ZoneInfo("Asia/Tokyo")

UID = "AABBCCDD"
UID2 = "11223344"
EMP = "emp01"
EMP2 = "emp02"


def ts(y, mo, d, h, m, s=0) -> datetime:
    return datetime(y, mo, d, h, m, s, tzinfo=JST)


# ---------------------------------------------------------------------------
# debounce
# ---------------------------------------------------------------------------


class TestDebounce:
    def test_tap_within_5min_ignored(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        result = apply_rules(st, ts(2026, 1, 10, 9, 4, 59), UID, EMP)
        assert result == []

    def test_tap_at_exactly_5min_processed(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        result = apply_rules(st, ts(2026, 1, 10, 9, 5), UID, EMP)
        assert len(result) == 1
        assert result[0]["act"] == "OUT"

    def test_tap_after_5min_processed(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        result = apply_rules(st, ts(2026, 1, 10, 9, 6), UID, EMP)
        assert len(result) == 1
        assert result[0]["act"] == "OUT"

    def test_debounce_is_per_uid(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        # 別 UID は制限を受けない
        result = apply_rules(st, ts(2026, 1, 10, 9, 1), UID2, EMP2)
        assert len(result) == 1
        assert result[0]["act"] == "IN"


# ---------------------------------------------------------------------------
# basic IN / OUT sequence
# ---------------------------------------------------------------------------


class TestBasicSequence:
    def test_first_tap_is_in(self):
        st = State.empty()
        result = apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        assert len(result) == 1
        assert result[0]["act"] == "IN"
        assert result[0]["emp"] == EMP

    def test_second_tap_is_out(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        result = apply_rules(st, ts(2026, 1, 10, 18, 0), UID, EMP)
        assert result[0]["act"] == "OUT"

    def test_out_then_same_day_tap_ignored(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        apply_rules(st, ts(2026, 1, 10, 18, 0), UID, EMP)
        result = apply_rules(st, ts(2026, 1, 10, 20, 0), UID, EMP)
        assert result == []

    def test_out_then_next_day_tap_is_in(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        apply_rules(st, ts(2026, 1, 10, 18, 0), UID, EMP)
        result = apply_rules(st, ts(2026, 1, 11, 9, 0), UID, EMP)
        assert len(result) == 1
        assert result[0]["act"] == "IN"


# ---------------------------------------------------------------------------
# unknown emp のタップ（uid_map に無いカード等）
# ---------------------------------------------------------------------------


class TestUnknownEmpTap:
    def test_unknown_emp_tap_uses_last_known_emp(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)  # IN by known emp
        result = apply_rules(st, ts(2026, 1, 10, 18, 0), UID, "unknown")  # OUT
        assert result[0]["act"] == "OUT"
        assert result[0]["emp"] == EMP

    def test_unknown_emp_tap_does_not_overwrite_stored_emp(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        apply_rules(st, ts(2026, 1, 10, 18, 0), UID, "unknown")  # OUT, emp unresolved
        result = apply_rules(st, ts(2026, 1, 11, 9, 0), UID, "unknown")  # next IN
        assert result[0]["act"] == "IN"
        assert result[0]["emp"] == EMP


# ---------------------------------------------------------------------------
# day_rollover error
# ---------------------------------------------------------------------------


class TestDayRollover:
    def test_in_yesterday_tap_today_emits_error_then_in(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 20, 0), UID, EMP)  # IN
        result = apply_rules(st, ts(2026, 1, 11, 9, 0), UID, EMP)

        acts = [e["act"] for e in result]
        assert "ERROR" in acts
        assert "IN" in acts

        err = next(e for e in result if e["act"] == "ERROR")
        assert err["code"] == "day_rollover"
        assert err["emp"] == EMP

    def test_day_rollover_order_error_before_in(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 20, 0), UID, EMP)
        result = apply_rules(st, ts(2026, 1, 11, 9, 0), UID, EMP)
        assert result[0]["act"] == "ERROR"
        assert result[1]["act"] == "IN"

    def test_sweep_errors_day_rollover(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 23, 0), UID, EMP)  # IN late night
        result = sweep_errors(st, ts(2026, 1, 11, 1, 0))

        assert len(result) == 1
        assert result[0]["act"] == "ERROR"
        assert result[0]["code"] == "day_rollover"

    def test_sweep_errors_after_rollover_uid_is_outside(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 23, 0), UID, EMP)
        sweep_errors(st, ts(2026, 1, 11, 1, 0))
        # 次のタッチで IN になるはず
        result = apply_rules(st, ts(2026, 1, 11, 9, 0), UID, EMP)
        assert result[0]["act"] == "IN"


# ---------------------------------------------------------------------------
# timeout_15h error
# ---------------------------------------------------------------------------


class TestTimeout:
    def test_in_then_16h_later_same_day_emits_timeout(self):
        st = State.empty()
        t0 = ts(2026, 1, 10, 0, 0)
        apply_rules(st, t0, UID, EMP)
        result = apply_rules(st, ts(2026, 1, 10, 16, 0), UID, EMP)

        acts = [e["act"] for e in result]
        assert "ERROR" in acts
        err = next(e for e in result if e["act"] == "ERROR")
        assert err["code"] == "timeout_15h"

    def test_in_then_14h_later_no_timeout(self):
        st = State.empty()
        t0 = ts(2026, 1, 10, 0, 0)
        apply_rules(st, t0, UID, EMP)
        result = apply_rules(st, ts(2026, 1, 10, 14, 0), UID, EMP)
        acts = [e["act"] for e in result]
        assert "ERROR" not in acts

    def test_sweep_errors_timeout(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 0, 0), UID, EMP)
        result = sweep_errors(st, ts(2026, 1, 10, 16, 0))

        assert len(result) == 1
        assert result[0]["code"] == "timeout_15h"


# ---------------------------------------------------------------------------
# sweep_errors: not inside → no error
# ---------------------------------------------------------------------------


class TestSweepNotInside:
    def test_not_inside_no_error(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        apply_rules(st, ts(2026, 1, 10, 18, 0), UID, EMP)
        result = sweep_errors(st, ts(2026, 1, 11, 1, 0))
        assert result == []

    def test_empty_state_no_error(self):
        st = State.empty()
        result = sweep_errors(st, ts(2026, 1, 11, 0, 0))
        assert result == []

    def test_multiple_uids_only_inside_flagged(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)  # IN
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID2, EMP2)  # IN
        apply_rules(st, ts(2026, 1, 10, 18, 0), UID, EMP)  # OUT → not inside

        result = sweep_errors(st, ts(2026, 1, 11, 1, 0))
        assert len(result) == 1
        assert result[0]["uid"] == UID2


# ---------------------------------------------------------------------------
# event fields
# ---------------------------------------------------------------------------


class TestEventFields:
    def test_event_has_required_fields(self):
        st = State.empty()
        result = apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        ev = result[0]
        assert "id" in ev
        assert "ts" in ev
        assert "uid" in ev
        assert "emp" in ev
        assert "act" in ev

    def test_error_event_has_code(self):
        st = State.empty()
        apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        result = apply_rules(st, ts(2026, 1, 11, 9, 0), UID, EMP)
        err = next(e for e in result if e["act"] == "ERROR")
        assert "code" in err

    def test_non_error_event_has_no_code(self):
        st = State.empty()
        result = apply_rules(st, ts(2026, 1, 10, 9, 0), UID, EMP)
        assert "code" not in result[0]


# ---------------------------------------------------------------------------
# State.from_current_month
# ---------------------------------------------------------------------------


class TestFromCurrentMonth:
    def _write_events(self, repo_root, events):
        from lib.attendance_store import append_event, month_events_path

        path = month_events_path(repo_root, ts(2026, 1, 15, 0, 0))
        for ev in events:
            append_event(path, ev)

    def _restore(self, monkeypatch, repo_root):
        import lib.attendance_rules as rules

        monkeypatch.setattr(rules, "now_jst", lambda: ts(2026, 1, 15, 12, 0))
        return State.from_current_month(repo_root)

    def test_restores_inside_state_and_emp(self, monkeypatch, tmp_path):
        self._write_events(tmp_path, [
            {"id": "1", "ts": ts(2026, 1, 15, 9, 0), "uid": UID, "emp": EMP, "act": "IN"},
        ])
        st = self._restore(monkeypatch, tmp_path)

        # 入場中として復元され、次のタップは OUT になる
        result = apply_rules(st, ts(2026, 1, 15, 10, 0), UID, "unknown")
        assert len(result) == 1
        assert result[0]["act"] == "OUT"
        assert result[0]["emp"] == EMP  # 従業員IDも復元されている

    def test_restores_done_day_after_out(self, monkeypatch, tmp_path):
        self._write_events(tmp_path, [
            {"id": "1", "ts": ts(2026, 1, 15, 9, 0), "uid": UID, "emp": EMP, "act": "IN"},
            {"id": "2", "ts": ts(2026, 1, 15, 11, 0), "uid": UID, "emp": EMP, "act": "OUT"},
        ])
        st = self._restore(monkeypatch, tmp_path)

        # OUT 済みとして復元され、同日中の再タップは無視される
        assert apply_rules(st, ts(2026, 1, 15, 11, 30), UID, EMP) == []

    def test_no_events_restores_empty_state(self, monkeypatch, tmp_path):
        st = self._restore(monkeypatch, tmp_path)

        # イベント無しは空の状態。初回タップは IN になる
        result = apply_rules(st, ts(2026, 1, 15, 9, 0), UID, EMP)
        assert len(result) == 1
        assert result[0]["act"] == "IN"

    def test_reads_only_current_month(self, monkeypatch, tmp_path):
        from lib.attendance_store import append_event, month_events_path

        # 先月のイベント（IN のまま）は現在月の復元対象にならない
        prev = month_events_path(tmp_path, ts(2025, 12, 20, 0, 0))
        append_event(prev, {"id": "1", "ts": ts(2025, 12, 20, 9, 0), "uid": UID, "emp": EMP, "act": "IN"})
        st = self._restore(monkeypatch, tmp_path)

        result = apply_rules(st, ts(2026, 1, 15, 9, 0), UID, EMP)
        assert len(result) == 1
        assert result[0]["act"] == "IN"
