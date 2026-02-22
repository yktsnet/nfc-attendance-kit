import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from lib.payroll_calc import build_daily_payroll_records
from lib.attendance_store import iter_events_month, month_key, month_payroll_path
from lib.time_jst import now_jst
from lib.env_loader import load_employee_env
from lib.gas_sync import post_records


def _env_int(key: str, default: int) -> int:
    v = str(os.environ.get(key, "")).strip()
    if not v:
        return default
    try:
        return int(v)
    except Exception:
        return default


def _env_float(key: str, default: float) -> float:
    v = str(os.environ.get(key, "")).strip()
    if not v:
        return default
    try:
        return float(v)
    except Exception:
        return default


def _prev_month_key(ym: str) -> str:
    s = str(ym).strip()
    if len(s) != 7 or s[4] != "-":
        return s
    try:
        y = int(s[0:4])
        m = int(s[5:7])
    except Exception:
        return s
    m -= 1
    if m <= 0:
        y -= 1
        m = 12
    return f"{y:04d}-{m:02d}"


def _emp_name(repo_root: Path, emp: str, cache: dict) -> str:
    if emp in cache:
        return cache[emp]
    try:
        env = load_employee_env(repo_root, emp)
        name = str(env.get("NAME", "")).strip()
    except Exception:
        name = ""
    cache[emp] = name
    return name


def _post_records_retry(gas_url: str, records: list[dict], token: str | None, timeout_sec: int, retries: int, sleep_sec: float) -> dict:
    last_err = None
    n = retries if retries > 0 else 1
    for i in range(n):
        try:
            ack = post_records(gas_url, records, token, timeout_sec)
            out = dict(ack) if isinstance(ack, dict) else {"ok": True}
            out["sent_records"] = len(records)
            return out
        except Exception as e:
            last_err = e
            if i + 1 < n:
                time.sleep(sleep_sec)
    raise last_err if last_err else RuntimeError("gas_post_failed")


def _write_jsonl_replace(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            for r in records:
                if not isinstance(r, dict):
                    continue
                line = json.dumps(r, ensure_ascii=False, separators=(",", ":"))
                f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        try:
            dfd = os.open(str(path.parent), os.O_DIRECTORY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except Exception:
            pass
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _build_month(repo_root: Path, ym: str, name_cache: dict) -> tuple[list[dict], dict, Path]:
    events = [ev for ev in iter_events_month(repo_root, ym) if isinstance(ev, dict)]
    records, summary = build_daily_payroll_records(repo_root, events)

    for r in records:
        if not isinstance(r, dict):
            continue
        emp = str(r.get("emp", "")).strip()
        if emp:
            r["name"] = _emp_name(repo_root, emp, name_cache)

    records = [r for r in records if isinstance(r, dict)]
    records.sort(key=lambda r: (str(r.get("date", "")), str(r.get("emp", ""))))

    out_path = month_payroll_path(repo_root, ym)
    _write_jsonl_replace(out_path, records)

    if not isinstance(summary, dict):
        summary = {}
    return records, summary, out_path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dt = now_jst()
    ym_this = month_key(dt)

    months = [ym_this]
    try:
        day = int(getattr(dt, "day", 0) or 0)
    except Exception:
        day = 0
    if 1 <= day <= 2:
        ym_prev = _prev_month_key(ym_this)
        if ym_prev and ym_prev != ym_this:
            months = [ym_prev, ym_this]

    gas_url = str(os.environ.get("ATT_GAS_URL", "")).strip()
    token = str(os.environ.get("ATT_GAS_TOKEN", "")).strip() or None
    timeout_sec = _env_int("ATT_GAS_TIMEOUT_SEC", 20)
    retries = _env_int("ATT_GAS_RETRIES", 3)
    sleep_sec = _env_float("ATT_GAS_RETRY_SLEEP_SEC", 2.0)

    name_cache = {}
    out_months = []
    for ym in months:
        records, summary, out_path = _build_month(repo_root, ym, name_cache)
        s = {
            "month": ym,
            "events": int(summary.get("events", 0)),
            "events_unknown_emp": int(summary.get("events_unknown_emp", 0)),
            "days_emps": int(summary.get("days_emps", 0)),
            "flags_days": int(summary.get("flags_days", 0)),
            "local_path": str(out_path),
            "local_records": len(records),
        }
        if gas_url:
            ack = _post_records_retry(gas_url, records, token, timeout_sec, retries, sleep_sec)
            s["gas"] = ack
        out_months.append(s)

    if len(out_months) == 1:
        print(json.dumps(out_months[0], ensure_ascii=False, separators=(",", ":")), flush=True)
        return

    print(json.dumps({"months": out_months}, ensure_ascii=False, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
