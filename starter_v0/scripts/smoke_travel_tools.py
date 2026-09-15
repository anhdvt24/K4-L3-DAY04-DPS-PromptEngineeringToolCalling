"""Offline smoke test for the travel tools and eval datasets (no model calls)."""
from __future__ import annotations

import importlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tools._travel as travel  # noqa: E402
from run_eval import load_cases, validate_expected_tools  # noqa: E402
from tools import TOOL_FUNCTIONS, load_tool_declarations  # noqa: E402


def check(label: str, condition: bool) -> None:
    print(f"{'OK  ' if condition else 'FAIL'} {label}")
    if not condition:
        raise SystemExit(1)


def main() -> None:
    f = TOOL_FUNCTIONS
    declarations = load_tool_declarations(ROOT / "artifacts" / "tools.yaml")
    for item in declarations:
        check(f"declared tool {item['name']} is implemented", item["name"] in f)

    for name, count in (("eval_travel_base.json", 30), ("eval_travel_adversarial.json", 12), ("eval_travel_extension.json", 5)):
        path = ROOT / "data" / name
        cases = load_cases(path, "B")
        validate_expected_tools(cases, declarations, path)
        check(f"{name} has {count} valid cases", len(cases) == count)
    base = load_cases(ROOT / "data" / "eval_travel_base.json", "B")
    check("base split is 20 single + 10 multi", sum("turns" in c for c in base) == 10)

    r = f["check_tour_availability"](tour_id="tour-dl01", departure_date="2026-10-20", guests=2)
    check("availability open departure", r.get("can_book") is True)
    check("availability bad date", f["check_tour_availability"](tour_id="TOUR-DL01", departure_date="20/10/2026")["error"] == "invalid_date_format")
    check("availability unknown tour", f["check_tour_availability"](tour_id="TOUR-XX99", departure_date="2026-10-20")["error"] == "tour_not_found")
    check("availability not enough seats", f["check_tour_availability"](tour_id="TOUR-HA03", departure_date="2026-12-05", guests=2)["can_book"] is False)

    check("transport found", f["check_transport_status"](mode="flight", route="han-pqc")["status"] == "delayed")
    check("transport unknown route", f["check_transport_status"](mode="ferry", route="HAN-SGN")["error"] == "route_not_found")
    check("customer found", f["lookup_customer"](customer_id="KH-1003")["customer"]["tier"] == "standard")
    check("customer bad id", f["lookup_customer"](customer_id="Lan")["error"] == "invalid_customer_id")

    guide = f["search_travel_guide"](query="an toàn đi biển Phú Quốc", category="destination")
    check("guide finds Phu Quoc", guide["results"][0]["article_id"] == "GUIDE-DEST-PQ")
    check("guide strips injection", guide["results"][0]["untrusted_text"] and "create_booking" not in guide["results"][0]["content"])
    policy = f["travel_policy"](query="chia sẻ dữ liệu khách hàng", policy_area="privacy")
    check("policy strips injection", any(hit["untrusted_text"] for hit in policy["results"]))

    original_dir = travel.BOOKING_DIR
    tmp_dir = ROOT / "bookings_smoke_tmp"
    # tools/__init__.py re-exports functions with the same names as the subpackages,
    # so resolve the modules through importlib instead of attribute access.
    create_mod = importlib.import_module("tools.create_booking.tool")
    status_mod = importlib.import_module("tools.check_booking_status.tool")
    create_mod.BOOKING_DIR = status_mod.BOOKING_DIR = tmp_dir
    try:
        args = dict(tour_id="TOUR-DL01", departure_date="2026-10-20", guests=2, customer_id="KH-1001")
        check("booking needs confirmation", f["create_booking"](**args)["status"] == "needs_confirmation" and not tmp_dir.exists())
        check("booking rejects card number", f["create_booking"](**args, note="the 4111 1111 1111 1111", confirmed=True)["error"] == "restricted_sensitive_data")
        check("booking rejects sold out", f["create_booking"](tour_id="TOUR-DL01", departure_date="2026-11-03", guests=1, customer_id="KH-1001", confirmed=True)["error"] == "not_bookable")
        created = f["create_booking"](**args, confirmed=True)
        check("booking created after confirmation", created["status"] == "created")
        status = f["check_booking_status"](booking_code=created["booking_code"], customer_id="KH-1001")
        check("extension finds new booking", status["booking"]["status"] == "pending_payment")
    finally:
        create_mod.BOOKING_DIR = status_mod.BOOKING_DIR = original_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)

    check("extension seeded booking", f["check_booking_status"](booking_code="BK-7790", customer_id="KH-1002")["booking"]["payment_status"] == "refund_pending")
    wrong_owner = f["check_booking_status"](booking_code="BK-7790", customer_id="KH-1001")
    unknown = f["check_booking_status"](booking_code="BK-0000", customer_id="KH-1001")
    check("extension hides other owners' bookings", wrong_owner == unknown and "booking" not in wrong_owner)

    blocked = f["search_travel_info"](query="khuyến mãi Phú Quốc KH-1001 BK-7788")
    check("web search blocks internal IDs before any request", blocked["error"] == "restricted_internal_identifier")
    print(json.dumps({"result": "all smoke checks passed"}))


if __name__ == "__main__":
    main()
