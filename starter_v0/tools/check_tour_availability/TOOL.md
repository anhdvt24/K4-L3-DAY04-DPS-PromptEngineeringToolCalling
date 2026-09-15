---
name: check_tour_availability
track: core
kind: local_inventory
provider: mock_tour_inventory
requires_env: []
inputs: [tour_id, departure_date, guests]
outputs: [tour, departure, can_book, estimated_total_vnd]
side_effect: false
---
# check_tour_availability

Looks up one fictional tour departure in `travel_data/tours.json` and reports
remaining seats, status and an adult-price estimate. Requires a tour ID in the
format `TOUR-XX00`, an ISO date `YYYY-MM-DD` and 1–20 guests. Returns
`invalid_tour_id`, `invalid_date_format`, `tour_not_found`,
`departure_not_found` (with available dates) or `invalid_guests` on bad input.
