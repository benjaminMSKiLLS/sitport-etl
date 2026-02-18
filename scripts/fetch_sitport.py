import json
import time
from datetime import datetime, timezone

import requests

BASE = "https://orion.directemar.cl/sitport/back/users"

ENDPOINTS = [
    ("consultaRestricciones", "POST"),
    ("consultaBahias", "POST"),
    ("consultaZonas", "POST"),
    ("consultareparzona", "POST"),
    ("consultaCapuertoRestriccion", "POST"),
    ("Totalpronostico", "GET"),
    ("Totalgeneral", "GET"),
]

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "sitport-gha/1.0",
}

TIMEOUT = (10, 60)  # connect, read


def fetch(ep: str, method: str, session: requests.Session):
    url = f"{BASE}/{ep}"
    for attempt in range(6):
        try:
            if method == "GET":
                r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
            else:
                r = session.post(url, json={}, headers=HEADERS, timeout=TIMEOUT)

            # reintentos por rate limit / temporales
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 + attempt * 2)
                continue

            r.raise_for_status()
            return r.json()

        except requests.RequestException:
            time.sleep(2 + attempt * 2)

    raise RuntimeError(f"Failed after retries: {method} {url}")


def main():
    out = {
        "refreshed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base": BASE,
        "data": {},
    }

    with requests.Session() as s:
        for ep, method in ENDPOINTS:
            print(f"Fetching {method} {ep} ...")
            out["data"][ep] = {
                "method": method,
                "payload": fetch(ep, method, s),
            }

    with open("data/sitport.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("OK -> data/sitport.json")


if __name__ == "__main__":
    main()
