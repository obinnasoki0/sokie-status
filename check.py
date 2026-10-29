"""Sokie external uptime check (runs on GitHub Actions every 5 minutes).

Checks the customer/runner app, the admin portal, Supabase Auth and the
backend's own health endpoint (database, scheduled jobs, security monitor).
Each check gets one retry after 20 seconds so a single blip doesn't page
anyone. Writes a Markdown report and exits 1 if anything is still down.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

SUPABASE = "https://yuingomretjukpbqocfa.supabase.co"
PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")


def fetch(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "sokie-status-monitor", **(headers or {})})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200_000).decode("utf-8", "replace"), time.time() - started
    except urllib.error.HTTPError as e:
        return e.code, e.read(20_000).decode("utf-8", "replace"), time.time() - started
    except Exception as e:  # DNS, TLS, timeout
        return 0, str(e), time.time() - started


def app(url, marker):
    def check():
        status, body, secs = fetch(url)
        ok = status == 200 and marker in body
        return ok, f"HTTP {status} in {secs:.1f}s" + ("" if ok or status != 200 else f" (page didn't contain '{marker}')")
    return check


def backend_health():
    status, body, secs = fetch(f"{SUPABASE}/functions/v1/health")
    try:
        data = json.loads(body)
    except Exception:
        data = {}
    ok = status == 200 and data.get("ok") is True
    detail = ", ".join(f"{k}: {v}" for k, v in data.items() if k not in ("ok", "checked_in_ms")) or body[:200]
    return ok, f"HTTP {status} in {secs:.1f}s ({detail})"


def auth_health():
    if not PUBLISHABLE_KEY:
        return True, "skipped (no SUPABASE_PUBLISHABLE_KEY secret)"
    status, body, secs = fetch(f"{SUPABASE}/auth/v1/health", {"apikey": PUBLISHABLE_KEY})
    return status == 200, f"HTTP {status} in {secs:.1f}s"


def simulated():
    return False, "simulated outage (test run)"


CHECKS = [
    ("Customer & runner app (mysokie.com)", app("https://mysokie.com/", "flutter")),
    ("Admin portal", app("https://obinnasoki0.github.io/sokie-admin/", "flutter")),
    ("Backend: database, scheduled jobs, security monitor", backend_health),
    ("Sign-in service (Supabase Auth)", auth_health),
]


def main():
    if os.environ.get("SIMULATE_OUTAGE") == "true":
        CHECKS.append(("Simulated outage (test)", simulated))
    results = []
    for name, check in CHECKS:
        ok, detail = check()
        if not ok:
            time.sleep(20)
            ok, detail = check()
        results.append((name, ok, detail))

    down = [r for r in results if not r[1]]
    lines = [f"| {'✅' if ok else '❌'} | {name} | {detail} |" for name, ok, detail in results]
    report = "| | Check | Result |\n|---|---|---|\n" + "\n".join(lines)
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(report)
    if down:
        with open("down.txt", "w", encoding="utf-8") as f:
            f.write(", ".join(r[0] for r in down))
        sys.exit(1)


if __name__ == "__main__":
    main()
