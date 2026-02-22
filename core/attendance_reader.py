import json
import sys
import threading
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from lib.rcs300_pcsc import read_uid_blocking
from lib.attendance_rules import State, apply_rules, sweep_errors
from lib.attendance_store import append_event, month_events_path
from lib.time_jst import now_jst, iso_jst


def load_uid_map(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            o = json.load(f)
        return o if isinstance(o, dict) else {}
    except Exception:
        return {}


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    uid_map_path = repo_root / "config" / "attendance" / "uid_map.json"
    uid_map = load_uid_map(uid_map_path)

    st = State.from_current_month(repo_root)
    lock = threading.Lock()
    stop = threading.Event()

    def emit(ev: dict) -> None:
        p = month_events_path(repo_root, ev["ts"])
        append_event(p, ev)
        ev_out = dict(ev)
        ev_out["ts"] = iso_jst(ev_out["ts"])
        print(json.dumps(ev_out, ensure_ascii=False, separators=(",", ":")), flush=True)

    def sweeper() -> None:
        while not stop.is_set():
            time.sleep(1.0)
            ts = now_jst()
            try:
                with lock:
                    for ev in sweep_errors(st, ts):
                        emit(ev)
            except Exception as e:
                print(str(e), file=sys.stderr, flush=True)

    th = threading.Thread(target=sweeper, daemon=True)
    th.start()

    try:
        while True:
            uid = read_uid_blocking()
            ts = now_jst()
            emp = str(uid_map.get(uid, "unknown"))
            with lock:
                for ev in apply_rules(st, ts, uid, emp):
                    emit(ev)
    except KeyboardInterrupt:
        stop.set()
        return


if __name__ == "__main__":
    main()
