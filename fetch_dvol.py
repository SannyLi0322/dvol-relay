"""GitHub Actions job: pull Deribit DVOL daily closes (ETH, BTC) and write CSVs for the trading host.

Runs on GitHub-hosted runners (which can reach Deribit); the trading host (Aliyun, Deribit blocked)
reads the committed CSVs from raw.githubusercontent.com. Output format matches pool_cycle._read_dvol_csv:
    date,dvol
    2026-11-07,62.13
Full history is rewritten each run (idempotent) so a missed day never leaves a gap.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
CURRENCIES = ("ETH", "BTC")
DAYS = 1200
URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"


def fetch(currency: str) -> list[tuple[str, float]]:
    end = int(time.time() * 1000)
    start = end - DAYS * 86400_000
    q = urllib.parse.urlencode({"currency": currency, "start_timestamp": start, "end_timestamp": end, "resolution": "1D"})
    with urllib.request.urlopen(f"{URL}?{q}", timeout=60) as resp:
        payload = json.load(resp)
    rows = payload["result"]["data"]  # [ts_ms, open, high, low, close]
    out: dict[str, float] = {}
    for ts, _o, _h, _l, c in rows:
        day = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        out[day] = float(c)
    return sorted(out.items())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"asof": datetime.now(timezone.utc).isoformat(), "source": URL, "series": {}}
    for ccy in CURRENCIES:
        rows = fetch(ccy)
        if len(rows) < 30:
            raise SystemExit(f"{ccy}: too few rows ({len(rows)}); refusing to overwrite")
        path = OUT / f"dvol_{ccy.lower()}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "dvol"])
            w.writerows(rows)
        manifest["series"][ccy] = {"rows": len(rows), "first": rows[0][0], "last": rows[-1][0], "last_close": rows[-1][1]}
        print(f"{ccy}: {len(rows)} rows, last {rows[-1]}")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
