---
name: create_booking
track: core
kind: action
provider: local_booking_store
requires_env: []
inputs: [tour_id, departure_date, guests, customer_id, note, confirmed]
outputs: [status, booking_preview, booking_code, path]
side_effect: local_file_write
requires_confirmation: true
---
# create_booking

Creates a local mock booking under `bookings/` (gitignored). Validates tour ID,
ISO date, guest count, customer ID and remaining seats. It returns
`needs_confirmation` with a `booking_preview` and writes nothing unless
`confirmed` is explicitly `true`. Notes containing card numbers, CVV, OTP,
passwords or ID numbers are rejected with `restricted_sensitive_data`.
