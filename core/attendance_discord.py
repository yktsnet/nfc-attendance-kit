import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import timezone, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from lib.env_loader import load_employee_env
from lib.attendance_store import iter_events_month, month_key
from lib.time_jst import now_jst, parse_iso


JST = timezone(timedelta(hours=9))


def _env_str(key: str) -> str:
    return str(os.environ.get(key, "")).strip()


def _http_post_json(url: str, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "nfc-attendance/1.0")
    with urllib.request.urlopen(req, timeout=10) as resp:
        _ = resp.read()


def _post_discord_retry(webhook_url: str, text: str) -> None:
    last_err = None
    for i in range(3):
        try:
            _http_post_json(webhook_url, {"content": text})
            return
        except urllib.error.HTTPError as e:
            try:
                b = e.read().decode("utf-8", "replace")
            except Exception:
                b = ""
            last_err = RuntimeError(f"HTTP {e.code} {e.reason} {b}".strip())
            if i < 2:
                time.sleep(1.0)
        except Exception as e:
            last_err = e
            if i < 2:
                time.sleep(1.0)
    raise last_err if last_err else RuntimeError("discord_post_failed")


def _fmt_jst_dt(ts) -> str:
    if getattr(ts, "tzinfo", None) is None:
        ts = ts.replace(tzinfo=JST)
    return ts.astimezone(JST).strftime("%Y-%m-%d %H:%M")


def _fmt_dur(ts0, ts1) -> str:
    sec = int((ts1 - ts0).total_seconds())
    if sec < 0:
        return ""
    m = sec // 60
    h = m // 60
    mm = m % 60
    return f"{h}h{mm:02d}m"


def _events_path(repo_root: Path, ym: str) -> Path:
    return repo_root / "state" / "attendance" / "events" / f"{ym}.jsonl"


def _restore_open_in(repo_root: Path, ym: str) -> dict:
    open_in = {}
    for ev in iter_events_month(repo_root, ym):
        if not isinstance(ev, dict):
            continue
        emp = str(ev.get("emp", "unknown"))
        act = str(ev.get("act", ""))
        ts_s = ev.get("ts")
        if not isinstance(ts_s, str) or not ts_s:
            continue
        try:
            ts = parse_iso(ts_s)
        except Exception:
            continue
        if act == "IN":
            open_in[emp] = ts
        elif act in ("OUT", "ERROR"):
            open_in.pop(emp, None)
    return open_in


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    webhook_url = _env_str("ATT_DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("ATT_DISCORD_WEBHOOK_URL_EMPTY")

    name_cache = {}
    cur_ym = month_key(now_jst())
    open_in = _restore_open_in(repo_root, cur_ym)

    p = _events_path(repo_root, cur_ym)

    def get_name(emp: str) -> str:
        if emp in name_cache:
            return name_cache[emp]
        d = load_employee_env(repo_root, emp)
        n = str(d.get("NAME", "")).strip()
        out = n if n else emp
        name_cache[emp] = out
        return out

    def open_tail(path: Path):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        fh = open(path, "r", encoding="utf-8")
        fh.seek(0, 2)
        return fh

    f = open_tail(p)

    while True:
        now_ym = month_key(now_jst())
        if now_ym != cur_ym:
            try:
                f.close()
            except Exception:
                pass
            cur_ym = now_ym
            name_cache = {}
            open_in = _restore_open_in(repo_root, cur_ym)
            p = _events_path(repo_root, cur_ym)
            f = open_tail(p)

        line = f.readline()
        if not line:
            time.sleep(0.2)
            continue

        s = line.strip()
        if not s:
            continue

        try:
            ev = json.loads(s)
        except Exception:
            continue
        if not isinstance(ev, dict):
            continue

        emp = str(ev.get("emp", "unknown"))
        act = str(ev.get("act", ""))
        ts_s = ev.get("ts")
        if not isinstance(ts_s, str) or not ts_s:
            continue

        try:
            ts = parse_iso(ts_s)
        except Exception:
            continue

        dt = _fmt_jst_dt(ts)
        disp = get_name(emp)

        if act == "IN":
            open_in[emp] = ts
            msg = f"{dt}  {disp}  IN"
        elif act == "OUT":
            if emp in open_in:
                t0 = open_in.pop(emp)
                dur = _fmt_dur(t0, ts)
                msg = f"{dt}  {disp}  OUT  ({dur})" if dur else f"{dt}  {disp}  OUT"
            else:
                msg = f"{dt}  {disp}  OUT"
        elif act == "ERROR":
            code = ev.get("code")
            code_s = str(code).strip() if code is not None else ""
            open_in.pop(emp, None)
            msg = f"{dt}  {disp}  ERROR  {code_s}" if code_s else f"{dt}  {disp}  ERROR"
        else:
            continue

        try:
            _post_discord_retry(webhook_url, msg)
        except Exception as e:
            print(str(e), file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
