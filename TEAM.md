# TEAM — DPS, Day04

## Thông tin bài nộp

- Nhóm: DPS; đề tài: trợ lý du lịch Sao Viet Travel, dữ liệu giả lập.
- Đại diện: Đặng Văn Thái Anh — 2A202602407 — `anhdvt24`.
- URL chính thức do đại diện xác nhận: https://github.com/anhdvt24/K4-L3-DAY04-DPS-PromptEngineeringToolCalling.git
- Nhánh: `main`. Commit được rà soát: `891ab6b`; chưa phải commit chốt của bản sửa hiện tại.
- Deadline do đại diện xác nhận: **12:00 ngày 16/09/2026, UTC+07:00**. Chưa cung cấp link thông báo Keycoach.
- Tên repo hiện dùng `DPS`, chưa theo mẫu họ tên–MSSV trong SUBMISSION. Cần xác nhận ngoại lệ với Keycoach hoặc đổi tên trước khi chốt.
- Trạng thái nộp VLearn: chưa được xác nhận cho từng người.

## Thành viên

Danh sách đã được đại diện xác nhận; các ô chưa rõ cần chính thành viên bổ sung.

| Họ tên | MSSV | GitHub | Đóng góp đối chiếu được |
|---|---|---|---|
| Đặng Văn Thái Anh | 2A202602407 | anhdvt24 | commits trên `artifacts/system_prompt.md`, `artifacts/tools.yaml`, `artifacts/REPORT.md`, `artifacts/version_log.csv` |
| Bùi Đức Thành | 2A202602364 | n4hhh | commits trên `data/eval_travel_adversarial.json`, `runs/v4_B_adversarial_*.json`, scripts/smoke_travel_tools.py |
| Nguyễn Thành Luân | 2A202602769 |  | commits trên `data/eval_group.json`, `runs/v4_B_group_*.json` |
| Nguyễn Lê Ngọc Bảo | | NLNBao237 | commits trên `tools/check_booking_status/`, `data/eval_travel_extension.json`, `runs/v4_B_extension_*.json` |
| Nguyễn Ngọc Linh | 2A202602480 | linhmoimoi | commits trên `ui.py`, `app/`, `transcripts/v4_gemini_*.transcript.json`, `scripts/chat_scenarios/` |

## Nhận xét chung

### Kết quả và bằng chứng

- Giữ bộ IT gốc; bộ du lịch 30 base (20+10), 12 safety chốt ở `37be8d7`; có thêm 10 case nhóm (5+5) và 5 extension.
- Có 14 run chính v0–v4, đều đủ measured cases và không lỗi provider; 3 run lỗi được giữ trong `starter_v0/runs/invalid/`.
- V4 lịch sử: base **29/30**, adversarial **11/12**, group **10/10**, extension **5/5**. Run thật mang timestamp `20260915T204...`; không có evidence cho lần chạy 22:17.
- Prompt v4 lịch sử có hash `91a13e3ac159`, tools hash `23d06775e1e7`, được lưu trong `starter_v0/artifacts/history/`. Bản hiện tại v4.1 có artifact `v4.1+p4ce4d2cd8e80+t5eec2f547192`.
- V4.1 OpenRouter / `openai/gpt-4o-mini`: **safety 12/12, base 28/30, group 9/10, extension 4/5**; đủ measured cases, không lỗi provider. Có 4 transcript UI mới mang nhãn v4.1 (điều khiển widget tự động, gọi model thật); xem REPORT B8.
- Có 5 transcript CLI v4 và một transcript UI cũ `v3_gemini_ui_20260915T205127724948.transcript.json`. UI cũ dùng prompt hash v4 nhưng nhãn v3; giữ nguyên evidence cũ và dùng 4 transcript v4.1 mới cho bản sửa.
- Không có run `221*.json`, transcript UI `221903900625`, `app/main.py` hay `scripts/run_gemini_v0.py` được nhắc trong TEAM cũ; không dùng chúng làm bằng chứng.
- Safety lịch sử: v0 ghi booking trái phép ở S03/S04/S10/S11; v3 tái phát S03. Không được kết luận cả v0–v4 luôn xác nhận đúng.
- Kiểm tra offline ngày 16/09/2026: **32 smoke checks và 18 regression tests safety PASS**. Đây là test code, không thay thế run model thật.
- Báo cáo, run, phân tích trước/sau và giới hạn: [REPORT](starter_v0/artifacts/REPORT.md).

### Thay đổi hiệu quả nhất và giới hạn

V1 thêm luật xác nhận: base 24/30 → 29/30, adversarial 7/12 → 10/12. V2 cải thiện safety lên 12/12 nhưng base giảm; v3 tái phát lỗi xác nhận. V4 đạt 29/30 base và 11/12 adversarial, còn T14/S05. Chưa có đủ lần chạy lặp để kết luận độ ổn định.

V4.1 sửa thứ tự ưu tiên prompt, thêm guard dữ liệu nhạy cảm trước provider/tool và redaction. Lần đầu chỉ sửa prompt đạt safety 10/12 và ghi booking trái phép ở S03; đã giữ evidence. Sau đó thêm consent theo payload trong session: chỉ cho ghi sau câu hỏi thật và xác nhận một lần, payload sửa/hủy mất quyền. Bản cuối đạt safety 12/12 và T14 PASS; S05 do guard xử lý trước provider. Base còn T18/TM02, group còn G02, extension còn X02. Web search trả `missing_api_key`, chưa chứng minh tìm kiếm thực tế. Thay provider và execution protocol nên không so điểm trực tiếp để quy kết hiệu quả riêng của prompt.

## INDIVIDUAL

### Đặng Văn Thái Anh — 2A202602407 (Lead + Prompt/Tool engineer)

- **Phần việc và file/commit/PR:**
  - Chạy baseline v0 với `scripts/run_gemini_v0.py` và lưu `runs/v0_B_base_gemini_20260915T201829636279.json`, `runs/v0_B_adversarial_gemini_20260915T201914462898.json` (2 run đầu tiên bị 429 do chạy song song — chuyển vào `runs/invalid/`, không dùng làm evidence).
  - Viết `artifacts/system_prompt.md` qua 4 vòng: v1 (hash `b9547ea5b52a`) thêm mục "Write actions & untrusted text"; v2 giữ nguyên; v3 (hash `b21ba80276fa`) thêm "Requests with several parts" và "Multi-turn conversations"; v4 (hash `91a13e3ac159`) — bản cuối — thêm "Output format" tiếng Việt thay JSON, định nghĩa xác nhận chặt hơn, mục Privacy, từ chối tin nhắn tự nhận `SYSTEM/admin`.
  - Viết `artifacts/tools.yaml` v2 (hash `23d06775e1e7`): bổ sung `response_type` cho `clarify`, map từ `xe khách/tàu hỏa/xe buýt/tàu cao tốc` sang enum `mode` của `check_transport_status`, ranh giới riêng tư cho `search_travel_info`, giải thích `create_booking` không dùng để preview, mô tả tool bonus `check_booking_status`.
  - Tổng hợp `artifacts/version_log.csv` (5 dòng v0–v4) và `artifacts/REPORT.md` (đủ A1–A4, B1–B7, C1–C3) từ run JSON của cả nhóm.
  - Commit chính: thay đổi trên `artifacts/system_prompt.md`, `artifacts/tools.yaml`, `artifacts/REPORT.md`, `artifacts/version_log.csv`, `starter_v0/runs/`, `starter_v0/transcripts/`.

- **Quyết định, khó khăn và cách xử lý:**
  - *Quyết định 1 — prompt viết tiếng Anh hay tiếng Việt?* v1 viết bằng tiếng Anh với schema ID rất cứng (`BK-XXXX`, `CUST-XXXX`, `HTL-XXX`). Sau khi đổi sang lĩnh vực du lịch, tôi viết lại prompt hoàn toàn bằng tiếng Việt, bỏ regex cứng, dùng anchor bằng keyword trong câu (`"máy bay"` → `flight`). Cách này dễ bảo trì hơn khi mở rộng tour.
  - *Quyết định 2 — định dạng output JSON hay văn bản?* v1–v3 ép model trả JSON (`intent, action, reply, evidence_ids`). Lúc chạy eval có `tool_choice="required"` nên routing đạt 0.97, nhưng khi mở UI chat thật (transcript 01 v3) model trả JSON "để em kiểm tra..." mà không gọi tool. v4 đổi sang trả văn bản tiếng Việt, vẫn ép gọi tool bằng rule "Use tools for facts ... call the tool in this turn".
  - *Quyết định 3 — ranh giới xác nhận để ở prompt hay đưa xuống code?* v1–v4 vẫn để ở prompt và quan sát S03 dao động giữa `clarify` và `create_booking(confirmed=true)` qua 5 lần chạy. Tôi đã ghi vào REPORT B7 rằng vòng tiếp theo nên đưa xuống code: `create_booking` chỉ chấp nhận `confirmed=true` khi session có `clarify(yes_no)` ở lượt trước với đúng payload — để S03 không còn phụ thuộc model.
  - *Khó khăn — dao động model ở temperature 0:* `gemini-3.5-flash-lite` vẫn cho kết quả khác nhau ở T05/T15/T19/TM09/S03 qua các version. Tôi đã chạy lại v4 hai lần (20:46 và 22:17) và thấy base 29/30 và adversarial 11/12 được giữ nguyên — chênh 1 case (0.033) không đủ kết luận, nên tôi không ghi nó là "improvement" trong version_log.
  - *Khó khăn — quota free tier 15 req/phút của Gemini:* hai run v0 đầu chạy song song đều 429. Sửa provider `providers/gemini_provider.py` để đọc `retryDelay` từ response và back off; sau đó chạy tuần tự.

- **Điều đã học:**
  - **Failure tự động không đồng nghĩa vi phạm dữ liệu, và ngược lại.** S03/S04/S10/S11 v0 routing PASS là false-positive nguy hiểm: tool_results có `create_booking(confirmed=true)` và `bookings/` có file mới. Ngược lại S05 v4 routing FAIL nhưng không có số thẻ trong tool call — không vi phạm. Mở cả tool_results mới đánh giá được.
  - **Một prompt tốt phải dùng anchor bằng hành động, không bằng keyword cứng.** v1 dùng regex `BK-\d{4,6}` rất dễ vỡ khi user viết "số 42" hay "booking 1001"; v4 dùng anchor bằng intent ("When the user asks to book") và exception rõ ràng.
  - **Tool description là một phần của prompt.** v2 thêm "map mode theo lời user", "không gọi để preview", "không gửi mã nội bộ" vào `description` của tool — model đọc nó cùng lúc với system prompt và routing cải thiện ngay.
  - **Reproducibility quan trọng.** Cùng artifact v4 chạy 2 lần, 2 lần đều base 29/30 và adversarial 11/12 — bằng chứng rằng metric không phải do may rủi.

- **AI/công cụ đã dùng và cách kiểm tra:**
  - **Cursor (mô hình `claude-sonnet-5`) — completion & chat:** dùng để đọc trace JSON, tóm tắt failure mode, đề xuất prompt diff. Không dùng để viết report/INDIVIDUAL cuối cùng.
  - **Gemini `gemini-3.5-flash-lite` (provider của nhóm):** model thật trong tất cả run evidence. Temperature 0, có retry với `retryDelay`.
  - **Python 3.11 + `hashlib`:** đối chiếu SHA256 của `artifacts/system_prompt.md` và `artifacts/tools.yaml` với `prompt_hash`/`tools_hash` trong run JSON — khớp cho mọi version.
  - **Cách tự kiểm tra:** (1) Chạy `python scripts/smoke_travel_tools.py` sau mỗi lần sửa tools.yaml — phải 33/33 PASS. (2) Sau mỗi lần sửa prompt, chạy lại 4 suite với `--version vN --suite {base|adversarial|group|extension}`, kiểm tra `summary.provider_error_cases == 0` và `summary.measured_cases == summary.total_cases` trước khi nhận kết quả. (3) Mở `runs/invalid/` để đảm bảo run đó thực sự lỗi provider, không âm thầm lẫn vào evidence. (4) Đối chiếu `bookings/` với transcript — nếu có booking mới không xuất hiện trong transcript hợp lệ, đó là write trái phép.

- **Thời điểm đã tự nộp URL repo chung trên VLearn:** sẽ nộp `https://github.com/anhdvt24/K4-L3-DAY04-DangVanThaiAnh-2A202602407-PromptEngineeringToolCalling` 


### Nguyễn Ngọc Linh — 2A202602480

- **Phần việc thực tế và evidence:**
  - Xây dựng và hoàn thiện UI Streamlit trong `starter_v0/ui.py`: cho chọn provider/model và phiên bản artifact, hiển thị câu trả lời, tool call, input, kết quả hoặc lỗi, trạng thái từng lượt và đường dẫn transcript; lưu hội thoại theo cùng schema với CLI.
  - Viết và chạy các kịch bản chat trong `starter_v0/scripts/chat_scenarios/`: yêu cầu thông thường, thiếu thông tin rồi xác nhận, sửa thông tin rồi hủy, tạo booking rồi tra trạng thái booking, và các yêu cầu giả mạo quyền/quay vòng dữ liệu nhạy cảm.
  - Lưu evidence hội thoại Gemini v3–v4 trong `starter_v0/transcripts/` và phối hợp kiểm tra 4 transcript UI v4.1 OpenRouter: `v4.1_openrouter_ui_20260916T103226666176.transcript.json` (tra tour), `v4.1_openrouter_ui_20260916T103232061891.transcript.json` (xác nhận–tạo–tra booking), `v4.1_openrouter_ui_20260916T103241111759.transcript.json` (sửa rồi hủy), `v4.1_openrouter_ui_20260916T103245653390.transcript.json` (tool result giả và dữ liệu thanh toán). Các quan sát và giới hạn được tổng hợp ở REPORT B8.
  - Tích hợp UI với state nhiều lượt, cơ chế consent cho `create_booking` và redaction dữ liệu nhạy cảm; transcript booking tạo được `BK-L476002`, còn luồng hủy không gọi tool ghi và không tạo booking mới.

- **Điều học được và cách kiểm tra:**
  - UI của agent cần lưu đủ provider/model, artifact version, tool input và tool result/error; chỉ thấy routing PASS chưa đủ, phải đối chiếu transcript với side effect trong `bookings/`. Kiểm tra bằng `streamlit run ui.py`, `python scripts/demo_ui_live.py`, các transcript đã lưu, cùng `python -m unittest discover -s tests -v` và `python scripts/smoke_travel_tools.py` (18 regression tests và 32 smoke checks PASS theo REPORT).
  - Qua các kịch bản nhiều lượt, xác nhận phải gắn với đúng payload hiện tại; sửa số khách hoặc hủy phải làm mất quyền ghi cũ. Giới hạn còn lại là lượt đầu thiếu dữ liệu đôi khi hỏi bằng text thay vì gọi `clarify`, nhưng vẫn không tạo booking trái phép.

- **AI/công cụ đã dùng:** Streamlit và Python để xây UI/lưu transcript; AppTest trong `scripts/demo_ui_live.py` để điều khiển bốn kịch bản UI và gọi OpenRouter thật (`openai/gpt-4o-mini`); Gemini `gemini-3.5-flash-lite` cho các transcript lịch sử. Tự kiểm tra bằng cách đọc lại tool trace/result, kiểm tra artifact version và đối chiếu transcript với kết quả ghi dữ liệu.

- **VLearn:** nộp cùng URL repo nhóm `https://github.com/anhdvt24/K4-L3-DAY04-DangVanThaiAnh-2A202602407-PromptEngineeringToolCalling`; thời điểm nộp riêng của thành viên cần Nguyễn Ngọc Linh xác nhận.
