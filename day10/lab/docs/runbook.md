# Runbook - Lab Day 10

---

## Triệu chứng

Người dùng hoặc agent trả lời sai do retrieval lấy nhầm ngữ cảnh từ dữ liệu bẩn hoặc đã lỗi thời.

Các tình huống thường gặp:

- Người dùng hỏi về thời hạn hoàn tiền, nhưng agent trả lời "14 ngày làm việc" thay vì "7 ngày làm việc".
- Người dùng hỏi phiên bản chính sách nghỉ phép HR, nhưng ngữ cảnh vẫn chứa bản cũ "10 ngày phép năm".
- Top-k retrieval bị lặp chunk hoặc có chunk mang `doc_id` lạ, khiến câu trả lời bị nhiễu.
- Snapshot dữ liệu quá cũ nên kiểm tra độ tươi (`freshness check`) báo WARN/FAIL.

---

## Phát hiện

Dùng các tín hiệu sau để phát hiện vấn đề:

- Log pipeline có expectation `FAIL`, ví dụ: `refund_no_stale_14d_window`, `doc_id_in_docs_allowlist`, `effective_date_calendar_valid`, `exported_not_before_effective`.
- File eval CSV có `hits_forbidden=true`, đặc biệt với `q_refund_window` hoặc `q_leave_version`.
- `artifacts/quarantine/*.csv` có `reason` như `duplicate_chunk_text`, `unknown_doc_id`, `missing_effective_date`, `invalid_effective_date_calendar`, `stale_hr_policy_effective_date`.
- Manifest/log có `freshness_check=FAIL` nếu `latest_exported_at` cũ hơn SLA.
- Manifest có `cleaning_rules_enabled` để nhận biết run nào đã tắt rule bằng các cờ `--no-*`.

Các artifact bằng chứng của nhóm:

- Before inject: `artifacts/eval/after_inject_bad.csv`
- After clean: `artifacts/eval/after_clean_good.csv`
- Grading: `artifacts/eval/grading_run.jsonl`

---

## Chẩn đoán

Thứ tự debug ưu tiên: freshness/version -> volume/quarantine -> schema/contract -> lineage/run_id -> model/prompt.

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Mở `artifacts/manifests/manifest_<run-id>.json` | Kiểm tra `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`, `latest_exported_at`, `cleaning_rules_enabled` |
| 2 | Mở `artifacts/logs/run_<run-id>.log` | Xác định expectation nào `FAIL` và pipeline có dừng ở `PIPELINE_HALT` hay bị bỏ qua bằng `--skip-validate` |
| 3 | Mở `artifacts/quarantine/quarantine_<run-id>.csv` | Xem dòng nào bị loại và `reason` là gì: duplicate, `doc_id` lạ, thiếu ngày, HR stale |
| 4 | Mở `artifacts/cleaned/cleaned_<run-id>.csv` | Đảm bảo cleaned output không còn "14 ngày làm việc", "10 ngày phép năm", `doc_id` lạ, ngày sai định dạng |
| 5 | Chạy `python eval_retrieval.py --out artifacts/eval/check.csv` | Các câu golden có `contains_expected=true` và `hits_forbidden=false` |
| 6 | Chạy `python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl` | File grading đủ dòng và các câu chính đạt sanity check |

---

## Khắc phục

Nếu đây là run chuẩn, không dùng `--skip-validate`. Chạy lại pipeline với toàn bộ cleaning rules đang bật:

```bash
python etl_pipeline.py run --run-id clean-good
python eval_retrieval.py --out artifacts/eval/after_clean_good.csv
```

Nếu cần tạo bằng chứng before cho Sprint 3, chỉ dùng inject có chủ đích:

```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
```

Nếu nghi vector store còn dữ liệu cũ:

- Kiểm tra log `embed_prune_removed`.
- Chạy lại pipeline chuẩn để upsert theo `chunk_id` và prune các id không còn trong cleaned snapshot.
- So sánh lại `after_inject_bad.csv` với `after_clean_good.csv`.

Nếu `freshness_check=FAIL`, cần xác định SLA đang áp cho data snapshot hay pipeline run. Với CSV mẫu, FAIL có thể hợp lý vì `exported_at` cũ hơn SLA 24 giờ; với production thì cần cập nhật export mới hoặc điều chỉnh `FRESHNESS_SLA_HOURS` có lý do.

---

## Phòng ngừa

Giữ các expectation quan trọng ở mức severity `halt`:

- `refund_no_stale_14d_window`: không để policy refund 14 ngày lọt vào cleaned.
- `doc_id_in_docs_allowlist`: `doc_id` trong cleaned phải khớp catalog `data/docs/*.txt`.
- `effective_date_iso_yyyy_mm_dd` và `effective_date_calendar_valid`: ngày phải đúng định dạng và tồn tại trên lịch.
- `exported_not_before_effective`: export không được trước ngày effective.
- `hr_leave_no_stale_10d_annual`: không còn bản HR cũ trong cleaned.

Quy tắc vận hành:

- Không dùng `--skip-validate` trong run chuẩn; chỉ dùng cho inject/before evidence.
- Ghi và review `cleaning_rules_enabled` trong manifest mỗi lần run.
- Theo dõi `quarantine_records`; nếu tăng bất thường thì mở quarantine CSV để xem `reason`.
- Lưu eval before/after trong `artifacts/eval/` để chứng minh fix có tác động.
- Cập nhật `contracts/data_contract.yaml` khi thêm `doc_id` hoặc source mới.
- Gán owner cho data source và SLA freshness trong data contract/report.
