from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compute_airdm import build_latest, history_point
from fetch_market_prices import fetch_market_prices
from fetch_sec_capex import fetch_sec_capex
from fetch_tw_revenue import fetch_tw_revenue

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"
LATEST_PATH = DATA_DIR / "latest.json"
HISTORY_PATH = DATA_DIR / "history.json"
SOURCE_STATUS_PATH = DATA_DIR / "source_status.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    mode = os.environ.get("UPDATE_MODE", "full").strip().lower()
    old_latest = read_json(LATEST_PATH, None)
    history = read_json(HISTORY_PATH, {"updated_at": None, "series": [], "tw_revenue_observations": {}})

    previous_tw_observations = history.get("tw_revenue_observations", {})

    if mode == "market":
        supply = old_component(old_latest, "supply_chain_revenue", "tw_revenue")
        capex = old_component(old_latest, "hyperscaler_capex", "sec_capex")
    else:
        supply = fetch_tw_revenue(previous_tw_observations, data_dir=DATA_DIR)
        capex = fetch_sec_capex()
    market = fetch_market_prices()

    fatal_count = sum(1 for result in (supply, capex, market) if result.get("score") is None)
    if fatal_count == 3 and old_latest:
        latest = old_latest
        latest["stale"] = True
        latest["stale_components"] = ["supply_chain_revenue", "hyperscaler_capex", "market_confirmation"]
        latest["source_status"] = {
            "tw_revenue": "stale",
            "sec_capex": "stale",
            "market_prices": "stale",
        }
        latest["as_of"] = old_latest.get("as_of", utc_now())
    else:
        latest = build_latest(supply, capex, market, old_latest)
        if mode == "market":
            latest["stale"] = True
            latest["stale_components"] = sorted(
                set(latest.get("stale_components", []) + ["supply_chain_revenue", "hyperscaler_capex"])
            )
            latest["source_status"]["tw_revenue"] = "stale"
            latest["source_status"]["sec_capex"] = "stale"
        series = list(history.get("series", []))
        point = history_point(latest)
        if not series or series[-1].get("as_of") != point["as_of"]:
            series.append(point)
        history["series"] = series[-730:]

    history["updated_at"] = utc_now()
    if supply.get("observations"):
        history["tw_revenue_observations"] = supply["observations"]

    source_status = {
        "generated_at": utc_now(),
        "stale": latest.get("stale", False),
        "sources": {
            "tw_revenue": supply.get("source_detail", {}),
            "sec_capex": capex.get("source_detail", {}),
            "market_prices": market.get("source_detail", {}),
        },
    }
    for key, component in (
        ("tw_revenue", "supply_chain_revenue"),
        ("sec_capex", "hyperscaler_capex"),
        ("market_prices", "market_confirmation"),
    ):
        if component in latest.get("stale_components", []):
            source_status["sources"].setdefault(key, {})["status"] = "stale"

    write_json_atomic(LATEST_PATH, latest)
    write_json_atomic(HISTORY_PATH, history)
    write_json_atomic(SOURCE_STATUS_PATH, source_status)

    print(
        "AI-RDM updated:",
        latest["ai_rdm_score"],
        latest["status"],
        f"mode={mode}",
        "sources=",
        latest["source_status"],
    )


def old_component(old_latest: dict[str, Any] | None, detail_key: str, source_key: str) -> dict[str, Any]:
    if not old_latest:
        return {
            "score": None,
            "status": "error",
            "source_detail": {
                "status": "error",
                "last_updated": utc_now(),
                "source": "previous latest.json",
                "missing": [source_key],
                "notes": ["market mode requires an existing latest.json for fundamental components"],
            },
        }

    detail = dict(old_latest.get("details", {}).get(detail_key, {}))
    detail["score"] = old_latest.get("subscores", {}).get(detail_key)
    detail["status"] = "stale"
    detail["source_detail"] = {
        "status": "stale",
        "last_updated": old_latest.get("as_of"),
        "source": "previous latest.json",
        "missing": [],
        "notes": ["market-only update: fundamental component carried forward"],
    }
    return detail


if __name__ == "__main__":
    main()
