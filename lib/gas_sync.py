import json
import time
import urllib.request
import urllib.error


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request_json(url: str, method: str, body_bytes: bytes | None, headers: dict, timeout_sec: int) -> tuple[dict, str]:
    opener = urllib.request.build_opener(_NoRedirect())
    cur_url = url
    cur_method = method
    cur_body = body_bytes
    last_text = ""

    for _ in range(10):
        req = urllib.request.Request(cur_url, data=(cur_body if cur_method != "GET" else None), method=cur_method)
        for k, v in headers.items():
            req.add_header(k, v)

        try:
            with opener.open(req, timeout=timeout_sec) as resp:
                text = (resp.read() or b"").decode("utf-8", "replace").strip()
                last_text = text
                try:
                    obj = json.loads(text) if text else {}
                except Exception:
                    obj = {}
                return obj, resp.geturl()
        except urllib.error.HTTPError as e:
            code = int(getattr(e, "code", 0) or 0)
            loc = ""
            try:
                loc = str(e.headers.get("Location", "") or "")
            except Exception:
                loc = ""
            text = ""
            try:
                text = (e.read() or b"").decode("utf-8", "replace").strip()
            except Exception:
                text = ""
            last_text = text

            if code in (301, 302, 303, 307, 308) and loc:
                cur_url = loc
                if code in (301, 302, 303):
                    cur_method = "GET"
                    cur_body = None
                continue

            raise RuntimeError(f"http_error code={code} url={cur_url} body={text[:400]}")

    raise RuntimeError(f"too_many_redirects url={url} last_body={last_text[:400]}")


def post_records(url: str, records: list[dict], token: str | None, timeout_sec: int) -> dict:
    payload = {"records": records}
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Auth-Token"] = token

    obj, _final_url = _request_json(url, "POST", body, headers, timeout_sec)
    if isinstance(obj, dict) and obj.get("ok") is True:
        return obj
    raise RuntimeError(f"bad_response body={json.dumps(obj, ensure_ascii=False, separators=(',', ':'))}")


def sync_payroll_month(repo_root, ym: str, gas_url: str, token: str | None, timeout_sec: int, retries: int, sleep_sec: float) -> dict:
    from lib.attendance_store import iter_payroll_month

    records = []
    for rec in iter_payroll_month(repo_root, ym):
        if isinstance(rec, dict):
            records.append(rec)

    last_err = None
    n = retries if retries > 0 else 1
    for i in range(n):
        try:
            ack = post_records(gas_url, records, token, timeout_sec)
            ack_out = dict(ack)
            ack_out["sent_records"] = len(records)
            return ack_out
        except Exception as e:
            last_err = e
            if i + 1 < n:
                time.sleep(sleep_sec)

    raise last_err if last_err else RuntimeError("sync_failed")
