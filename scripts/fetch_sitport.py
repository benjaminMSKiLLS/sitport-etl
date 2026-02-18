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
    "User-Agent": "sitport-etl/1.0 (+github-actions)",
    # a veces ayuda si el WAF se pone pesado:
    "Origin": "https://orion.directemar.cl",
    "Referer": "https://orion.directemar.cl/",
}

TIMEOUT = (10, 60)  # connect, read


def fetch(ep: str, method: str, session: requests.Session, payload: dict | None = None, tries: int = 6):
    url = f"{BASE}/{ep}"
    payload = payload or {}

    for attempt in range(1, tries + 1):
        try:
            if method.upper() == "POST":
                r = session.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
            else:
                r = session.get(url, headers=HEADERS, timeout=TIMEOUT)

            ct = (r.headers.get("content-type") or "").lower()
            print(f"[{ep}] attempt {attempt}/{tries} -> {r.status_code} | {ct}")

            # reintentos “buenos”
            if r.status_code in (429, 502, 503, 504):
                sleep_s = 2 * attempt
                print(f"[{ep}] retryable status {r.status_code}. sleeping {sleep_s}s...")
                time.sleep(sleep_s)
                continue

            # si no es 200, muestra body y falla (sin reintentar eternamente)
            if r.status_code >= 400:
                print(f"[{ep}] ERROR body preview: {r.text[:400]}")
                r.raise_for_status()

            # si no es JSON, muéstralo (esto detecta HTML/login/WAF)
            if "json" not in ct:
                print(f"[{ep}] Non-JSON response preview: {r.text[:400]}")
                raise RuntimeError(f"Non-JSON content-type for {ep}: {ct}")

            return r.json()

        except RequestException as e:
            print(f"[{ep}] RequestException: {type(e).__name__}: {e}")
        except Exception as e:
            print(f"[{ep}] Exception: {type(e).__name__}: {e}")

        sleep_s = 2 * attempt
        time.sleep(sleep_s)

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
