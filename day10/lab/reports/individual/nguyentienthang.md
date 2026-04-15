# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Tiến Thắng  
**Vai trò:** Cleaning Rules / Data Contract / Architecture Docs  
**Ngày nộp:** 2026-04-15  

---

## 1. Tôi phụ trách phần nào? 

**File / module:**

- `day10/lab/transform/cleaning_rules.py`
- `day10/lab/contracts/data_contract.yaml`
- `day10/lab/docs/data_contract.md`
- `day10/lab/docs/pipeline_architecture.md`
- `day10/lab/data/raw/policy_export_dirty_1.csv`

**Kết nối với thành viên khác:**

Tôi làm phần chuẩn hóa luật dữ liệu và contract để các thành viên khác chạy pipeline nhất quán. Dữ liệu raw từ Đức/Tú được tôi map vào rule clean và schema contract, sau đó bàn giao cho Hữu Thành/Bắc chạy expectation, eval và quality report.

**Bằng chứng (commit / comment trong code):**

Commit chính: `28b935f`, `1fe0f5a`, `524ed79`, `5ed24e1`, `aef6330`.

---

## 2. Một quyết định kỹ thuật 

Quyết định tôi chọn là đồng bộ chặt giữa logic clean và data contract thay vì để contract chỉ mang tính mô tả. Trong `data_contract.yaml`, tôi khai báo các expectation quan trọng với severity `halt` như allowlist, refund stale window, date validity, chronology, stale HR annual leave. Điều này buộc pipeline phải “fail fast” nếu dữ liệu làm lệch chính sách nghiệp vụ. Đồng thời tôi bổ sung tài liệu kiến trúc/contract để đội có chung ngôn ngữ: field nào bắt buộc, lý do quarantine, canonical source nào là chuẩn. Nhờ cách này, khi có câu hỏi “vì sao row bị loại?” thì có thể truy ngược từ quarantine reason sang rule và sang contract, giảm tranh luận cảm tính.

---

## 3. Một lỗi hoặc anomaly đã xử lý 

Lỗi điển hình tôi xử lý là dữ liệu ngày hiệu lực “nhìn giống đúng” nhưng thực tế sai lịch (ví dụ 2026-02-30) hoặc sai chronology (`exported_at < effective_date`). Nếu chỉ dùng regex thì những case này có thể lọt qua và gây sai versioning. Tôi phối hợp bổ sung rule parse lịch thực + chronology trong clean/expectation để bắt đúng lỗi. Trong quality report, các lỗi này thể hiện rõ ở run inject: `effective_date_calendar_valid` fail và `exported_not_before_effective` fail; sau khi chạy clean-good thì pass. Đây là điểm quan trọng vì policy/version phụ thuộc trực tiếp vào timeline dữ liệu.

---

## 4. Bằng chứng trước / sau 

`run_id=inject-bad` (trước):
- `manifest_inject-bad.json`: `cleaned_records=13`, `quarantine_records=0`
- Expectation summary trong `docs/quality_report.md`: `effective_date_calendar_valid FAIL`, `exported_not_before_effective FAIL`

`run_id=clean-good` (sau):
- `manifest_clean-good.json`: `cleaned_records=7`, `quarantine_records=6`
- `docs/quality_report.md`: hai expectation trên chuyển sang `OK`

Bằng chứng này xác nhận rule về date/chronology không chỉ “đẹp code” mà tạo tác động định lượng.

---

## 5. Cải tiến tiếp theo 

Nếu có thêm 2 giờ, tôi sẽ tách `data_contract.yaml` thành phần “business policy constraints” và “technical schema constraints”, rồi thêm script kiểm tra contract drift tự động khi thay đổi cleaning rule. Việc này giúp tránh trường hợp rule mới được thêm vào code nhưng chưa cập nhật contract, gây lệch giữa vận hành và tài liệu.