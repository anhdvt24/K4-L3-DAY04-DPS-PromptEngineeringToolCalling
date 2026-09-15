from __future__ import annotations

from typing import Any

from tools._shared import err
from tools._travel import find_customer, load_json, normalize_id


def lookup_customer(customer_id: str = "") -> dict[str, Any]:
    try:
        customer, error = find_customer(normalize_id(customer_id))
        if error:
            return {"tool": "lookup_customer", **error}
        return {
            "tool": "lookup_customer",
            "customer": customer,
            "snapshot_at": load_json("customers.json")["snapshot_at"],
            "privacy": "Internal customer data. Do not send names, contacts or booking codes to external tools.",
        }
    except Exception as exc:
        return err("lookup_customer", exc)
