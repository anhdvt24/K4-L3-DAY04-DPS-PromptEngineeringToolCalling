from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from tools._shared import ROOT, fold_text


TRAVEL_DIR = ROOT / "travel_data"
BOOKING_DIR = ROOT / "bookings"

TOUR_ID_PATTERN = re.compile(r"^TOUR-[A-Z]{2}\d{2}$")
CUSTOMER_ID_PATTERN = re.compile(r"^KH-\d{4}$")
BOOKING_CODE_PATTERN = re.compile(r"^BK-[0-9A-Z]{4,8}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INTERNAL_ID_PATTERN = re.compile(r"\b(?:KH-\d{4}|BK-[0-9A-Z]{4,8}|TOUR-[A-Z]{2}\d{2})\b", re.IGNORECASE)
# Card numbers, national ID numbers and secrets such as OTP/PIN/password values.
SENSITIVE_DATA_PATTERN = re.compile(
    r"\b(?:\d[ -]?){12,19}\b"
    r"|\b(?:cvv|cvc|otp|pin|password|mat khau|cccd|cmnd|passport|ho chieu)\b\s*(?:[:=]|la|is)?\s*[a-z]{0,2}\d{3,}",
    re.IGNORECASE,
)
SUSPICIOUS_MARKERS = (
    "assistant:", "system:", "developer:", "tro ly:", "ignore all", "ignore previous",
    "bo qua moi chi dan", "bo qua chi dan", "create_booking", "reveal the system prompt",
)


def load_json(name: str) -> dict[str, Any]:
    return json.loads((TRAVEL_DIR / name).read_text(encoding="utf-8"))


def normalize_id(value: Any) -> str:
    return value.strip().upper() if isinstance(value, str) else ""


def parse_guests(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if isinstance(value, int) and 1 <= value <= 20:
        return value
    return None


def contains_sensitive_data(text: str) -> bool:
    return bool(SENSITIVE_DATA_PATTERN.search(fold_text(text or "")))


def find_departure(tour_id: str, departure_date: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Return (tour, departure, error) for a normalized tour ID and ISO date."""
    if not TOUR_ID_PATTERN.fullmatch(tour_id):
        return None, None, {"error": "invalid_tour_id", "tour_id": tour_id, "expected_format": "TOUR-XX00"}
    if not DATE_PATTERN.fullmatch(departure_date):
        return None, None, {"error": "invalid_date_format", "departure_date": departure_date, "expected_format": "YYYY-MM-DD"}
    tour = next((item for item in load_json("tours.json")["tours"] if item["tour_id"] == tour_id), None)
    if tour is None:
        return None, None, {"error": "tour_not_found", "tour_id": tour_id}
    departure = next((item for item in tour["departures"] if item["date"] == departure_date), None)
    if departure is None:
        return tour, None, {
            "error": "departure_not_found",
            "tour_id": tour_id,
            "departure_date": departure_date,
            "available_dates": [item["date"] for item in tour["departures"]],
        }
    return tour, departure, None


def find_customer(customer_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not CUSTOMER_ID_PATTERN.fullmatch(customer_id):
        return None, {"error": "invalid_customer_id", "customer_id": customer_id, "expected_format": "KH-0000"}
    customer = next((item for item in load_json("customers.json")["customers"] if item["customer_id"] == customer_id), None)
    if customer is None:
        return None, {"error": "customer_not_found", "customer_id": customer_id}
    return customer, None


def load_doc(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            return dict(yaml.safe_load(parts[1]) or {}), parts[2].strip()
    return {}, raw.strip()


def split_untrusted(text: str) -> tuple[str, list[str]]:
    """Separate instruction-like lines (prompt injection) from reference content."""
    trusted: list[str] = []
    untrusted: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(">") or any(marker in fold_text(stripped) for marker in SUSPICIOUS_MARKERS):
            if stripped:
                untrusted.append(stripped.lstrip("> ").strip())
            continue
        trusted.append(line)
    return "\n".join(trusted).strip(), untrusted


def sections(body: str) -> list[tuple[str, str]]:
    result: list[tuple[str, list[str]]] = []
    title = "Overview"
    lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if lines:
                result.append((title, lines))
            title = line[3:].strip()
            lines = []
        else:
            lines.append(line)
    if lines:
        result.append((title, lines))
    return [(name, "\n".join(chunk).strip()) for name, chunk in result if "\n".join(chunk).strip()]
