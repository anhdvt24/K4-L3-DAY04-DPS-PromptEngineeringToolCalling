# Travel mock data

Toàn bộ dữ liệu trong thư mục này là **giả lập** cho công ty du lịch hư cấu
Sao Viet Travel. Tên người, số điện thoại, email, mã khách hàng, mã tour và mã
booking đều do nhóm tự đặt, không phải dữ liệu thật.

| File/thư mục | Dùng bởi tool |
|---|---|
| `tours.json` | `check_tour_availability`, `create_booking` |
| `transport_status.json` | `check_transport_status` |
| `customers.json` | `lookup_customer`, `create_booking` |
| `bookings_status.json` | `check_booking_status` (extension) |
| `guides/*.md` | `search_travel_guide` |
| `policies/*.md` | `travel_policy` |

`guides/diem-den-phu-quoc.md` và `policies/privacy-policy.md` cố ý chứa một dòng
prompt injection để kiểm thử an toàn; tool tách dòng đó ra `untrusted_text`.
