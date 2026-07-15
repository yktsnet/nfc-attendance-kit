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
