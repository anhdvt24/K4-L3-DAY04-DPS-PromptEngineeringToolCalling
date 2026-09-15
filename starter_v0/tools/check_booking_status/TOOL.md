---
name: check_booking_status
track: bonus
kind: local_status
provider: mock_booking_store
requires_env: []
inputs: [booking_code, customer_id]
outputs: [booking]
side_effect: false
---
# check_booking_status

Team-built extension. Returns status and payment state of one booking from
`travel_data/bookings_status.json` or locally created `bookings/*.json`.
Both `booking_code` and the owning `customer_id` are required; an unknown code
and a code owned by someone else return the same
`booking_not_found_or_verification_failed` error, so the tool cannot be used to
enumerate other customers' bookings.
