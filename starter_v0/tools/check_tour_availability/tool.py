from __future__ import annotations

from typing import Any

from tools._shared import err
from tools._travel import find_departure, load_json, normalize_id, parse_guests


def check_tour_availability(tour_id: str = "", departure_date: str = "", guests: int = 1) -> dict[str, Any]:
    try:
        wanted_id = normalize_id(tour_id)
        wanted_date = departure_date.strip() if isinstance(departure_date, str) else ""
        guest_count = parse_guests(guests)
        if guest_count is None:
            return {"tool": "check_tour_availability", "error": "invalid_guests", "guests": guests, "allowed_range": [1, 20]}
        tour, departure, error = find_departure(wanted_id, wanted_date)
        if error:
            return {"tool": "check_tour_availability", **error}
        can_book = departure["status"] == "open" and departure["seats_left"] >= guest_count
        return {
            "tool": "check_tour_availability",
            "tour": {key: tour[key] for key in ("tour_id", "name", "destination", "duration", "departure_city", "price_adult_vnd", "includes")},
            "departure": departure,
            "guests": guest_count,
            "can_book": can_book,
            "estimated_total_vnd": tour["price_adult_vnd"] * guest_count,
            "pricing_note": "Estimate uses adult price; children pricing follows the children policy.",
            "snapshot_at": load_json("tours.json")["snapshot_at"],
        }
    except Exception as exc:
        return err("check_tour_availability", exc)
