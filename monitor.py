from typing import Dict, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import time

import database


def check_url(url: str) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        req = Request(url, headers={"User-Agent": "PingMonitorPro/1.0"})
        with urlopen(req, timeout=10) as response:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "status": "up" if response.status < 400 else "down",
                "response_time_ms": elapsed_ms,
                "details": f"HTTP {getattr(response, 'status', 'unknown')}",
            }
    except (HTTPError, URLError) as exc:
        return {
            "status": "down",
            "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
            "details": str(exc),
        }


def run_monitor_cycle() -> None:
    for site in database.get_websites():
        result = check_url(site["url"])
        database.record_check(site["id"], result["status"], result["response_time_ms"], result["details"])
