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
| chunk_id | string | Có | Mã hash SHA256 dựa trên doc_id, nội dung chunk và seq, đảm bảo Idempotent. |
| doc_id | string | Có | Khóa định danh tài liệu tham chiếu (VD: policy_refund_v4), phải nằm trong Allowlist. |
| chunk_text | string | Có | Nội dung kiến thức sạch, đã bị loại bỏ thẻ HTML, không còn nhãn [DRAFT]. |
| effective_date | date | Có | Ngày chính sách có hiệu lực, chuẩn hóa bắt buộc ISO 8601 (YYYY-MM-DD). |
| exported_at | datetime | Có | Thời gian xuất file raw từ API/DB nguồn. Dùng để tính SLA Freshness Monitor. |

---

## 3. Quy tắc quarantine vs drop

- **Không tự ý Drop (xóa hoàn toàn):** Không có dòng dữ liệu nào bị xóa vĩnh viễn không để lại dấu dạng hố đen. Mọi record không hợp lệ đều được "Quarantine" (cách ly) và ghi file log CSV riêng `artifacts/quarantine/`.
- **Người xử lý (Human-in-the-loop):** Data Quality Team sẽ xem xét file quarantine này, sau đó báo cho chủ sở hữu tài liệu (Data Owner bên HR hoặc IT) sửa dữ liệu tại Nguồn (Confluence, Wiki, ERP).
- **Merge lại thế nào?:** Hệ thống không sửa tay trực tiếp trong file quarantine để merge. Bản sửa đúng sẽ xuất hiện và tự động pass qua chốt chặn ở lần chạy cronjob Export (Run ETL) định kỳ kế tiếp.

---

## 4. Phiên bản & canonical

- **Source of truth (Bản chuẩn xác nhất):** Thừa nhận tài liệu `policy_refund_v4.txt` và `hr_leave_policy` năm 2026.
- **Quy tắc phiên bản:** Mọi chunk text có chứa logic thông tin lỗi thời như "Hoàn tiền 14 ngày làm việc" (bản v3 năm 2024 đổ về trước) hoặc "nghỉ phép 10 ngày" (năm 2025) sẽ bị chặn lại hoặc can thiệp đính chính thành "7 ngày" trước khi nhúng. Canonical Vector được phục vụ trong hệ thống bắt buộc là version 4 (2026) mới nhất.
