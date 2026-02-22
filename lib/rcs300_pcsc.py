import subprocess
import re
import time


_HEX2 = re.compile(r"^[0-9A-Fa-f]{2}$")
_READER_LINE = re.compile(r"^\s*(\d+)\s*:\s*(.+?)\s*$")


def read_uid_blocking(reader_index: int = 0) -> str:
    ri = _pick_reader_index(reader_index)
    out = _run_wait_apdu(ri)
    uid = _parse_uid(out)
    if not uid:
        raise RuntimeError(out.strip() or "uid parse failed")
    _wait_removed(ri)
    return uid


def _list_readers() -> list[tuple[int, str]]:
    cmd = ["opensc-tool", "--list-readers"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = p.stdout or ""
    if p.returncode != 0:
        return []
    readers = []
    for line in out.splitlines():
        m = _READER_LINE.match(line)
        if not m:
            continue
        try:
            idx = int(m.group(1))
        except Exception:
            continue
        name = str(m.group(2)).strip()
        if name:
            readers.append((idx, name))
    readers.sort(key=lambda x: x[0])
    return readers


def _pick_reader_index(hint: int) -> int:
    readers = _list_readers()
    if not readers:
        return hint
    if len(readers) == 1:
        return readers[0][0]

    keys = [
        "rc-s300",
        "rcs300",
        "pasori",
        "felica",
        "sony",
        "acr122",
        "acs",
        "nfc",
        "contactless",
    ]
    for idx, name in readers:
        low = name.lower()
        for k in keys:
            if k in low:
                return idx

    for idx, _ in readers:
        if idx == hint:
            return hint
    return readers[0][0]


def _run_wait_apdu(reader_index: int) -> str:
    cmd = [
        "opensc-tool",
        "--reader",
        str(reader_index),
        "--wait",
        "--card-driver",
        "default",
        "--send-apdu",
        "FF:CA:00:00:00",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = p.stdout or ""
    if p.returncode != 0:
        raise RuntimeError(out.strip() or "opensc-tool failed")
    return out


def _run_apdu(reader_index: int) -> int:
    cmd = [
        "opensc-tool",
        "--reader",
        str(reader_index),
        "--card-driver",
        "default",
        "--send-apdu",
        "FF:CA:00:00:00",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode


def _wait_removed(reader_index: int) -> None:
    while True:
        rc = _run_apdu(reader_index)
        if rc != 0:
            return
        time.sleep(0.2)


def _parse_uid(out: str) -> str:
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if "Received" in line:
            for j in range(i + 1, min(i + 8, len(lines))):
                toks = lines[j].strip().split()
                hexs = []
                for t in toks:
                    if _HEX2.match(t):
                        hexs.append(t.upper())
                    else:
                        break
                if hexs:
                    return "".join(hexs)

    for line in lines:
        toks = line.strip().split()
        hexs = []
        for t in toks:
            if _HEX2.match(t):
                hexs.append(t.upper())
            else:
                break
        if hexs:
            return "".join(hexs)
    return ""
