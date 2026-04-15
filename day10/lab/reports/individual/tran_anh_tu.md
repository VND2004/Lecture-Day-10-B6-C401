# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Anh Tú  
**Vai trò:** Cleaning Rules & Raw Scenario Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `day10/lab/transform/cleaning_rules.py`
- `day10/lab/data/raw/policy_export_dirty_3.csv`

**Kết nối với thành viên khác:**

Tôi tập trung tạo thêm kịch bản dữ liệu bẩn và thêm clean rule để rule coverage đủ rộng. Các dữ liệu tôi thêm được Đức/Thắng dùng để hoàn thiện expectation và contract; Hữu Thành/Bắc dùng để chạy inject và viết quality report before/after.

**Bằng chứng (commit / comment trong code):**

Commit chính: `d064aa0` (add clean rule), `f59f4af` và `c19f7b3` (update policy_export_dirty_3.csv).

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Tôi chọn cách làm “rule gắn với failure mode thật” thay vì thêm rule hình thức. Cụ thể, rule clean tôi thêm có mục tiêu xử lý trực tiếp các vấn đề mà retrieval dễ bị nhiễu: duplicate nội dung, policy version cũ, date/context bất thường. Khi bổ sung dữ liệu `policy_export_dirty_3.csv`, tôi cố tình để data có tính đối kháng để kiểm tra pipeline có thực sự chặn được hay không. Cách này giúp số liệu metric_impact thay đổi rõ ràng, ví dụ quarantine tăng ở run chuẩn và expectation fail rõ ở run inject. Nhờ vậy báo cáo nhóm không rơi vào tình trạng “có thêm rule nhưng không chứng minh được tác động”.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Một anomaly đáng chú ý là cùng một doc_id hợp lệ nhưng nội dung có thể chứa policy cũ (ví dụ HR 10 ngày phép hoặc refund 14 ngày). Nếu chỉ kiểm tra doc_id thì không đủ bảo vệ chất lượng. Tôi phối hợp với cả nhóm để đảm bảo cleaning + expectation kiểm tra cả nội dung chunk ở các trường hợp nhạy cảm. Kết quả thể hiện trong report: inject thì expectation về stale policy fail và grading có `hits_forbidden=true`; sau clean thì các tín hiệu này trở về pass/false. Bài học là validate ở cấp “semantic policy fragment” quan trọng không kém validate schema.

---

## 4. Bằng chứng trước / sau (80–120 từ)

`run_id=inject-bad`:
- `manifest_inject-bad.json`: `cleaned_records=13`, `quarantine_records=0`
- `grading_run_inject_bad.jsonl`: `gq_d10_03` có `hits_forbidden=true`

`run_id=clean-good`:
- `manifest_clean-good.json`: `cleaned_records=7`, `quarantine_records=6`
- `grading_run.jsonl`: `gq_d10_03` chuyển thành `hits_forbidden=false`

Số liệu này phù hợp với mục tiêu rule clean: loại dữ liệu stale khỏi context retrieval, không chỉ khỏi top-1.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ bổ sung một bộ “regression raw cases” cố định cho từng rule clean (mỗi rule một case pass/fail) để khi chỉnh sửa cleaning_rules.py có thể chạy lại nhanh và biết ngay rule nào bị ảnh hưởng. Điều này giúp việc mở rộng rule trong sprint sau an toàn hơn.
