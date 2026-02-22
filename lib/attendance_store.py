import json
from pathlib import Path

from lib.time_jst import iso_jst


def month_key(dt) -> str:
    return dt.strftime("%Y-%m")


def month_events_path(repo_root: Path, dt) -> Path:
    p = repo_root / "state" / "attendance" / "events" / f"{month_key(dt)}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def month_payroll_path(repo_root: Path, ym: str) -> Path:
    p = repo_root / "state" / "attendance" / "payroll" / f"{ym}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append_event(path: Path, ev: dict) -> None:
    append_jsonl(path, _jsonify(ev))


def append_jsonl(path: Path, obj: dict) -> None:
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def iter_events_month(repo_root: Path, ym: str):
    p = repo_root / "state" / "attendance" / "events" / f"{ym}.jsonl"
    yield from _iter_jsonl(p)


def iter_payroll_month(repo_root: Path, ym: str):
    p = repo_root / "state" / "attendance" / "payroll" / f"{ym}.jsonl"
    yield from _iter_jsonl(p)


def _iter_jsonl(path: Path):
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                o = json.loads(s)
            except Exception:
                continue
            if isinstance(o, dict):
                yield o


def _jsonify(ev: dict) -> dict:
    o = dict(ev)
    if "ts" in o and hasattr(o["ts"], "isoformat"):
        o["ts"] = iso_jst(o["ts"])
    return o
