from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from lib.payroll_calc import build_daily_payroll_records
from lib.time_jst import iso_jst

JST = ZoneInfo("Asia/Tokyo")


def ts(y, mo, d, h, m) -> datetime:
    return datetime(y, mo, d, h, m, tzinfo=JST)


def ev(dt: datetime, emp: str, act: str, code: str = "") -> dict:
    e = {"ts": iso_jst(dt), "emp": emp, "act": act}
    if code:
        e["code"] = code
    return e


@pytest.fixture
def repo(tmp_path):
    emp_dir = tmp_path / "config" / "employees"
    emp_dir.mkdir(parents=True)
    (emp_dir / "emp01.env").write_text(
        "NAME=Test\nHOURLY_YEN=1200\nROUND_UNIT_MINUTES=5\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# 正常系
# ---------------------------------------------------------------------------


class TestNormalFlow:
    def test_in_out_60min(self, repo):
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 10, 10, 0), "emp01", "OUT"),
        ]
        recs, summary = build_daily_payroll_records(repo, events)
        assert len(recs) == 1
        r = recs[0]
        assert r["min_raw"] == 60
        assert r["min"] == 60
        assert r["yen"] == 1200
        assert r["flags"] == []

    def test_in_out_90min(self, repo):
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 10, 10, 30), "emp01", "OUT"),
        ]
        recs, _ = build_daily_payroll_records(repo, events)
        r = recs[0]
        assert r["min_raw"] == 90
        assert r["yen"] == 1800

    def test_rounding_truncates_down(self, repo):
        # 67 分 → ROUND_UNIT=5 → 65 分
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 10, 10, 7), "emp01", "OUT"),
        ]
        recs, _ = build_daily_payroll_records(repo, events)
        assert recs[0]["min_raw"] == 67
        assert recs[0]["min"] == 65

    def test_multiple_days(self, repo):
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 10, 10, 0), "emp01", "OUT"),
            ev(ts(2026, 1, 11, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 11, 11, 0), "emp01", "OUT"),
        ]
        recs, summary = build_daily_payroll_records(repo, events)
        assert len(recs) == 2
        assert summary["days_emps"] == 2

    def test_summary_counts(self, repo):
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 10, 10, 0), "emp01", "OUT"),
            {"ts": "", "emp": "unknown", "act": "IN"},
        ]
        _, summary = build_daily_payroll_records(repo, events)
        assert summary["events"] == 3
        assert summary["events_unknown_emp"] == 1


# ---------------------------------------------------------------------------
# 丸め・時給設定
# ---------------------------------------------------------------------------


class TestRoundingAndHourly:
    def test_zero_min_no_record(self, repo):
        # イベントなし → レコードなし
        recs, _ = build_daily_payroll_records(repo, [])
        assert recs == []

    def test_missing_hourly_yen_flag(self, tmp_path):
        # emp99 の env ファイルが存在しない
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp99", "IN"),
            ev(ts(2026, 1, 10, 10, 0), "emp99", "OUT"),
        ]
        recs, _ = build_daily_payroll_records(tmp_path, events)
        assert "missing_hourly_yen" in recs[0]["flags"]
        assert recs[0]["yen"] == 0

    def test_round_unit_zero_defaults_to_5(self, tmp_path):
        emp_dir = tmp_path / "config" / "employees"
        emp_dir.mkdir(parents=True)
        (emp_dir / "emp02.env").write_text(
            "NAME=Test2\nHOURLY_YEN=1200\nROUND_UNIT_MINUTES=0\n"
        )
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp02", "IN"),
            ev(ts(2026, 1, 10, 9, 7), "emp02", "OUT"),
        ]
        recs, _ = build_daily_payroll_records(tmp_path, events)
        # ROUND_UNIT=0 → 5 に補正 → 7 分 → 5 分
        assert recs[0]["min"] == 5


# ---------------------------------------------------------------------------
# 異常検知フラグ
# ---------------------------------------------------------------------------


class TestAnomalyFlags:
    def test_orphan_out(self, repo):
        events = [ev(ts(2026, 1, 10, 10, 0), "emp01", "OUT")]
        recs, _ = build_daily_payroll_records(repo, events)
        assert len(recs) == 1
        assert "orphan_out" in recs[0]["flags"]
        assert recs[0]["yen"] == 0

    def test_missing_out_from_end_of_events(self, repo):
        # IN のみで OUT がないまま終わった場合
        events = [ev(ts(2026, 1, 10, 9, 0), "emp01", "IN")]
        recs, _ = build_daily_payroll_records(repo, events)
        assert "missing_out" in recs[0]["flags"]

    def test_missing_out_from_error_event(self, repo):
        # ERROR が来たら open_in がクリアされ missing_out が記録される
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 11, 1, 0), "emp01", "ERROR", "day_rollover"),
        ]
        recs, _ = build_daily_payroll_records(repo, events)
        jan10 = next(r for r in recs if r["date"] == "2026-01-10")
        assert "missing_out" in jan10["flags"]

    def test_error_flag_recorded(self, repo):
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 10, 10, 0), "emp01", "ERROR", "timeout_15h"),
        ]
        recs, _ = build_daily_payroll_records(repo, events)
        jan10 = next(r for r in recs if r["date"] == "2026-01-10")
        assert "error:timeout_15h" in jan10["flags"]

    def test_double_in_sets_double_in_flag_on_second_day(self, repo):
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 11, 9, 0), "emp01", "IN"),  # double_in
        ]
        recs, _ = build_daily_payroll_records(repo, events)
        jan11 = next(r for r in recs if r["date"] == "2026-01-11")
        assert "double_in" in jan11["flags"]

    def test_double_in_sets_missing_out_on_first_day(self, repo):
        # バグ修正の検証: double_in 時に前日の d0 キーに missing_out が立つこと
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 11, 9, 0), "emp01", "IN"),  # double_in
        ]
        recs, _ = build_daily_payroll_records(repo, events)
        jan10 = next(r for r in recs if r["date"] == "2026-01-10")
        assert "missing_out" in jan10["flags"]

    def test_double_in_same_day(self, repo):
        # 同日に IN が二回来た場合
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 10, 10, 0), "emp01", "IN"),
        ]
        recs, _ = build_daily_payroll_records(repo, events)
        jan10 = next(r for r in recs if r["date"] == "2026-01-10")
        assert "double_in" in jan10["flags"]
        assert "missing_out" in jan10["flags"]

    def test_cross_day_flag(self, repo):
        # IN が前日、OUT が翌日
        events = [
            ev(ts(2026, 1, 10, 23, 0), "emp01", "IN"),
            ev(ts(2026, 1, 11, 1, 0), "emp01", "OUT"),
        ]
        recs, _ = build_daily_payroll_records(repo, events)
        jan10 = next(r for r in recs if r["date"] == "2026-01-10")
        assert "cross_day" in jan10["flags"]
        # 勤務時間は IN 側の日付 (jan10) に加算
        assert jan10["min_raw"] == 120


# ---------------------------------------------------------------------------
# unknown emp の除外
# ---------------------------------------------------------------------------


class TestUnknownEmp:
    def test_unknown_emp_excluded_from_records(self, repo):
        events = [
            ev(ts(2026, 1, 10, 9, 0), "unknown", "IN"),
            ev(ts(2026, 1, 10, 10, 0), "unknown", "OUT"),
        ]
        recs, summary = build_daily_payroll_records(repo, events)
        assert recs == []
        assert summary["events_unknown_emp"] == 2


# ---------------------------------------------------------------------------
# record_id の一意性
# ---------------------------------------------------------------------------


class TestRecordId:
    def test_same_date_emp_gives_same_id(self, repo):
        events = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 10, 10, 0), "emp01", "OUT"),
        ]
        recs1, _ = build_daily_payroll_records(repo, events)
        recs2, _ = build_daily_payroll_records(repo, events)
        assert recs1[0]["id"] == recs2[0]["id"]

    def test_different_date_gives_different_id(self, repo):
        events1 = [
            ev(ts(2026, 1, 10, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 10, 10, 0), "emp01", "OUT"),
        ]
        events2 = [
            ev(ts(2026, 1, 11, 9, 0), "emp01", "IN"),
            ev(ts(2026, 1, 11, 10, 0), "emp01", "OUT"),
        ]
        recs1, _ = build_daily_payroll_records(repo, events1)
        recs2, _ = build_daily_payroll_records(repo, events2)
        assert recs1[0]["id"] != recs2[0]["id"]
