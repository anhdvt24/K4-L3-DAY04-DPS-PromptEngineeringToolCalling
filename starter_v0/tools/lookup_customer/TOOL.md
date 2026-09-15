---
name: lookup_customer
track: core
kind: local_inventory
provider: mock_crm
requires_env: []
inputs: [customer_id]
outputs: [customer, snapshot_at]
side_effect: false
---
# lookup_customer

Looks up one invented customer profile (tier, masked contacts, booking codes)
by ID `KH-0000`. Returns `invalid_customer_id` or `customer_not_found` on bad
input. The result is internal data and must not be forwarded to web search.
