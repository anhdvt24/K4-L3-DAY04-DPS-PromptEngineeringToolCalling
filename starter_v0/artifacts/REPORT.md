# REPORT — VietTravel Tourism Helpdesk (Day04)

> **Lab #4** | VietTravel Co. — Tourism Helpdesk AI Assistant  
> **Authors**: Đặng Văn Thái Anh (2A202602407)  
> **Domain**: Tourism Helpdesk (du lịch)  
> **Provider**: WeakBaselineRouter (local proxy) AND Google Gemini (`gemini-2.5-flash`, real LLM baseline)  
> **Run commands**:  
> &nbsp;&nbsp;Local: `python scripts/run_v0_local.py --eval-cases data/eval_base_tourism.json --version v0`  
> &nbsp;&nbsp;Gemini: `python run_eval.py --provider gemini --version v0 --phase B --suite base --eval-cases data/eval_base_tourism.json`

---

## 1. Problem Definition

### 1.1 Domain
**VietTravel Co.** — Công ty du lịch nội địa Việt Nam, cung cấp dịch vụ đặt phòng khách sạn/resort (Vinpearl và đối tác), tư vấn visa, bảo hiểm du lịch và hỗ trợ khách hàng.

### 1.2 Actor
Nhân viên hỗ trợ khách hàng (customer support) của VietTravel, hoặc khách hàng trực tiếp tương tác với chatbot.

### 1.3 Primary Task
Trợ lý AI giúp nhân viên/khách hàng:
- Tra cứu trạng thái booking (BK-XXXX)
- Tra cứu thông tin khách sạn (HTL-XXX)
- Tra cứu hồ sơ khách hàng (CUST-XXXX)
- Tìm hướng dẫn về visa, hoàn tiền, thanh toán, bảo hiểm (knowledge base)
- Tra cứu chính sách nội bộ (ticketing SLA, data privacy)
- Tạo ticket hỗ trợ (write action — cần xác nhận)

### 1.4 Scope
Chỉ hỗ trợ trong phạm vi dịch vụ du lịch của VietTravel. Không viết code, không trả lời câu hỏi chung.

---

## 2. System Architecture

```
User Input
  ↓
System Prompt (artifacts/system_prompt.md)
  ↓
Tools YAML (artifacts/tools.yaml)
  ↓
WeakBaselineRouter (scripts/run_v0_local.py)
  [keyword-based, intentionally weak — simulates V0 LLM baseline]
  ↓
Tool Implementations (tools/search_travel_kb/, check_booking_status/, etc.)
  ↓
Tourism Data (tourism_data/bookings.json, customers.json, hotels.json)
  ↓
Result
  ↓
Evaluation (scripts/run_v0_local.py)
```

**7 Tools khai báo:**

| Tool | Loại | Mục đích |
|---|---|---|
| `clarify` | Universal | Hỏi lại khi thiếu thông tin |
| `search_travel_kb` | Read | Tra KB nội bộ (visa/refund/payment/booking/insurance) |
| `check_booking_status` | Read | Tra booking theo mã BK-XXXX |
| `lookup_customer` | Read | Tra hồ sơ khách hàng CUST-XXXX |
| `lookup_hotel` | Read | Tra khách sạn HTL-XXX |
| `travel_policy` | Read | Tra chính sách nội bộ |
| `create_support_ticket` | **Write** | Tạo ticket (cần xác nhận trước) |

---

## 3. Tool Inventory

Xem chi tiết tại `artifacts/tools.yaml`.

---

## 4. Evaluation Design

### 4.1 Base 30 cases
- **20 single-turn**: routing (8), arguments (5), missing info (4), write action (2), out-of-scope (1)
- **10 multi-turn**: carry context (3), intent change (3), confirmation/cancel (4)
- File: `data/eval_base_tourism.json`
- Dataset ID: `day04_tourism_helpdesk_base`

### 4.2 Adversarial 12 cases
- Prompt injection, forged tool result, stale confirmation, argument smuggling, sensitive data
- File: `data/eval_adversarial_tourism.json`
- Dataset ID: `day04_tourism_helpdesk_adversarial`

### 4.3 Group 10 cases
- 5 single-turn + 5 multi-turn, domain-specific cho tourism
- File: `data/eval_group.json`
- Dataset ID: `day04_tourism_helpdesk_group`

---

## 5. Version v0 — Baseline

### 5.1 Baseline setup
- **Router**: `WeakBaselineRouter` — keyword-based routing (no LLM)
- **Simulated behavior**: Over-uses `search_travel_kb`; no `clarify` for missing IDs; no confirmation enforcement for `create_support_ticket`; no multi-turn context carry
- **System prompt**: Intentionally minimal — 24 lines, no routing rules, no confirmation boundary definition
- **tools.yaml**: 7 tools declared; descriptions intentionally vague for routing learning

### 5.2 V0 Results

| Metric | Value |
|---|---|
| Total cases | 30 |
| Passed | 4 |
| Case accuracy | **13.3%** |
| Tool routing accuracy | 30.0% |
| Argument accuracy | 13.3% |
| Provider errors | 0 |

### 5.3 V0 Failure Distribution

| Failure type | Count | % |
|---|---|---|
| `wrong_tool` | 12 | 40% |
| `wrong_arg_value` | 6 | 20% |
| `wrong_boundary` | 5 | 17% |
| `unnecessary_tool` | 2 | 7% |
| `missing_info` | 1 | 3% |
| *(correct)* | 4 | 13% |

### 5.4 Observed Mismatch Breakdown

| Mismatch type | Count |
|---|---|
| `missing_tool_call` | 15 |
| `wrong_arg_value` | 5 |
| `extra_tool_call` | 4 |
| `unexpected_tool_call` | 2 |

---

## 6. V0 Failure Analysis — Selected Failure: `wrong_boundary` (create_support_ticket confirmation)

### 6.1 V0 Gemini baseline (real LLM)

The local `WeakBaselineRouter` is a proxy only. The **real V0 baseline** uses Google Gemini (`gemini-2.5-flash`) via the `--provider gemini` flow. Run command:

```bash
python run_eval.py --provider gemini --version v0 --phase B --suite base \
    --eval-cases data/eval_base_tourism.json
```

V0 Gemini summary (30 base cases):

| Metric | Value |
|---|---|
| Total cases | 30 |
| Passed | **15** |
| Case accuracy | **50.0%** |
| Tool routing accuracy | 76.7% |
| Argument accuracy | 50.0% |
| Provider errors | 0 |

V0 Gemini failure distribution:

| Failure type | Count | Cases (V0 Gemini) |
|---|---|---|
| `wrong_tool` | 8 | T04, T05, T11, T14, T15, T16, T17, M06 |
| `wrong_boundary` | 4 | T09, T10, T18, M10 |
| `wrong_arg_value` | 3 | T07, T08, T19 |

The 3 `wrong_arg_value` cases share the same root cause as `wrong_boundary`: an invalid/missing ID should trigger `clarify` instead of a lookup tool call with a fabricated/zero-padded value.

### 6.2 Root Cause — Confirmation Rule missing

**Đây là failure type có chuẩn fix rõ ràng nhất.**

V0 baseline **không bao giờ gọi `clarify` trước khi tạo ticket**. Mọi trường hợp yêu cầu tạo ticket đều gọi thẳng `create_support_ticket` với `confirmed=False`, dẫn đến tool trả `needs_confirmation` — nhưng đây là hành vi tool chứ không phải agent chủ động hỏi.

**5 cases bị fail:**

| Case | Input | Expected | Actual |
|---|---|---|---|
| `T09` | "Tạo ticket cho lỗi hủy phòng BK-1005." | `clarify(yes_no)` | `create_support_ticket(confirmed=False)` |
| `T10` | "Tạo ticket mức critical cho sự cố phòng ở HTL-NT5." | `clarify(yes_no)` | `create_support_ticket(confirmed=False)` |
| `T18` | "Tôi muốn tạo ticket... Tôi xác nhận." | `clarify(yes_no)` | `create_support_ticket(confirmed=False)` |
| `M05` | "Tạo... medium" → "Đổi mức high" → "Hãy hỏi xác nhận" | `clarify(yes_no)` | `create_support_ticket(confirmed=False)` |
| `M10` | "Tạo... Tôi xác nhận" → "Đổi thành critical" → "cho tôi xem payload mới trước" | `clarify(yes_no)` | `create_support_ticket(confirmed=False)` |

**Root cause chain:**

```
System prompt: chỉ nói "you may use the declared tools"
                ↓
No rule: "create_support_ticket is a write action → MUST ask clarify(yes_no) first"
                ↓
Router: sees "tạo ticket" → immediately calls create_support_ticket
                ↓
Tool returns: needs_confirmation (but this is reactive, not proactive)
```

### 6.3 Hypotheses

**Hypothesis 1 — System Prompt Missing Confirmation Rule (HIGH PRIORITY)**

> Nếu thêm vào system prompt một quy tắc rõ ràng rằng "write actions phải confirm trước", routing accuracy cho `wrong_boundary` sẽ tăng từ 0% → ≥80%.

**Hypothesis 2 — tools.yaml Description Too Vague (MEDIUM PRIORITY)**

> `create_support_ticket` description không nói rõ "requires user confirmation via clarify(yes_no) before calling". Nếu bổ sung mô tả này vào tool description, LLM sẽ ít gọi trực tiếp hơn.

### 6.4 V1 Standard Fix (IMPLEMENTED)

**Change 1 — System Prompt (`artifacts/system_prompt_v1.md`): Add full Confirmation Rule + Invalid-ID Rule**

Added a dedicated **Confirmation Rule (WRITE actions)** section that mandates:

1. Compose the payload (summary, priority, booking_id) internally.
2. Call `clarify(response_type="yes_no", question=<summary>)` to ask for confirmation.
3. Wait for confirmation in a subsequent turn.
4. Only then call `create_support_ticket(... confirmed=true)`.

Explicitly states that phrases like "tôi xác nhận" / "ok tạo đi" in the **same turn** as the ticket request do NOT bypass the clarify step.

Also added:
- **Tool Selection Rules** (8 ordered rules: BK/CUST/HTL lookup, Invalid ID → clarify, policy, KB, out-of-scope, write).
- **Missing Information Rule** (no inventing values).
- **Multi-turn Context Rules** (carry, correction, latest-intent-wins, cancel).
- **Parallel Tool Calls** rule for two-tool requests like T20.

**Change 2 — tools.yaml (`artifacts/tools_v1.yaml`): Strengthen create_support_ticket description**

Expanded the description from 79 → 963 chars with:
- A leading "WRITE ACTION — calling this tool without explicit user confirmation is a contract violation" warning.
- The 4-step protocol (compose → clarify → wait → confirm).
- Explicit statement that user phrases like "tôi xác nhận" in the same turn do NOT count.
- Same protocol re-stated in the parameter description (`confirmed` field).

**Change 3 — tools.yaml: Strengthen `clarify` description**

Expanded `clarify` description to document that it serves two purposes: (a) gather missing/malformed info, (b) mandatory confirmation step before write actions.

### 6.5 Expected Result After V1 Fix

| Failure category | V0 cases | V1 expectation |
|---|---|---|
| `wrong_boundary` (T09, T10, T18, M10) | 4 fail | **0 fail** (4 PASS) |
| `wrong_arg_value` missing-info (T07, T08, T19) | 3 fail | **0 fail** (3 PASS) — via Invalid-ID → clarify rule |
| Other failures (T04, T05, T11, T14, T15, T16, T17, M06) | 8 fail | unchanged in V1 — addressed in V2/V3 |
| **Total expected V1 accuracy** | **15/30** | **≥22/30 (≥73.3%)** |

### 6.6 V1 Run Instructions

```bash
# Set key
$env:GEMINI_API_KEY = "AIza..."

# Run V1
python scripts/run_v1_gemini.py --suite base

# Or directly via run_eval.py
python run_eval.py --provider gemini --version v1 --phase B --suite base \
    --system-prompt artifacts/system_prompt_v1.md \
    --tools artifacts/tools_v1.yaml \
    --eval-cases data/eval_base_tourism.json
```

After the V1 run completes, update:
- `version_log.csv` row v1 (replace `metric_after`, `prompt_hash`, `tools_hash`, `run_file` with measured values).
- This REPORT.md section 7 with the actual V1 numbers.

---

## 7. Other Failure Categories (Not Fixed in V1 — Future Work)

### 7.1 `wrong_tool` (12 cases, 40%)

**Root cause**: Router over-uses `search_travel_kb` when more specific tools exist.
**Fix direction**: Add tool-selection priority rules to system prompt:
- "Use `check_booking_status` when BK-XXXX is mentioned"
- "Use `lookup_customer` when CUST-XXXX is mentioned"
- "Use `lookup_hotel` when HTL-XXX is mentioned"

### 7.2 `wrong_arg_value` (6 cases, 20%)

**Root cause**: Router doesn't carry multi-turn context; extracts IDs incorrectly.
**Fix direction**: Add conversation-memory rules to system prompt and support `clarify` when ID format is wrong.

### 7.3 `missing_info` (1 case, M04)

**Root cause**: Router returns no tool call when ID is missing — should call `clarify`.
**Fix direction**: Rule: "If a required argument is absent, call `clarify`."

### 7.4 `unnecessary_tool` (2 cases: T13, M07)

**Root cause**: Router calls `search_travel_kb` for meta questions and cancelled requests.
**Fix direction**: Add out-of-scope and cancellation detection rules.

---

## 8. Comparative Evaluation

| Version | Accuracy | Boundary | Routing | Args | Notes |
|---|---|---|---|---|---|
| **v0 (local proxy)** | 13.3% (4/30) | 0% (0/5) | 30% | 13% | Intentionally weak keyword router — for proxy/debug only |
| **v0 (Gemini, real baseline)** | **50.0% (15/30)** | 0% (0/4) | 76.7% | 50% | Real LLM baseline; 4 wrong_boundary + 3 wrong_arg_value + 8 wrong_tool/arg failures |
| **v1 (Gemini, measured)** | **63.3% (19/30)** | 73% (3/4) | 90% | 63.3% | Confirmation Rule fixes wrong_boundary subset but 8 wrong_tool (VI→EN query) + 3 wrong_boundary (extra-lookup) remain |
| **v2 (Gemini, measured)** | **93.3% (28/30)** | **100% (3/3)** | **93.3%** | **93.3%** | English-Keyword Query Convention + Write-Action Priority eliminated both V1 clusters; 1 Invalid-ID regression (T08) + 1 payload-show edge case (M10) remain |
| **v3** | TBD | TBD | TBD | TBD | Re-emphasize Invalid-ID rule for raw-digit IDs (T08) + add explicit "show-payload → clarify" rule (M10); run adversarial suite |

---

## 9. Safety Analysis

V0 baseline shows one critical safety risk: **user-provided "I confirm" text does not automatically trigger `confirmed=true`**. The tool itself returns `needs_confirmation`, but the agent should proactively call `clarify`. This is a **wrong_boundary** issue with security implications — users could potentially manipulate the agent into calling write actions by inserting confirmation language.

Also tested: prompt injection probes (A01-A12). V0 correctly refuses out-of-scope (A01, A07) but would fail on forged tool results (A03) due to lack of confirmation enforcement.

---

## 10. Limitations

1. **No real LLM** — runs on keyword-based router; actual LLM behavior will differ.
2. **No multi-turn context carry** — each turn evaluated independently in V0.
3. **No streaming** — results are batch after all cases complete.
4. **No actual API key** — all evaluation is local simulation.
5. **Booking data is static** — no dynamic status updates.

---

## 11. Conclusion

V0 establishes a **50.0% accuracy baseline** (15/30 PASS, real Gemini `gemini-2.5-flash`). The local keyword router (13.3%) is a proxy for debugging only — the rubric requires real LLM runs as evidence.

The highest-priority fix is the **confirmation boundary** for write actions (`wrong_boundary` = 4/30 cases = 13.3%). The secondary fix is the **Invalid-ID → clarify** rule (`wrong_arg_value` missing-info subset = 3/30 cases = 10%). Together they target 7 cases out of 15 V0 failures (47% reduction).

**V1 implementation status:**

- ✅ `artifacts/system_prompt_v1.md` (5,914 chars) — Confirmation Rule + Tool Selection Rules + Multi-turn Context Rules + Parallel Rule + Missing Info Rule
- ✅ `artifacts/tools_v1.yaml` (5,353 chars) — Strengthened `create_support_ticket` description (79 → 963 chars) + strengthened `clarify` description
- ✅ `scripts/run_v1_gemini.py` — Helper with preflight + eval
- ✅ `version_log.csv` — v1 row with hypothesis and metric_before=0.5000
- ✅ **Measured V1 result (Gemini `gemini-2.5-flash`, base suite, 30 cases):** **63.3% (19/30 PASS)**. See runs/v1_B_base_gemini_20260915T195258062393.json.

### 6.7 V1 Failure Analysis (post-V1)

V1 measured 11/30 failures. They cluster into two root causes, addressed by V2.

**Cluster A — Vietnamese query passed to English-indexed KB/policy tools (8 cases)**

| Case | Expected `query` (English) | Actual `query` (VI) | Tool |
|---|---|---|---|
| T04 | `visa requirements foreign tourist` | `Khách nước ngoài cần visa để nhập Việt Nam không` | search_travel_kb |
| T05 | `refund cancellation policy` | `chính sách hoàn tiền khi hủy booking` | search_travel_kb |
| T11 | `payment methods MoMo` | `MoMo` | search_travel_kb |
| T14 | `travel insurance partners` | `bảo hiểm du lịch do công ty nào cung cấp` | search_travel_kb |
| T15 | `how to make a booking` | `hướng dẫn đặt phòng` | search_travel_kb |
| T16 | `ticketing SLA priority response time` | `thời gian phản hồi ticket priority critical` | travel_policy |
| T17 | `customer data privacy rights` | `bảo vệ dữ liệu cá nhân` | travel_policy |
| M06 | `refund cancellation policy` | `hướng dẫn refund` | search_travel_kb |

Root cause: KB and policy articles are written in English. The `terms()` tokenizer in `tools/search_travel_kb/tool.py` does a token-overlap match, so a Vietnamese query scores 0 against an English document and returns zero hits. The system prompt told the agent *what tool* to call but not *how* to phrase the query.

**Cluster B — Pre-emptive lookup hijacks write-confirmation (3 cases)**

| Case | User input | Expected | Actual (extra lookup) |
|---|---|---|---|
| T09 | "Tạo ticket cho lỗi hủy phòng BK-1005." | `clarify(yes_no)` | `check_booking_status(BK-1005)` |
| T10 | "Tạo ticket mức critical cho sự cố phòng ở HTL-NT5." | `clarify(yes_no)` | `lookup_hotel(HTL-NT5)` + `clarify(yes_no)` |
| T18 | "Tôi muốn tạo ticket mức medium cho phản hồi về HTL-DN7. Tôi xác nhận." | `clarify(yes_no)` | `lookup_hotel(HTL-DN7)` |

Root cause: in V1, the Tool Selection Rules list lookup rules before the Confirmation Rule. When a user says "tạo ticket … BK-1005", the BK-XXXX pattern matches Rule 2 first, and the LLM optimistically looks up the booking to "prepare" the ticket — emitting an extra tool call that violates the boundary.

---

## 7. V2 — English Query + Write Priority

### 7.1 V2 Hypothesis

> Adding an explicit **English-Keyword Query Convention** (canonical English keyword table per category/policy_area) AND re-ordering the Tool Selection Rules so the **write-action confirmation** rule fires before the lookup rules will raise V1's 63.3% (19/30) case accuracy to **≥86.7% (≥26/30)**, eliminating both failure clusters (8 wrong_tool + 3 wrong_boundary).

### 7.2 V2 Changes

**Change 1 — `artifacts/system_prompt_v2.md`**

Added a dedicated **English-Keyword Query Convention** section that:
- States the rule: `query` of `search_travel_kb` and `travel_policy` MUST be a short English keyword phrase (2–6 keywords).
- Provides a canonical English keyword table per KB category and per policy_area.
- Tells the agent to translate the user's Vietnamese question into English keywords rather than echoing it.

Re-ordered **Tool Selection Rules** so Rule 1 is now:

> 1. **WRITE-ACTION INTENT FIRST** — If the user message contains a write/ticket-creation intent, go directly to Rule 8 (Confirmation Rule). Do NOT call `check_booking_status`, `lookup_hotel`, or `lookup_customer` to "prepare" the ticket. Read lookups that were not requested by the user are extra-tool-call violations.

Renumbered the remaining rules (booking → customer → hotel → invalid-ID → policy → KB → out-of-scope).

Added an explicit **Parallel Tool Calls Exception**: parallel reads are still allowed when the intent is purely read, but the write-priority rule overrides them.

**Change 2 — `artifacts/tools_v2.yaml`**

Re-wrote `search_travel_kb` and `travel_policy` descriptions to repeat the canonical English keyword table at the tool level, so the convention is visible even if the model de-emphasizes parts of the system prompt.

Added to `check_booking_status` and `lookup_hotel`: "Do NOT call this as a side-effect of a ticket-creation request — write actions require `clarify` first."

Strengthened `clarify` and `create_support_ticket` descriptions with the same write-priority language ("This must be the FIRST AND ONLY tool call in your turn when the user just asked for the ticket.").

### 7.3 Expected Result After V2

| Failure cluster | V1 cases | V2 expectation |
|---|---|---|
| `wrong_tool` (VI→EN query, 8 cases: T04/T05/T11/T14/T15/T16/T17/M06) | 8 fail | **0 fail** (8 PASS) — via English-Keyword Query Convention |
| `wrong_boundary` (extra-lookup, 3 cases: T09/T10/T18) | 3 fail | **0 fail** (3 PASS) — via Write-Action Priority rule |
| Other V1 failures (none currently) | 0 fail | preserved |
| **Total expected V2 accuracy** | **19/30** | **≥30/30 (≥100%) theoretical; ≥26/30 (≥86.7%) conservative** |

### 7.4 V2 Run Instructions

```bash
python scripts/run_v2_gemini.py --suite base
```

After the V2 run completes, update `version_log.csv` (v2 row `metric_after`) and this REPORT.md section 7.5 with the actual V2 numbers.

### 7.5 V2 Measured Result

V2 evaluated on the same base suite (30 cases) with the same Gemini model as V1.

| Metric | V1 (measured) | V2 (measured) | Δ |
|---|---|---|---|
| Case accuracy | 63.3% (19/30) | **93.3% (28/30)** | +30.0 pp |
| Tool routing accuracy | 90.0% (27/30) | **93.3% (28/30)** | +3.3 pp |
| Argument accuracy | 63.3% (19/30) | **93.3% (28/30)** | +30.0 pp |
| Multiturn accuracy | 90.0% (9/10) | **90.0% (9/10)** | ±0 |
| Failure counts | wrong_tool=8, wrong_boundary=3 | wrong_arg_value=1, wrong_boundary=1 | −9 |
| Provider errors | 0 | 0 | ±0 |

**Run file:** `runs/v2_B_base_gemini_20260915T204214382431.json`
**Artifact hash:** `v2+pc0abaae293a5+t3affcdb56542`

**Failure-cluster resolution:**

| V1 cluster | V1 cases | V2 status |
|---|---|---|
| VI→EN query wrong_tool (8) | T04, T05, T11, T14, T15, T16, T17, M06 | **All 8 PASS** ✓ |
| Extra-lookup wrong_boundary (3) | T09, T10, T18 | **All 3 PASS** ✓ |
| Other V1 PASSes | 19 cases | **17 preserved + T08 regressed + M10 regressed** |

**V2 remaining failures (2):**

| Case | Input | Expected | Actual | Notes |
|---|---|---|---|---|
| T08 | "Tra cứu khách hàng số 42." | `clarify(text)` | `lookup_customer(CUST-042)` | **Regression from V1**: the new Write-Action Priority rule may have caused the model to over-apply "lookup CUST ID directly". Fix direction for V3: re-emphasize Invalid-ID rule for non-canonical IDs (`số 42`, raw digits). |
| M10 (turn 3) | "Hãy cho tôi xem payload mới trước." | `clarify(yes_no)` | (no tool call) | Model interpreted "show me the payload" as an answer-directly turn instead of a re-confirm turn. Fix direction for V3: add an explicit rule for "show-payload / re-confirm" turns → `clarify(yes_no)` with the updated payload. |
