# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Như Giáp  
**Vai trò:** Monitoring / Runbook / Documentation Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `day10/lab/docs/runbook.md`

**Kết nối với thành viên khác:**

Tôi tổng hợp góc nhìn vận hành từ các phần ingestion-cleaning-eval của nhóm và đóng gói thành runbook để người vận hành debug theo thứ tự chuẩn. Các thành viên kỹ thuật cung cấp log, manifest, eval; tôi đưa về checklist chẩn đoán và quy trình khắc phục/phòng ngừa.

**Bằng chứng (commit / comment trong code):**

Commit chính: `44e49a4` (Add runbooks), kèm các merge commit đồng bộ nhánh: `835fe30`, `76af30d`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định của tôi là chuẩn hóa thứ tự debug “freshness/version → volume/quarantine → schema/contract → lineage/run_id → model/prompt” ngay trong runbook. Đây là quyết định quan trọng vì khi agent trả lời sai, nhóm thường có xu hướng nhảy ngay vào prompt/model; nhưng ở Day 10, nguyên nhân gốc đa phần nằm ở data quality. Tôi biến quy trình này thành bảng thao tác cụ thể: mở manifest để đọc run metadata, mở log để xem expectation fail/halt, đọc quarantine reason, rồi mới chạy eval/grading. Cách tổ chức này giúp giảm thời gian khoanh vùng lỗi và tránh fix sai tầng.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Anomaly vận hành tôi xử lý là trường hợp freshness FAIL dễ bị hiểu nhầm là “pipeline hỏng”. Trong dữ liệu lab, run `sprint1` có `latest_exported_at` cũ nên freshness báo FAIL dù code chạy đúng. Tôi ghi rõ trong runbook rằng cần phân biệt “lỗi hệ thống” và “tín hiệu dữ liệu không còn tươi theo SLA”. Đồng thời tôi thêm hướng dẫn khi nào được dùng `--skip-validate` (chỉ inject demo) và không dùng cho run chuẩn. Nhờ vậy đội tránh việc publish dữ liệu chưa qua kiểm soát chỉ vì muốn pipeline chạy qua bước embed.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Bằng chứng tôi sử dụng trong runbook và báo cáo:

- `manifest_inject-bad.json`: `run_id=inject-bad`, `cleaning_rules_enabled` đều `false`, `skipped_validate=true`.
- `manifest_clean-good.json`: `run_id=clean-good`, `cleaning_rules_enabled` đều `true`, `skipped_validate=false`.

Từ hai manifest này có thể thấy trạng thái vận hành trước/sau rõ ràng: run inject phục vụ demo corruption, run clean phục vụ publish chuẩn. Kết hợp với grading JSONL, sau clean các chỉ số `hits_forbidden` ở câu nhạy cảm chuyển từ `true` sang `false`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ thêm phần “on-call checklist” ngắn (5 bước) và template incident note vào runbook để mỗi lần có regression nhóm chỉ cần điền run_id, expectation fail, artifact đính kèm và phương án rollback. Điều này sẽ giúp quy trình vận hành nhất quán hơn khi làm theo nhóm đông thành viên.
