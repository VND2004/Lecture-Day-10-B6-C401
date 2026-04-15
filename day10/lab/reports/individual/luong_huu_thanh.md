# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lương Hữu Thành  
**Vai trò:** Embed / Idempotency / Evaluation Artifact  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `day10/lab/etl_pipeline.py`
- `day10/lab/transform/cleaning_rules.py`
- `day10/lab/quality/expectations.py`
- `day10/lab/artifacts/eval/after_clean_good.csv`
- `day10/lab/artifacts/eval/grading_run.jsonl`

**Kết nối với thành viên khác:**

Tôi làm phần kết nối giữa clean/validate và publish sang vector DB. Khi Đức và Tú bổ sung dữ liệu raw, Thắng/Tú cập nhật rule clean, tôi điều chỉnh luồng chạy để có cờ bật/tắt cleaning phục vụ inject, rồi cùng Bắc/Thành đối chiếu kết quả eval trước-sau.

**Bằng chứng (commit / comment trong code):**

Các commit chính: `0089de1`, `598e6cb`, `b4c77fd`, `47143d4`, `8586d05`, `5c2ed07`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định quan trọng nhất của tôi là giữ tính idempotent ở tầng embed bằng `chunk_id` ổn định và cơ chế prune id cũ. Trong `etl_pipeline.py`, sau khi clean pass expectation, pipeline upsert vào Chroma theo `chunk_id` để rerun không nhân bản vector. Nhưng chỉ upsert thì chưa đủ: dữ liệu bẩn từ run trước có thể vẫn tồn tại nếu chunk đó không còn trong cleaned mới. Vì vậy tôi thêm bước đọc toàn bộ id trong collection và `delete` những id không thuộc snapshot cleaned hiện tại (`embed_prune_removed`). Quyết định này giúp đường biên publish rõ ràng: vector store phải phản ánh đúng cleaned CSV của run hiện tại, không giữ “mồi cũ” làm nhiễu top-k.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Anomaly lớn là khi chạy inject (`--no-cleaning-rules --skip-validate`), retrieval vẫn có top1 nhìn đúng nhưng top-k chứa chunk sai chính sách. Triệu chứng thấy rõ ở `artifacts/eval/grading_run_inject_bad.jsonl`: `gq_d10_01` và `gq_d10_03` có `hits_forbidden=true`. Điều này nghĩa là context vẫn lẫn “14 ngày làm việc” và “10 ngày phép năm”. Tôi xử lý theo hai lớp: (1) đảm bảo run chuẩn bật đủ cleaning rules và expectation halt, (2) ở embed, prune id cũ để xóa triệt để chunk bẩn từng được publish trong run inject. Sau khi chạy lại `clean-good`, file `artifacts/eval/grading_run.jsonl` cho thấy hai câu trên về `hits_forbidden=false`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

`run_id=inject-bad` (trước):
- `{"id":"gq_d10_01", ..., "hits_forbidden": true, "top_k_used": 5}`
- `{"id":"gq_d10_03", ..., "hits_forbidden": true, "top_k_used": 5}`

`run_id=clean-good` (sau):
- `{"id":"gq_d10_01", ..., "hits_forbidden": false, "top_k_used": 5}`
- `{"id":"gq_d10_03", ..., "hits_forbidden": false, "top_k_used": 5}`

Manifest cũng phản ánh tác động clean: inject có `cleaned_records=13, quarantine_records=0`, còn clean-good có `cleaned_records=7, quarantine_records=6`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ thêm một bước “snapshot integrity check” sau embed: so sánh số lượng ID thực tế trong collection với số dòng `cleaned_<run_id>.csv` và ghi metric sai lệch vào log/manifest. Việc này giúp phát hiện sớm trường hợp prune hoặc upsert không chạy đúng trong môi trường deploy thật.
