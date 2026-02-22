import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from lib.attendance_store import iter_events_month, month_key
from lib.time_jst import date_jst, now_jst, parse_iso


_DEBOUNCE = timedelta(minutes=5)
_TIMEOUT = timedelta(hours=15)


@dataclass
class CardState:
    inside: bool
    last_ts: object
    emp: str


@dataclass
class State:
    uid_state: dict
    uid_last_seen: dict
    uid_done_day: dict

    @staticmethod
    def empty():
        return State(uid_state={}, uid_last_seen={}, uid_done_day={})

    @staticmethod
    def from_current_month(repo_root: Path):
        st = State.empty()
        ym = month_key(now_jst())
        for ev in iter_events_month(repo_root, ym):
            _apply_event_for_restore(st, ev)
        return st


def apply_rules(st: State, ts, uid: str, emp: str) -> list[dict]:
    if uid in st.uid_last_seen:
        if ts - st.uid_last_seen[uid] < _DEBOUNCE:
            return []
    st.uid_last_seen[uid] = ts

    today = date_jst(ts)
    if uid in st.uid_done_day and st.uid_done_day[uid] != today:
        st.uid_done_day.pop(uid, None)
    if uid in st.uid_done_day and st.uid_done_day[uid] == today:
        return []

    if uid not in st.uid_state:
        st.uid_state[uid] = CardState(inside=False, last_ts=ts, emp=emp)
    cs = st.uid_state[uid]

    if emp != "unknown":
        cs.emp = emp

    events = []
    events.extend(_errors_for_uid(st, ts, uid))
    cs = st.uid_state[uid]

    act = "IN" if not cs.inside else "OUT"
    emp_out = cs.emp if emp == "unknown" else emp
    events.append(_event(ts, uid, emp_out, act, None))

    st.uid_state[uid] = CardState(inside=(act == "IN"), last_ts=ts, emp=emp_out)
    if act == "OUT":
        st.uid_done_day[uid] = today

    return events


def sweep_errors(st: State, ts) -> list[dict]:
    events = []
    for uid, cs in list(st.uid_state.items()):
        if not cs.inside:
            continue
        if date_jst(cs.last_ts) != date_jst(ts):
            events.append(_event(ts, uid, cs.emp, "ERROR", "day_rollover"))
            st.uid_state[uid] = CardState(inside=False, last_ts=ts, emp=cs.emp)
            continue
        if ts - cs.last_ts > _TIMEOUT:
            events.append(_event(ts, uid, cs.emp, "ERROR", "timeout_15h"))
            st.uid_state[uid] = CardState(inside=False, last_ts=ts, emp=cs.emp)
    return events


def _errors_for_uid(st: State, ts, uid: str) -> list[dict]:
    cs = st.uid_state[uid]
    if not cs.inside:
        return []
    if date_jst(cs.last_ts) != date_jst(ts):
        st.uid_state[uid] = CardState(inside=False, last_ts=ts, emp=cs.emp)
        return [_event(ts, uid, cs.emp, "ERROR", "day_rollover")]
    if ts - cs.last_ts > _TIMEOUT:
        st.uid_state[uid] = CardState(inside=False, last_ts=ts, emp=cs.emp)
        return [_event(ts, uid, cs.emp, "ERROR", "timeout_15h")]
    return []


def _event(ts, uid: str, emp: str, act: str, code) -> dict:
    o = {"id": uuid.uuid4().hex, "ts": ts, "uid": uid, "emp": emp, "act": act}
    if act == "ERROR" and code:
        o["code"] = code
    return o


def _apply_event_for_restore(st: State, ev: dict) -> None:
    try:
        ts = parse_iso(str(ev.get("ts", "")))
    except Exception:
        return
    uid = str(ev.get("uid", ""))
    if not uid:
        return
    emp = str(ev.get("emp", "unknown"))
    act = str(ev.get("act", ""))

    st.uid_last_seen[uid] = ts

    if uid not in st.uid_state:
        st.uid_state[uid] = CardState(inside=False, last_ts=ts, emp=emp)

    cs = st.uid_state[uid]
    if cs.emp == "unknown" and emp != "unknown":
        cs.emp = emp

    d = date_jst(ts)

    if act == "IN":
        st.uid_state[uid] = CardState(inside=True, last_ts=ts, emp=cs.emp)
        if uid in st.uid_done_day and st.uid_done_day[uid] == d:
            st.uid_done_day.pop(uid, None)
    elif act == "OUT":
        st.uid_state[uid] = CardState(inside=False, last_ts=ts, emp=cs.emp)
        st.uid_done_day[uid] = d
    elif act == "ERROR":
        st.uid_state[uid] = CardState(inside=False, last_ts=ts, emp=cs.emp)
        if uid in st.uid_done_day and st.uid_done_day[uid] == d:
            st.uid_done_day.pop(uid, None)
