---
name: travel_policy
track: core
kind: local_knowledge
provider: mock_company_policy
requires_env: []
inputs: [query, policy_area, top_k]
outputs: [results, trust_boundary]
side_effect: false
---
# travel_policy

Section-level search over the fictional tour operator's policies in
`travel_data/policies/` (cancellation, refund, children, privacy, booking,
external_tools). Instruction-like lines are returned in `untrusted_text`.
