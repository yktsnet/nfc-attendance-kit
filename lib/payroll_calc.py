import hashlib
from collections import defaultdict
from pathlib import Path

from lib.env_loader import load_employee_env, env_int
from lib.time_jst import parse_iso, date_jst


def build_daily_payroll_records(repo_root: Path, events: list[dict]) -> tuple[list[dict], dict]:
    parsed = []
    unknown_emp = 0

    for ev in events:
        if not isinstance(ev, dict):
            continue
        emp = str(ev.get("emp", "unknown"))
        if emp == "unknown":
            unknown_emp += 1
            continue
        ts_s = ev.get("ts")
        if not isinstance(ts_s, str) or not ts_s:
            continue
        try:
            ts = parse_iso(ts_s)
        except Exception:
            continue
        act = str(ev.get("act", ""))
        code = ev.get("code")
        code = str(code) if code is not None else ""
        parsed.append((ts, emp, act, code))

    parsed.sort(key=lambda x: x[0])

    open_in = {}
    mins = defaultdict(int)
    flags = defaultdict(set)

    for ts, emp, act, code in parsed:
        d = str(date_jst(ts))
        key = (emp, d)

        if act == "IN":
            if emp in open_in:
                flags[key].add("double_in")
            open_in[emp] = ts
            continue

        if act == "OUT":
            if emp not in open_in:
                flags[key].add("orphan_out")
                continue
            t0 = open_in.pop(emp)
            d0 = str(date_jst(t0))
            key0 = (emp, d0)
            dur = int((ts - t0).total_seconds() // 60)
            if dur < 0:
                flags[key0].add("negative_duration")
                continue
            mins[key0] += dur
            if d0 != d:
                flags[key0].add("cross_day")
            continue

        if act == "ERROR":
            c = code if code else "error"
            flags[key].add(f"error:{c}")
            if emp in open_in:
                d0 = str(date_jst(open_in[emp]))
                flags[(emp, d0)].add("missing_out")
                open_in.pop(emp, None)
            continue

    for emp, t0 in list(open_in.items()):
        d0 = str(date_jst(t0))
        flags[(emp, d0)].add("missing_out")

    keys = set(mins.keys()) | set(flags.keys())
    keys = sorted(keys, key=lambda x: (x[1], x[0]))

    recs = []
    flags_days = 0

    for emp, d in keys:
        raw_min = int(mins.get((emp, d), 0))
        fset = set(flags.get((emp, d), set()))
        if not raw_min and not fset:
            continue

        e = load_employee_env(repo_root, emp)
        hourly = env_int(e, "HOURLY_YEN", 0)
        unit = env_int(e, "ROUND_UNIT_MINUTES", 5)
        if unit <= 0:
            unit = 5
        if hourly <= 0:
            fset.add("missing_hourly_yen")

        rounded = (raw_min // unit) * unit
        yen = (rounded * hourly) // 60

        rid = _rid(d, emp)
        if fset:
            flags_days += 1

        recs.append(
            {
                "id": rid,
                "date": d,
                "emp": emp,
                "min_raw": raw_min,
                "min": rounded,
                "yen_h": hourly,
                "yen": int(yen),
                "flags": sorted(list(fset)),
            }
        )

    summary = {
        "events": len(events),
        "events_unknown_emp": unknown_emp,
        "days_emps": len(keys),
        "flags_days": flags_days,
    }
    return recs, summary


def _rid(date_s: str, emp: str) -> str:
    s = f"{date_s}|{emp}".encode("utf-8")
    return hashlib.sha1(s).hexdigest()
