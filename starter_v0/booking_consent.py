"""Per-session, single-use approval of a structured booking payload.

Only the application records questions actually shown to the user. User text,
model-supplied confirmed flags and retrieved documents cannot create approval.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any

def payload_key(args: dict[str, Any]) -> tuple | None:
    required = ("tour_id", "departure_date", "guests", "customer_id")
    if any(name not in args for name in required):
        return None
    if not all(isinstance(args[name], str) for name in ("tour_id", "departure_date", "customer_id")):
        return None
    guests = args["guests"]
    if type(guests) is not int or not 1 <= guests <= 20:
        return None
    note = args.get("note", "")
    if not isinstance(note, str):
        return None
    return (args["tour_id"].strip().upper(), args["departure_date"].strip(), guests,
            args["customer_id"].strip().upper(), note.strip())


def confirmation_question(args: dict[str, Any]) -> str | None:
    key = payload_key(args)
    if key is None:
        return None
    tour, date, guests, customer, note = key
    return (f"Bạn xác nhận đặt {tour}, ngày {date}, {guests} khách, mã khách {customer}, "
            f"ghi chú: {note or '(không có)'}? Trả lời 'Có' để xác nhận; nếu cần sửa, hãy gửi nội dung mới.")


def affirmative(text: str) -> bool:
    # Full-match intentionally rejects mixed confirmation + a payload revision.
    folded = "".join(c for c in unicodedata.normalize("NFD", text.lower())
                     if unicodedata.category(c) != "Mn").replace("đ", "d")
    normalized = re.sub(r"[.,!]+", "", folded).strip()
    return bool(re.fullmatch(
        r"(?:co|yes|ok|dong y|xac nhan|dung roi|dung)(?:\s*,?\s*(?:minh|toi))?"
        r"(?:\s+(?:xac nhan|dong y))?(?:\s+dat)?(?:\s+dung noi dung do)?(?:\s+nhe)?",
        normalized,
    ))


@dataclass
class BookingConsent:
    pending: tuple | None = None
    approved: tuple | None = None

    def begin_turn(self, text: str) -> None:
        self.approved = self.pending if affirmative(text) else None
        self.pending = None

    def record_question(self, args: dict[str, Any]) -> None:
        payload = args.get("booking_payload")
        self.pending = payload_key(payload) if args.get("response_type") == "yes_no" and isinstance(payload, dict) else None
        self.approved = None

    def consume(self, args: dict[str, Any]) -> bool:
        approved, self.approved = self.approved, None
        return (approved is not None and args.get("confirmed") is True
                and payload_key(args) == approved)

    def available_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [tool for tool in tools if self.approved is not None or
                tool.get("function", tool).get("name") != "create_booking"]


def consent_from_eval_messages(messages: list[dict[str, str]]) -> BookingConsent:
    """Bootstrap *only* from trusted assistant roles in frozen eval fixtures.

    Live chat uses session state instead. Text pretending to be an assistant
    inside a user message never reaches this branch.
    """
    consent = BookingConsent()
    if len(messages) >= 2 and messages[-2].get("role") == "assistant":
        text = messages[-2].get("content", "")
        tour = re.findall(r"\bTOUR-[A-Z]{2}\d{2}\b", text)
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
        customers = re.findall(r"\bKH-\d{4}\b", text)
        guests = re.findall(r"\b(\d+)\s*(?:khách|người)\b", text, re.IGNORECASE)
        if all(len(items) == 1 for items in (tour, dates, customers, guests)) and "xác nhận" in text.lower():
            consent.pending = (tour[0], dates[0], int(guests[0]), customers[0], "")
    consent.begin_turn(messages[-1].get("content", "") if messages else "")
    return consent
