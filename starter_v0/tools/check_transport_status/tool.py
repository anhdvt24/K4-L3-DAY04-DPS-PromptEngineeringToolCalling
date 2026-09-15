from __future__ import annotations

from typing import Any

from tools._shared import err
from tools._travel import load_json, normalize_id


TRANSPORT_MODES = {"flight", "train", "bus", "ferry"}


def check_transport_status(mode: str = "", route: str = "") -> dict[str, Any]:
    try:
        wanted_mode = mode.strip().lower() if isinstance(mode, str) else ""
        wanted_route = normalize_id(route).replace(" ", "")
        if wanted_mode not in TRANSPORT_MODES:
            return {"tool": "check_transport_status", "error": "invalid_mode", "mode": wanted_mode, "allowed": sorted(TRANSPORT_MODES)}
        data = load_json("transport_status.json")
        for item in data["routes"]:
            if item["mode"] == wanted_mode and item["route"] == wanted_route:
                return {"tool": "check_transport_status", **item, "checked_at": data["snapshot_at"]}
        return {
            "tool": "check_transport_status",
            "mode": wanted_mode,
            "route": wanted_route,
            "error": "route_not_found",
            "available_routes": sorted(item["route"] for item in data["routes"] if item["mode"] == wanted_mode),
        }
    except Exception as exc:
        return err("check_transport_status", exc)
