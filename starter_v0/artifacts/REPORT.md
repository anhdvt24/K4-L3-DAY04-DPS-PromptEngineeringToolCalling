# Day 04 Lab v3 Report — Trợ lý du lịch Sao Viet Travel

- Lĩnh vực tự chọn: **Du lịch** — trợ lý tư vấn và đặt tour cho công ty lữ hành hư cấu Sao Viet Travel (dữ liệu giả lập).
- Nhiệm vụ và luồng cơ bản đã chốt trước v0: khách hỏi tour/chuyến đi → trợ lý tra chỗ trống tour, tình trạng phương tiện, cẩm nang, chính sách hoặc hồ sơ khách → hỏi lại khi thiếu thông tin → tóm tắt và hỏi xác nhận yes/no → chỉ khi khách xác nhận đúng nội dung mới gọi `create_booking(confirmed=true)`. Tìm kiếm web (Tavily) chỉ nhận truy vấn công khai.
- Đường dẫn bộ 30 câu cơ bản và 12 câu an toàn: [`data/eval_travel_base.json`](../data/eval_travel_base.json) (20 một lượt + 10 nhiều lượt), [`data/eval_travel_adversarial.json`](../data/eval_travel_adversarial.json) (12 câu). Commit chốt bộ trước v0: `37be8d7`.
- Chức năng mở rộng ngoài luồng cơ bản: **tra tình trạng đặt chỗ** `check_booking_status(booking_code, customer_id)` có xác minh chủ booking; kiểm thử ở [`data/eval_travel_extension.json`](../data/eval_travel_extension.json) và [`scripts/smoke_travel_tools.py`](../scripts/smoke_travel_tools.py).

## Team

- Team: TBD
- Thành viên và INDIVIDUAL: [TEAM.md](../../TEAM.md)
- Members: TBD
- Provider/model: Gemini `gemini-3.5-flash-lite` (free tier, temperature 0)

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Trợ lý tra cứu tour, chỗ trống, tình trạng chuyến bay/tàu/xe/tàu cao tốc, cẩm nang và chính sách công ty trên dữ liệu giả lập, và tạo booking cục bộ chỉ sau khi khách xác nhận đúng nội dung. Giới hạn: dữ liệu là snapshot tĩnh (không có giá/lịch thật), không thanh toán, không nhận số thẻ/OTP/giấy tờ; tìm kiếm web cần `TAVILY_API_KEY` và không gửi mã khách hàng, mã booking hay mã tour ra ngoài.

**Link dùng thử:**

> URL: chạy cục bộ `streamlit run ui.py` trong `starter_v0` (xem README).

## A2. Tool agent có

| Tool | Chức năng | Core / optional / team-built |
|---|---|---|
| clarify | Hỏi bổ sung hoặc xác nhận | core |
| search_travel_guide | Tìm cẩm nang nội bộ (visa, hành lý, điểm đến, sức khỏe, thanh toán) | team-built (core của lĩnh vực) |
| check_tour_availability | Chỗ trống, trạng thái và giá ước tính của một ngày khởi hành | team-built (core) |
| check_transport_status | Tình trạng máy bay/tàu/xe/tàu cao tốc theo chặng | team-built (core) |
| lookup_customer | Hồ sơ khách hàng giả lập (liên hệ đã che) | team-built (core) |
| travel_policy | Chính sách hủy, hoàn tiền, trẻ em, dữ liệu, đặt tour, công cụ ngoài | team-built (core) |
| create_booking | Tạo booking cục bộ; cần `confirmed=true`, chặn số thẻ/CVV/OTP/giấy tờ | team-built (core, action) |
| search_travel_info | Tìm web qua Tavily; chặn mã nội bộ và dữ liệu nhạy cảm trước khi gửi | optional (external) |
| check_booking_status | Tra tình trạng booking khi có cả mã booking và mã khách đúng chủ | team-built (bonus) |

## A3. Câu hỏi mẫu

1. Tour TOUR-PQ02 ngày 08/11/2026 còn chỗ cho 3 người không, chuyến bay HAN-PQC hôm nay có trễ không?
2. Đặt tour TOUR-DL01 ngày 2026-10-20 cho 2 người, khách KH-1001. (→ hỏi xác nhận, trả lời "có" → tạo booking)
3. Booking BK-7790 của KH-1002 bị công ty hủy, kiểm tra tình trạng và chính sách hoàn tiền.

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Cải thiện version | Fallback run/transcript |
|---|---|---|---|
| TBD | TBD | TBD | TBD |

# PHẦN B — Chi tiết và evidence

Metric chỉ hợp lệ khi `provider_error_cases == 0`, `measured_cases ==
total_cases`, và tool result error đã được review thủ công.

Lần chạy v0 đầu tiên bị lỗi 429 (quota free tier 15 request/phút) do chạy hai suite song song; hai file đó được giữ ở [`runs/invalid/`](../runs/invalid/) và **không** dùng làm evidence. Provider Gemini được sửa để chờ `retryDelay` rồi thử lại.

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric | Before | After | Run file |
|---|---|---|---|---:|---:|---|
| v0 | baseline | Đo hành vi trước khi sửa | case_accuracy (base) | – | 0.80 | [v0 base](../runs/v0_B_base_gemini_20260915T201829636279.json) |
| v1 | TBD |  |  |  |  |  |
| v2 | TBD |  |  |  |  |  |
| v3 | TBD |  |  |  |  |  |

## B2. Failure analysis

| Case ID | Failure type | Actual calls | What failed | Fix |
|---|---|---|---|---|
| TBD |  |  |  |  |

## B3. Team eval cases

Liệt kê đúng 10 case tự viết: 5 single-turn và 5 multi-turn ([`data/eval_group.json`](../data/eval_group.json)).

| Case ID | What it tests | Expected behavior | Result |
|---|---|---|---|
| G01_cancelled_departure | Ngày khởi hành đã hủy vẫn phải tra tool | `check_tour_availability` TOUR-HL05, 2026-11-01, 2 | TBD |
| G02_payment_guide_category | Category payment của cẩm nang | `search_travel_guide` category payment | TBD |
| G03_bus_mode | "Xe khách" → mode bus | `check_transport_status` bus, HAN-SPA | TBD |
| G04_change_date_policy_area | Đổi ngày nằm trong chính sách cancellation | `travel_policy` cancellation | TBD |
| G05_web_hotel_search | Khách sạn bên ngoài → web search | `search_travel_info` category hotel | TBD |
| GM01_update_guest_count | Cộng thêm khách ở lượt sau | `check_tour_availability` guests 3 | TBD |
| GM02_answer_mode_choice | Dùng lựa chọn khách vừa trả lời | `check_transport_status` train, HAN-SGN | TBD |
| GM03_genuine_confirmation | Xác nhận thật đúng nội dung → ghi | `create_booking` confirmed=true | TBD |
| GM04_decline_at_confirmation | Từ chối ở bước xác nhận | `travel_policy` cancellation, không đặt | TBD |
| GM05_privacy_safe_web_search | Web search không mang dữ liệu khách | `search_travel_info` category food; review query | TBD |

## B4. Live chat evidence

| Scenario/turn | Version | Tool calls + args | Transcript/run | Outcome |
|---|---|---|---|---|
| TBD |  |  |  |  |

## B4a. Adversarial evidence

Phân tích ít nhất 3 cases. Automatic score không chứng minh rằng không có dữ
liệu bị ghi hoặc gửi ra ngoài; cần kiểm tra cả `tool_results` và filesystem.

| Attack case | Expected boundary | Actual calls | Sensitive write/exfiltration occurred? | Outcome |
|---|---|---|---|---|
| TBD |  |  |  |  |

## B5. Optional và bonus tool evidence

| Category | Evidence file | What worked | Risk / guardrail |
|---|---|---|---|
| Optional built-in | – | Không dùng tool IT optional | – |
| External search + privacy boundary | [`tools/search_travel_info/tool.py`](../tools/search_travel_info/tool.py), case T06, S06, S12, GM05 | TBD | Chặn `KH-xxxx`, `BK-xxxx`, `TOUR-xx00`, số thẻ/OTP trước khi gọi Tavily; `TAVILY_API_KEY` trống nên kết quả thật trả `missing_api_key` |
| Bonus: tool mới do nhóm tự xây | [`tools/check_booking_status/`](../tools/check_booking_status/), [`data/eval_travel_extension.json`](../data/eval_travel_extension.json) | TBD | Cần cả mã booking và mã khách; sai chủ và mã không tồn tại trả cùng một lỗi nên không dò được booking người khác |

## B6. Safety review

- Agent có bao giờ tự đoán tour ID hoặc customer ID không? TBD
- Trace/booking có chứa số thẻ, OTP, mật khẩu hay dữ liệu thật không? TBD
- Booking chỉ được tạo sau xác nhận rõ chưa? TBD
- Tool result error nào cần review thủ công? TBD

## B7. Technical reflection

- Fix nào thuộc `system_prompt.md`? TBD
- Fix nào thuộc `tools.yaml`? TBD
- Failure nào không thể chỉ nhìn automatic score? TBD
- Nếu có thêm một vòng, nhóm sẽ thử hypothesis nào? TBD

# PHẦN C — Checkout trước khi nộp

Phần này được hoàn thành sau khi toàn bộ code, evidence và report đã được đưa
lên repository chung. Nhóm chưa nên nộp link trên VLearn nếu reflection hoặc
commit evidence của bất kỳ thành viên nào còn thiếu.

## C1. Nhận xét chung của nhóm

Hoàn thành mục nhận xét chung trong [TEAM.md](../../TEAM.md). Dẫn tới các run, file và commit trong phần B để chứng minh kết quả. Ghi dưới đây đường dẫn tới mục đã hoàn thành:

> Link:

## C2. INDIVIDUAL của từng thành viên

Mỗi người tự viết và commit mục INDIVIDUAL của mình trong [TEAM.md](../../TEAM.md), nêu phần việc, bằng chứng kỹ thuật và điều đã học. Không yêu cầu chép lại cùng nội dung ở đây. Mỗi mục phải có file/commit/PR thật, không dùng commit tự đánh giá làm bằng chứng kỹ thuật duy nhất.

> Link các mục INDIVIDUAL:

## C3. Final checkout

Chỉ nộp bài khi mọi mục dưới đây đã được kiểm tra trên branch cuối cùng của
repository chung:

- [ ] `TEAM.md` có đủ họ tên, MSSV, GitHub username và vai trò.
- [ ] Mỗi thành viên có ít nhất một commit trong lịch sử branch nộp bài.
- [ ] Phần nhận xét chung trong TEAM.md đã hoàn thành và có evidence.
- [ ] Mỗi thành viên đã tự viết và commit mục INDIVIDUAL trong TEAM.md.
- [ ] `system_prompt.md`, `tools.yaml`, version log, runs, eval, transcript, UI
      và report đã có trong repository.
- [ ] Không có `.env`, API key, token, dữ liệu thật, cache hoặc generated ticket.
- [ ] Nhóm trưởng và mọi thành viên đã thống nhất đúng một URL repository chung.
- [ ] Nhóm trưởng và mọi thành viên sẽ nộp cùng URL đó trên VLearn.

**URL repository chung dùng để nộp:**

> URL:

- [ ] Tên repo đúng mẫu K4-L3-DAY04-HoVaTen-MSSV-PromptEngineeringToolCalling.
- [ ] Kiểm tra deadline và bản chốt theo [SUBMISSION.md](../../SUBMISSION.md).
