# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Vũ Phúc Thành  
**Vai trò:** Evaluation / Grading Evidence Owner  
**Ngày nộp:** 2026-04-15  

---

## 1. Tôi phụ trách phần nào? 

**File / module:**

- `day10/lab/artifacts/eval/grading_run_inject_bad.jsonl`
- `day10/lab/artifacts/manifests/manifest_sprint1.json`
- `day10/lab/artifacts/cleaned/cleaned_sprint1.csv`
- `day10/lab/artifacts/quarantine/quarantine_sprint1.csv`

**Kết nối với thành viên khác:**

Tôi phụ trách phần bằng chứng chấm điểm (grading) và artifact sprint đầu để nhóm có dữ liệu đối chiếu xuyên suốt từ ingest đến đánh giá retrieval. Tôi phối hợp với Bắc để đưa số liệu grading vào quality report và với Hữu Thành để kiểm tra before/after theo run_id.

**Bằng chứng (commit / comment trong code):**

Commit chính: `0942990`, `144b4c5`, `f441ef1`.

---

## 2. Một quyết định kỹ thuật 

Quyết định kỹ thuật của tôi là dùng grading JSONL top-k=5 để làm lớp kiểm tra nhạy hơn so với eval golden top-k=3. Trong thực tế RAG, top-1 đúng chưa đủ; nếu top-k vẫn chứa chunk sai thì agent vẫn có nguy cơ trả lời lệch khi tổng hợp ngữ cảnh. Vì vậy tôi tạo `grading_run_inject_bad.jsonl` để chụp đúng trạng thái “context bị nhiễu” ở run inject. Cách làm này bổ sung tốt cho eval CSV: eval cho bức tranh nhanh, grading cho kiểm tra sát tiêu chí chấm và độ sạch của context rộng hơn.

---

## 3. Một lỗi hoặc anomaly đã xử lý 

Anomaly tôi theo dõi là độ lệch giữa các bộ đánh giá: một số câu ở eval trông ổn nhưng grading vẫn fail tiêu chí `hits_forbidden`. Nếu nhóm chỉ bám eval top-k=3 thì dễ kết luận sớm rằng dữ liệu đã sạch. Tôi xử lý bằng cách giữ riêng artifact grading cho run inject, trong đó `gq_d10_01` và `gq_d10_03` đều có `hits_forbidden=true`, để cả nhóm thấy rõ ảnh hưởng của dữ liệu stale trong context. Sau khi chạy clean-good, so sánh với `grading_run.jsonl` cho thấy hai chỉ số này về `false`. Điều này giúp báo cáo nhóm có bằng chứng mạnh hơn và tránh “đánh giá thiếu độ sâu”.

---

## 4. Bằng chứng trước / sau 

`run_id=inject-bad` (`artifacts/eval/grading_run_inject_bad.jsonl`):
- `gq_d10_01`: `contains_expected=true`, `hits_forbidden=true`
- `gq_d10_03`: `contains_expected=true`, `hits_forbidden=true`, `top1_doc_matches=true`

`run_id=clean-good` (`artifacts/eval/grading_run.jsonl`):
- `gq_d10_01`: `contains_expected=true`, `hits_forbidden=false`
- `gq_d10_03`: `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true`

Đây là bằng chứng rõ rằng clean + expectation + prune đã giảm nhiễu context.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ thêm một script so sánh tự động hai file grading theo từng id (inject vs clean) và xuất bảng diff `contains_expected/hits_forbidden/top1_doc_matches`. Việc này giúp đội cập nhật báo cáo nhanh, đồng thời giảm rủi ro đọc nhầm khi số lượng câu hỏi grading tăng lên ở các buổi lab sau.
