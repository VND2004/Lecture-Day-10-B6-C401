# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** C401-B6  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Lương Hữu Thành | Embed & Idempotency Owner | 117010350+fisherman611@users.noreply.github.com |
| Vũ Như Đức | Ingestion / Raw Owner | vunhuduc2004@gmail.com |
| Nguyễn Tiến Thắng | Cleaning & Data Contract Owner | thang.nt225530@sis.hust.edu.vn |
| Hoàng Văn Bắc | Quality Report / Observability Owner | 26ai.bachv@viuni.edu.vn |
| Trần Anh Tú | Cleaning Rules & Raw Scenario Owner | 77563365+tuta202@users.noreply.github.com |
| Nguyễn Như Giáp | Monitoring / Docs Owner | baluanhugiap@gmail.com |
| Vũ Phúc Thành | Evaluation & Grading Evidence Owner | oliverheldensfhm@gmail.com |

**Ngày nộp:** 2026-04-15  
**Repo:** VND2004/Lecture-Day-10-B6-C401  
**Độ dài khuyến nghị:** 600–1000 từ

---

## 1. Pipeline tổng quan (150–200 từ)

Luồng nhóm triển khai theo chuỗi ingest → clean → expectation → embed → manifest/freshness trong `etl_pipeline.py`. Dữ liệu raw chính là `data/raw/policy_export_dirty_add_extra.csv` (13 dòng), chứa nhiều lỗi chủ đích: duplicate, thiếu ngày, ngày không hợp lệ, doc_id lạ, stale policy HR và chronology sai. Ở bước clean (`transform/cleaning_rules.py`), dữ liệu được chuẩn hóa, quarantine theo reason, sửa stale refund 14→7 và dedupe. Bước expectation (`quality/expectations.py`) có 10 check, trong đó đa số là `halt` để chặn publish khi dữ liệu bẩn. Sau khi pass, pipeline embed vào Chroma bằng cơ chế upsert theo `chunk_id` và prune id cũ để giữ snapshot nhất quán. Mỗi lần chạy sinh log + manifest có `run_id` và số liệu (`raw_records`, `cleaned_records`, `quarantine_records`). Nhóm dùng 2 run chính để chứng minh before/after: `inject-bad` và `clean-good`.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

`python etl_pipeline.py run --run-id clean-good && python eval_retrieval.py --out artifacts/eval/after_clean_good.csv`

---

## 2. Cleaning & expectation (150–200 từ)

Nhóm mở rộng cleaning bằng các rule có tác động đo được: chuẩn hóa định dạng text, chronology check (`exported_at >= effective_date`), validate calendar date thực, stale HR filter, refund window fix và dedupe. Ở expectation, nhóm bổ sung/siết các check như `doc_id_in_docs_allowlist`, `effective_date_calendar_valid`, `exported_not_before_effective`, `chunk_text_normalized_format`, `hr_leave_no_stale_10d_annual`.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| doc_id_allowlist + expectation `doc_id_in_docs_allowlist` | inject: unknown_doc_id_count=1 (FAIL) | clean: unknown_doc_id_count=0 (PASS) | `artifacts/manifests/manifest_inject-bad.json`, `docs/quality_report.md`, commit `b4c77fd`, `31bd8d1` |
| refund_window_fix + expectation `refund_no_stale_14d_window` | inject: violations=1 (FAIL) | clean: violations=0 (PASS) | `artifacts/eval/grading_run_inject_bad.jsonl`, `artifacts/eval/grading_run.jsonl`, commit `b4c77fd` |
| chronology check + expectation `exported_not_before_effective` | inject: chronology_violations=1 (FAIL) | clean: chronology_violations=0 (PASS) | `docs/quality_report.md`, quarantine reason `exported_before_effective_date` |
| dedupe + required field checks | inject: quarantine_records=0 | clean: quarantine_records=6 | `manifest_inject-bad.json` vs `manifest_clean-good.json` |

**Rule chính (baseline + mở rộng):**

- allowlist doc_id, chuẩn hóa effective_date, required field check, HR stale filter, text normalization, chronology check, dedupe, refund_window_fix.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Run `inject-bad` dùng `--no-cleaning-rules --skip-validate` làm expectation halt fail hàng loạt (8 fail). Cách xử lý là chạy lại run chuẩn `clean-good` với full cleaning rules để expectation pass và prune chunk bẩn khỏi vector store.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**

Nhóm chạy: `python etl_pipeline.py run --run-id inject-bad --no-cleaning-rules --skip-validate`. Mục tiêu là cố ý publish dữ liệu chưa qua clean để đo ảnh hưởng retrieval. Sau đó chạy lại run chuẩn `clean-good` để so sánh.

**Kết quả định lượng (từ CSV / bảng):**

- Ở mức manifest: `inject-bad` có `cleaned_records=13, quarantine_records=0`, còn `clean-good` có `cleaned_records=7, quarantine_records=6`.
- Ở grading top-k=5:  
  - `gq_d10_01` (refund): `hits_forbidden=true` khi inject, về `false` sau clean.  
  - `gq_d10_03` (HR leave): `hits_forbidden=true` khi inject, về `false` sau clean.  
  - `gq_d10_02` (P1 SLA): ổn định `false` ở cả hai run.
- Ở eval golden top-k=3, chênh lệch thể hiện rõ nhất ở `q_leave_version`: inject có `hits_forbidden=yes`, clean là `no`.

Ý nghĩa: dù top-1 có thể vẫn đúng, context top-k vẫn có thể chứa chunk stale. Do đó nhóm dùng thêm grading top-k=5 để tăng độ nhạy quan sát “context contamination” và chứng minh hiệu quả rule clean + prune trong embed.

---

## 4. Freshness & monitoring (100–150 từ)

Nhóm cấu hình SLA freshness 24 giờ (`FRESHNESS_SLA_HOURS=24`) và kiểm tra qua `python etl_pipeline.py freshness --manifest ...`. Kết quả trên các manifest mẫu:

- `inject-bad`: `latest_exported_at=2026-04-15T08:10:00`, PASS.
- `clean-good`: `latest_exported_at=2026-04-15T08:00:00`, PASS.
- `sprint1`: dữ liệu export cũ (2026-04-10), FAIL do vượt SLA.

PASS/WARN/FAIL được dùng như tín hiệu vận hành: PASS = dữ liệu đủ tươi để publish; FAIL = cần kiểm tra nguồn export/cron hoặc điều chỉnh SLA có lý do. Runbook (`docs/runbook.md`) mô tả thứ tự debug và artifact cần kiểm tra trước khi xử lý model/prompt.

---

## 5. Liên hệ Day 09 (50–100 từ)

Dữ liệu sau embed ở Day 10 là lớp “nguồn sự thật” cho agent Day 09. Khi chưa clean, agent có nguy cơ lấy nhầm chunk stale (14 ngày refund hoặc 10 ngày phép HR) dù top-1 đôi lúc vẫn đúng. Sau khi clean + expectation + prune, context retrieval ổn định hơn, giảm rủi ro trả lời sai chính sách khi orchestration multi-agent chạy ở Day 09.

---

## 6. Rủi ro còn lại & việc chưa làm

- Eval golden top-k=3 chưa luôn phát hiện contamination như grading top-k=5.
- Freshness hiện dựa vào manifest timestamp, chưa nối trực tiếp watermark từ hệ nguồn thật.
- `contracts/data_contract.yaml` vẫn còn owner/source ở mức tổng quát, có thể chi tiết thêm theo từng domain owner.
- Chưa có đánh giá end-to-end bằng LLM judge; hiện vẫn keyword-based.
