# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Hoàng Văn Bắc  
**Vai trò:** Quality Report / QA Evidence Owner  
**Ngày nộp:** 2026-04-15  


---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `day10/lab/docs/quality_report.md`
- `day10/lab/artifacts/eval/after_inject_bad.csv`
- `day10/lab/artifacts/cleaned/cleaned_inject-bad.csv`
- `day10/lab/artifacts/manifests/manifest_inject-bad.json`
- `day10/lab/artifacts/quarantine/quarantine_inject-bad.csv`

**Kết nối với thành viên khác:**

Tôi nhận output từ pipeline/eval của cả nhóm và tổng hợp thành quality report có số liệu trước-sau, bảng expectation, freshness và phần corruption inject. Tôi phối hợp với Hữu Thành/Thành để lấy grading jsonl, với Thắng/Tú để mô tả đúng nguyên nhân theo rule.

**Bằng chứng (commit / comment trong code):**

Commit chính: `0d44dec`, `de84ac3`, `5e26860`.

---

## 2. Một quyết định kỹ thuật

Quyết định của tôi là dùng đồng thời hai lớp bằng chứng: (1) manifest/log cho số lượng record và trạng thái expectation, (2) eval/grading cho tác động lên retrieval. Nếu chỉ có một lớp, báo cáo dễ thiếu thuyết phục: ví dụ biết quarantine tăng nhưng không biết agent có bớt nhiễu không; hoặc biết retrieval cải thiện nhưng không chỉ ra rule nào tạo cải thiện. Trong quality report, tôi đặt bảng metric tổng (`raw_records`, `cleaned_records`, `quarantine_records`, expectation halt) và bảng theo từng câu hỏi grading (`hits_forbidden` inject vs clean). Cách trình bày này giúp trace rõ từ nguyên nhân dữ liệu → tín hiệu chất lượng → tác động đầu ra.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly tôi gặp là sự khác biệt giữa eval golden top-k=3 và grading top-k=5. Ban đầu nhìn `after_inject_bad.csv`, nhiều chỉ số tưởng vẫn ổn, nhưng khi xem `grading_run_inject_bad.jsonl` thì `gq_d10_01` và `gq_d10_03` đều có `hits_forbidden=true`. Tôi ghi rõ trong báo cáo rằng top-k nhỏ có thể bỏ sót contamination trong context. Đây không phải lỗi code, mà là lỗi quan sát nếu chọn metric chưa đủ nhạy. Việc bổ sung phân tích top-k=5 giúp team chứng minh đúng tinh thần observability: không chỉ đúng câu trả lời top-1, mà phải sạch cả ngữ cảnh truy hồi.

---

## 4. Bằng chứng trước / sau

Bằng chứng tôi đưa vào `docs/quality_report.md`:

- `run_id inject-bad`: `raw_records=13`, `cleaned_records=13`, `quarantine_records=0`, expectation halt = YES.
- `run_id clean-good`: `raw_records=13`, `cleaned_records=7`, `quarantine_records=6`, expectation halt = NO.

Với grading top-k=5:
- `gq_d10_01`: `hits_forbidden` từ `true` → `false`.
- `gq_d10_03`: `hits_forbidden` từ `true` → `false`.

Đây là bằng chứng before/after rõ nhất về tác động của cleaning + expectation + embed prune.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ chuẩn hóa quality report thành form bán tự động: đọc trực tiếp manifest/eval/grading và sinh bảng so sánh. Như vậy báo cáo sẽ bớt phụ thuộc thao tác thủ công, giảm sai sót khi nhóm chạy lại nhiều run_id hoặc thay đổi top-k trong quá trình kiểm thử.