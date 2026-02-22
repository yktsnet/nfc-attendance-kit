from pathlib import Path


def load_env_file(path: Path) -> dict:
    d = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k:
                    d[k] = v
    except Exception:
        return {}
    return d


def env_int(d: dict, key: str, default: int) -> int:
    v = d.get(key)
    if v is None:
        return default
    try:
        return int(str(v).strip())
    except Exception:
        return default


def employee_env_path(repo_root: Path, emp: str) -> Path:
    return repo_root / "config" / "employees" / f"{emp}.env"


def load_employee_env(repo_root: Path, emp: str) -> dict:
    return load_env_file(employee_env_path(repo_root, emp))
