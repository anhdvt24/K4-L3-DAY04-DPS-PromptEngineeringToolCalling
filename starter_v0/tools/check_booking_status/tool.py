from __future__ import annotations

import json
from typing import Any

from tools._shared import err
from tools._travel import BOOKING_CODE_PATTERN, BOOKING_DIR, CUSTOMER_ID_PATTERN, load_json, normalize_id


def _all_bookings() -> list[dict[str, Any]]:
    bookings = list(load_json("bookings_status.json")["bookings"])
    if BOOKING_DIR.exists():
        bookings.extend(json.loads(path.read_text(encoding="utf-8")) for path in sorted(BOOKING_DIR.glob("*.json")))
    return bookings


def check_booking_status(booking_code: str = "", customer_id: str = "") -> dict[str, Any]:
    tool = "check_booking_status"
    try:
        wanted_code = normalize_id(booking_code)
        wanted_customer = normalize_id(customer_id)
        if not BOOKING_CODE_PATTERN.fullmatch(wanted_code):
            return {"tool": tool, "error": "invalid_booking_code", "expected_format": "BK-0000"}
        if not CUSTOMER_ID_PATTERN.fullmatch(wanted_customer):
            return {"tool": tool, "error": "invalid_customer_id", "expected_format": "KH-0000"}
        booking = next((item for item in _all_bookings() if item["booking_code"] == wanted_code), None)
        # Same error for unknown code and wrong owner, so the tool cannot be used to probe other customers' bookings.
        if booking is None or booking["customer_id"] != wanted_customer:
            return {
                "tool": tool,
                "error": "booking_not_found_or_verification_failed",
                "message": "No booking matches this booking code and customer ID.",
            }
        return {"tool": tool, "booking": booking}
    except Exception as exc:
        return err(tool, exc)
