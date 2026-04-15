# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
| :--- | :--- | :--- | :--- |
| **CSV Raw Export** (`kb_chunk_raw.csv`) | Batch processing (mỗi 24h) | Sai định dạng ngày tháng, trùng lặp nội dung chunk. | Tỷ lệ dòng lỗi > 5% |
| **Docs Folder** (`data/docs/*.txt`) | File system watcher / Git sync | Thiếu file canonical (v4), sai versioning văn bản. | SLA Freshness > 24h |
---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
| :--- | :--- | :--- | :--- |
| `chunk_id` | string | Có | Hash hoặc `doc_id` + `seq`. Đảm bảo tính ổn định để tránh duplicate. |
| `doc_id` | string | Có | Khóa logic ánh xạ tới nguồn (VD: `policy_refund_v4`). |
| `chunk_text` | string | Có | Nội dung văn bản (Min length: 8 chars). |
| `effective_date` | date | Có | Ngày văn bản có hiệu lực. Dùng để lọc chính sách cũ. |
| `exported_at` | datetime | Có | Thời điểm export dữ liệu từ pipeline. |

---

## 3. Quy tắc quarantine vs drop

>Để đảm bảo hệ thống RAG không trả lời sai, team C401-D6 áp dụng quy trình xử lý lỗi như sau:

* **Quarantine (Cách ly):**
    * **Trường hợp:** Record thiếu `effective_date` hoặc `chunk_text` bị cảnh báo trùng lặp (`warn`).
    * **Nơi lưu trữ:** Table `stg_kb_quarantine`.
    * **Quy trình xử lý:** Ingestion Owner (Nhật) kiểm tra thủ công. Nếu dữ liệu hợp lệ sau khi fix, sẽ được duyệt để merge lại vào main pipeline.
* **Drop (Hủy bỏ):**
    * **Trường hợp:** Vi phạm quy tắc `no_stale_refund_window` (chứa thông tin 14 ngày thay vì 7 ngày của v4). Đây là lỗi nghiêm trọng (`halt`).
    * **Hành động:** Pipeline dừng hoặc loại bỏ hoàn toàn record để bảo vệ tính đúng đắn của bot.

**Người phê duyệt (Approver):** Tech Lead (Lê Huy Hồng Nhật).

---

## 4. Phiên bản & canonical

> Xác định "Nguồn sự thật" (Source of Truth) để tránh Hallucination:

* **Source of Truth (Refund Policy):** File `data/docs/policy_refund_v4.txt`. 
* **Quy tắc phiên bản:** * Chỉ chấp nhận `doc_id: policy_refund_v4` với window = 7 ngày.
    * Mọi chunk chứa nội dung "14 ngày" sẽ bị hệ thống tự động loại bỏ.
* **Cutoff Date:** Các chính sách nhân sự (`hr_leave_policy`) phải có `effective_date` từ ngày **2026-01-01** (theo biến môi trường `hr_leave_min_effective_date`).
