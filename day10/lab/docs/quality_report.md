# Quality Report — Lab Day 10 (nhóm)

**run_id (clean):** clean-good  
**run_id (inject):** inject-bad  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (inject-bad) | Sau (clean-good) | Ghi chú |
|--------|-------------------|-----------------|---------|
| raw_records | 13 | 13 | Cùng file `policy_export_dirty_add_extra.csv` |
| cleaned_records | 13 | 7 | inject: tắt toàn bộ cleaning → 0 bị quarantine |
| quarantine_records | 0 | 6 | Sau clean: 6 dòng bị loại (stale HR, ngày sai, doc_id lạ, duplicate) |
| Expectation halt? | YES (8 fail) | NO (tất cả pass) | inject dùng `--no-cleaning-rules --skip-validate` |

### Quarantine breakdown (clean-good — 6 dòng bị loại)

| chunk_id | doc_id | reason | Chi tiết |
|----------|--------|--------|---------|
| 2 | policy_refund_v4 | duplicate_chunk_text | Nội dung trùng với chunk đã có |
| 5 | policy_refund_v4 | missing_effective_date | Trường `effective_date` rỗng |
| 7 | hr_leave_policy | stale_hr_policy_effective_date | effective_date=2025-01-01 < 2026-01-01 (bản HR cũ "10 ngày phép") |
| 9 | legacy_catalog_xyz_zzz | unknown_doc_id | doc_id không thuộc allowlist |
| 12 | policy_refund_v4 | invalid_effective_date_calendar | effective_date=2026-02-30 không tồn tại trong lịch |
| 13 | hr_leave_policy | exported_before_effective_date | exported_at=2025-12-31 < effective_date=2026-01-01 (vi phạm chronology) |

> inject-bad: quarantine=0 — toàn bộ 13 dòng kể cả dữ liệu bẩn đều lọt vào cleaned vì `--no-cleaning-rules`.

---

Chi tiết expectations khi inject-bad:

| Expectation | inject-bad | clean-good |
|-------------|-----------|-----------|
| min_one_row | OK | OK |
| no_empty_doc_id | OK | OK |
| doc_id_in_docs_allowlist | **FAIL** (1 unknown) | OK |
| refund_no_stale_14d_window | **FAIL** (1 violation) | OK |
| chunk_min_length_8 | **FAIL** (warn, 1 short) | OK |
| effective_date_iso_yyyy_mm_dd | **FAIL** (2 non-ISO) | OK |
| effective_date_calendar_valid | **FAIL** (3 invalid) | OK |
| exported_not_before_effective | **FAIL** (1 violation) | OK |
| chunk_text_normalized_format | **FAIL** (1 violation) | OK |
| hr_leave_no_stale_10d_annual | **FAIL** (1 violation) | OK |

---

## 2. Before / after retrieval

File đính kèm:
- `artifacts/eval/after_inject_bad.csv` — eval golden (top-k=3) sau inject
- `artifacts/eval/after_clean_good.csv` — eval golden (top-k=3) sau clean
- `artifacts/eval/grading_run_inject_bad.jsonl` — grading thực tế (top-k=5) sau inject
- `artifacts/eval/grading_run.jsonl` — grading thực tế (top-k=5) sau clean

### Grading thực tế (top-k=5) — so sánh inject vs clean

| id | Question | hits_forbidden (inject) | hits_forbidden (clean) | Nhận xét |
|----|----------|------------------------|----------------------|---------|
| gq_d10_01 | Refund window — bao nhiêu ngày? | **true** | false | Chunk "14 ngày làm việc" lọt vào top-5 khi inject |
| gq_d10_02 | Ticket P1 resolution SLA? | false | false | Không bị ảnh hưởng |
| gq_d10_03 | Nhân viên <3 năm được bao nhiêu ngày phép? | **true** | false | Chunk HR cũ "10 ngày phép" lọt vào top-5 khi inject |

> Grading dùng top-k=5 (rộng hơn eval golden top-k=3) nên phát hiện được chunk stale ở `gq_d10_01` mà eval golden bỏ sót — đúng tinh thần observability "context vẫn còn chunk stale dù top-1 nhìn đúng".

### Câu hỏi then chốt: refund window (`gq_d10_01`)

| Scenario | top1_doc_id | contains_expected | hits_forbidden | top_k |
|----------|-------------|-------------------|----------------|-------|
| Trước (inject-bad) | policy_refund_v4 | true | **true** | 5 |
| Sau (clean-good) | policy_refund_v4 | true | false | 5 |

Chunk "14 ngày làm việc" không bị fix do `--no-cleaning-rules` → embed vào collection → xuất hiện trong top-5 context. Sau clean: `refund_window_fix` đổi thành "7 ngày" + `embed_prune_removed` xóa chunk cũ → `hits_forbidden=false`.

### Merit: versioning HR — `gq_d10_03`

| Scenario | top1_doc_id | contains_expected | hits_forbidden | top1_doc_matches | top_k |
|----------|-------------|-------------------|----------------|-----------------|-------|
| Trước (inject-bad) | hr_leave_policy | true | **true** | true | 5 |
| Sau (clean-good) | hr_leave_policy | true | false | true | 5 |

Khi `--no-cleaning-rules`: chunk HR cũ "10 ngày phép năm" (effective_date=2025-01-01) không bị quarantine → lọt vào embed → `hits_forbidden=true`. Sau clean: `hr_stale_filter` loại chunk → `hits_forbidden=false`. `top1_doc_matches=true` cả hai scenario vì doc_id đúng, nhưng context bị nhiễu bởi version cũ.

---

## 3. Freshness & monitor

| Run | latest_exported_at | age_hours | SLA (giờ) | Kết quả |
|-----|--------------------|-----------|-----------|---------|
| inject-bad | 2026-04-15T08:10:00 | ~1.7 | 24 | **PASS** |
| clean-good | 2026-04-15T08:00:00 | ~1.9 | 24 | **PASS** |
| sprint1 | 2026-04-10T08:00:00 | ~120 | 24 | **FAIL** (freshness_sla_exceeded) |

SLA 24 giờ được cấu hình qua `FRESHNESS_SLA_HOURS=24` trong `.env`.  
Run `sprint1` dùng file mẫu cũ (`policy_export_dirty.csv`) có `exported_at` cố định ngày 2026-04-10 nên luôn FAIL freshness — đây là hành vi đúng, phản ánh dữ liệu nguồn không được refresh.

---

## 4. Corruption inject (Sprint 3)

**Cách inject:** Chạy `python etl_pipeline.py run --run-id inject-bad --no-cleaning-rules --skip-validate`

Tắt toàn bộ 8 cleaning rules, bao gồm:

| Rule bị tắt | Hậu quả |
|-------------|---------|
| `doc_id_allowlist` | 1 doc_id lạ (`unknown_source`) lọt vào embed |
| `effective_date_cleaning` | 2 dòng ngày không ISO, 3 dòng ngày không tồn tại trong lịch |
| `hr_stale_filter` | Chunk HR cũ (effective_date 2024) lọt vào → `hits_forbidden=yes` trên `q_leave_version` |
| `refund_window_fix` | Chunk "14 ngày làm việc" không bị fix → expectation `refund_no_stale_14d_window` FAIL |
| `dedupe` | Duplicate chunk được embed → vector store có bản sao |
| `text_normalization` | HTML tag / whitespace thừa trong chunk_text |
| `chronology_check` | 1 dòng `exported_at` < `effective_date` |
| `required_field_check` | Dòng thiếu field bắt buộc không bị quarantine |

**Phát hiện:** 8/10 expectations FAIL khi không có cleaning. Pipeline bị halt nhưng `--skip-validate` cho phép embed tiếp (chỉ dùng cho demo có chủ đích).

**Khôi phục:** Chạy lại pipeline chuẩn `python etl_pipeline.py run --run-id clean-good` → tất cả expectations pass, `embed_prune_removed` xóa các chunk bẩn khỏi collection.

---

## 5. Hạn chế & việc chưa làm

- `q_refund_window` ở eval golden (top-k=3) không thấy `hits_forbidden=yes`, nhưng grading thực tế (top-k=5) đã phát hiện — cho thấy top-k nhỏ có thể che khuất chunk stale trong context
- Freshness check chỉ dựa trên `latest_exported_at` trong manifest, chưa kết nối watermark DB thực tế
- Chưa có LLM-judge để đánh giá chất lượng câu trả lời end-to-end (chỉ keyword-based)
- Data contract `contracts/data_contract.yaml` chưa được điền đầy đủ owner và SLA nguồn
