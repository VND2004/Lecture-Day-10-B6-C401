# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| **Policy/HR System** (`policy_refund`, `hr_leave_policy`) | Bulk CSV Export định kỳ | Dữ liệu trùng lặp, chứa phiên bản chính sách cũ (stale data), thiếu dữ liệu dòng (`chunk_text`, date) | % duplicate records, % records thiếu text/date, Số lượng conflict policy. |
| **IT Helpdesk/Wiki** (`it_helpdesk_faq`, `sla_p1_2026`) | API/CSV Sync từ Confluence/Jira | Sai định dạng ngày tháng hiệu lực (non-ISO), ID tài liệu không hợp lệ (`legacy_catalog_xyz...`) | % date format lỗi, % doc_id bị rejected/không nằm trong allowlist. |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | … |
| doc_id | string | Có | … |
| chunk_text | string | Có | … |
| effective_date | date | Có | … |
| exported_at | datetime | Có | … |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?
