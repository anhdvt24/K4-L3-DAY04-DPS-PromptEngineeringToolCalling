---
name: check_transport_status
track: core
kind: local_status
provider: mock_transport_feed
requires_env: []
inputs: [mode, route]
outputs: [status, delay_minutes, note, checked_at]
side_effect: false
---
# check_transport_status

Returns today's fictional status snapshot for one route of one transport mode
(`flight`, `train`, `bus`, `ferry`). Routes use location codes joined by a dash,
for example `HAN-PQC`. Unknown routes return `route_not_found` with the routes
available for that mode.
