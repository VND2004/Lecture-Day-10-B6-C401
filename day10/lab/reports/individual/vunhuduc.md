# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Vũ Như Đức  
**Vai trò:** Ingestion / Raw Data Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `day10/lab/data/raw/policy_export_dirty_add_extra.csv`
- `day10/lab/data/raw/policy_export_dirty_2.csv`
- `day10/lab/quality/expectations.py`

**Kết nối với thành viên khác:**

Tôi chịu trách nhiệm chuẩn bị dữ liệu raw có đủ case lỗi để đội clean/quality kiểm thử được tác động thật của rule. Dữ liệu tôi thêm là đầu vào để Tú/Thắng cập nhật cleaning rules và để Thành/Hữu Thành chạy before-after retrieval. Tôi cũng điều chỉnh expectation để phản ánh đúng các case đã inject.

**Bằng chứng (commit / comment trong code):**

Các commit chính: `c08335a` (add extra data), `f848578` (add raw dirty), `31bd8d1` (update expectation), `77690c4` (dọn artifact thừa).

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định kỹ thuật của tôi là mở rộng dataset raw theo hướng “có chủ đích gây lỗi observability”, thay vì chỉ thêm dữ liệu hợp lệ. Tôi thêm các dòng tạo ra nhiều failure mode cùng lúc: unknown doc_id, ngày sai định dạng/lịch, bản policy cũ, chronology lệch, duplicate. Lý do là nếu dữ liệu chỉ sạch thì team khó chứng minh metric_impact của rule và expectation. Với bộ `policy_export_dirty_add_extra.csv`, nhóm đo được chênh lệch rõ giữa `inject-bad` và `clean-good`: cùng 13 raw records nhưng sau clean còn 7 records và 6 dòng quarantine. Cách thiết kế dữ liệu này giúp mọi phần downstream (quality report, grading jsonl, runbook) có bằng chứng định lượng thống nhất.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Anomaly tôi gặp là “eval top-k=3 có thể không lộ hết dữ liệu bẩn”, khiến tưởng như pipeline vẫn ổn. Cụ thể ở `after_inject_bad.csv`, câu refund có `hits_forbidden=no` nhưng trong grading top-k=5 lại `hits_forbidden=true`. Điều này cho thấy nhiễu nằm sâu trong context, chưa chắc xuất hiện ở top-1 hoặc top-3. Tôi phối hợp với cả nhóm giữ lại dataset inject có mức nhiễu đủ mạnh và xác nhận bằng grading artifacts (`grading_run_inject_bad.jsonl`) để tránh kết luận sai khi chỉ nhìn một file eval. Nhờ đó group report mô tả đúng bản chất sự cố context contamination, không bị “false sense of quality”.

---

## 4. Bằng chứng trước / sau (80–120 từ)

`run_id=inject-bad`:
- `manifest_inject-bad.json`: `raw_records=13`, `cleaned_records=13`, `quarantine_records=0`
- `grading_run_inject_bad.jsonl`: `gq_d10_01 hits_forbidden=true`, `gq_d10_03 hits_forbidden=true`

`run_id=clean-good`:
- `manifest_clean-good.json`: `raw_records=13`, `cleaned_records=7`, `quarantine_records=6`
- `grading_run.jsonl`: cùng hai câu trên đều `hits_forbidden=false`

Hai cặp số liệu này chứng minh rõ khi bật clean + validate thì chất lượng context retrieval cải thiện.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ chuẩn hóa thêm “bộ dữ liệu inject theo profile” (schema lỗi, versioning lỗi, chronology lỗi) thành nhiều file raw riêng biệt để có thể chạy A/B theo từng loại corruption. Như vậy team sẽ đo được metric_impact của từng rule một cách tách bạch hơn, thay vì gộp nhiều lỗi trong cùng một run.