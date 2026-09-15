---
name: search_travel_guide
track: core
kind: local_knowledge
provider: mock_travel_guide
requires_env: []
inputs: [query, category, top_k]
outputs: [results, trust_boundary]
side_effect: false
---
# search_travel_guide

Keyword search over the company's fictional travel guides in
`travel_data/guides/` (visa, luggage, destination, health, payment).
Instruction-like lines inside a guide are stripped from `content` and returned
in `untrusted_text` so the agent never follows them.
