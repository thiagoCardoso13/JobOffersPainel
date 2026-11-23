"""Adzuna API client (https://developer.adzuna.com/docs/search).

Terms require attribution: the dashboard shows "Jobs by Adzuna".
Free/pending plan: 25 test calls in total; paid plans: 5,000/month, 500/day.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Iterator

import requests

BASE_URL = "https://api.adzuna.com/v1/api/jobs"


def _load_dotenv() -> None:
    env = Path(__file__).resolve().parents[2] / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


CALLS_FILE = Path(__file__).resolve().parents[2] / "data" / "api_calls.json"
CALL_LIMIT = 25   # test-plan quota (total, not monthly)
RESERVE = 2       # never spend the last calls


def _spend_call() -> None:
    """Persistent counter: aborts before the free quota is exhausted."""
    import json

    CALLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    used = json.loads(CALLS_FILE.read_text())["used"] if CALLS_FILE.exists() else 3  # 3 calls were already spent on manual tests
    if used >= CALL_LIMIT - RESERVE:
        raise SystemExit(f"Quota guard: {used}/{CALL_LIMIT} calls used. Aborting.")
    CALLS_FILE.write_text(json.dumps({"used": used + 1}))


def _creds() -> dict:
    try:
        return {"app_id": os.environ["ADZUNA_APP_ID"], "app_key": os.environ["ADZUNA_APP_KEY"]}
    except KeyError as e:
        raise SystemExit(f"Missing environment variable {e}. See the README.") from e


def search(what: str, where: str | None = None, country: str = "es", max_pages: int = 1,
           per_page: int = 50, pause: float = 1.0) -> Iterator[dict]:
    """Walk /jobs/{country}/search/{page} and yield each offer."""
    for page in range(1, max_pages + 1):
        params = {**_creds(), "what": what, "results_per_page": per_page}
        if where:
            params["where"] = where
        _spend_call()
        r = requests.get(f"{BASE_URL}/{country}/search/{page}", params=params, timeout=30)
        r.raise_for_status()
        items = r.json().get("results", [])
        yield from items
        if len(items) < per_page:
            break
        time.sleep(pause)
