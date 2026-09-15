from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from tools._shared import err
from tools._travel import BOOKING_DIR, contains_sensitive_data, find_customer, find_departure, normalize_id, parse_guests


def create_booking(
    tour_id: str = "",
    departure_date: str = "",
    guests: int = 1,
    customer_id: str = "",
    note: str = "",
    confirmed: bool = False,
) -> dict[str, Any]:
    tool = "create_booking"
    for name, value in (("tour_id", tour_id), ("departure_date", departure_date), ("customer_id", customer_id), ("note", note)):
        if not isinstance(value, str):
            return {"tool": tool, "error": f"invalid_{name}_type"}
    guest_count = parse_guests(guests)
    if guest_count is None:
        return {"tool": tool, "error": "invalid_guests", "allowed_range": [1, 20]}
    normalized_note = note.strip()
    if len(normalized_note) > 500:
        return {"tool": tool, "error": "note_too_long", "max_length": 500}
    if contains_sensitive_data(normalized_note):
        return {
            "tool": tool,
            "error": "restricted_sensitive_data",
            "message": "Remove card numbers, CVV, OTP, passwords and ID numbers from the booking note.",
        }
    try:
        tour, departure, error = find_departure(normalize_id(tour_id), departure_date.strip())
        if error:
            return {"tool": tool, **error}
        customer, error = find_customer(normalize_id(customer_id))
        if error:
            return {"tool": tool, **error}
        if departure["status"] != "open" or departure["seats_left"] < guest_count:
            return {
                "tool": tool,
                "error": "not_bookable",
                "departure_status": departure["status"],
                "seats_left": departure["seats_left"],
                "guests": guest_count,
            }
        preview = {
            "tour_id": tour["tour_id"],
            "tour_name": tour["name"],
            "departure_date": departure["date"],
            "guests": guest_count,
            "customer_id": customer["customer_id"],
            "estimated_total_vnd": tour["price_adult_vnd"] * guest_count,
            "note": normalized_note or None,
        }
        if confirmed is not True:
            return {
                "tool": tool,
                "status": "needs_confirmation",
                "booking_preview": preview,
                "message": "Create the booking only after the user explicitly confirms this exact preview.",
            }
        now = datetime.now(timezone.utc)
        seed = f"{now.isoformat()}|{json.dumps(preview, ensure_ascii=False, sort_keys=True)}"
        booking_code = "BK-L" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:6].upper()
        payload = {
            "booking_code": booking_code,
            **preview,
            "status": "pending_payment",
            "payment_status": "unpaid",
            "created_at": now.isoformat(),
            "source": "educational_local_mock",
        }
        BOOKING_DIR.mkdir(parents=True, exist_ok=True)
        path = BOOKING_DIR / f"{booking_code}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"tool": tool, "status": "created", "booking_code": booking_code, "booking": payload, "path": str(path)}
    except Exception as exc:
        return err(tool, exc)
