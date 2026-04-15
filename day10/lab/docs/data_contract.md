# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — Đã đồng bộ 100% với phiên bản 1.0 của nhóm D401 - D6.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `policy_export_dirty.csv` | Batch CSV | Stale dates, Corrupted encoding | `quarantine_records` > 0 |
| `data/docs/` | Local Files | Missing metadata, Version conflict | `effective_date` < cutoff |
| `access_control_sop` | Local Files | Unknown doc_id (Rule 10) | `illegal_doc_id_count` > 0 |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Hash duy nhất của nội dung và doc_id |
| doc_id | string | Có | Phải thuộc allowlist trong contract |
| chunk_text | string | Có | Văn bản đã làm sạch và fix stale data |
| effective_date | date | Có | Định dạng ISO YYYY-MM-DD |
| exported_at | datetime | Có | ISO-8601 từ hệ thống nguồn |

---

## 3. Quy tắc quarantine vs drop

- **Quarantine:** Bản ghi bị flag (Rule 7-11) được đẩy vào `artifacts/quarantine/*.csv`.
- **Halt (E7, E9):** Dừng pipeline nếu định dạng ngày tháng sai lệch nghiêm trọng hoặc doc_id lạ lọt lưới (phát hiện `access_control_sop` vi phạm).
- **Review:** Tech Lead (Nhật) và Documentation Owner (Sơn) review định kỳ.

---

## 4. Phiên bản & canonical

- **Source of Truth:** Chính sách `policy_refund_v4` và `access_control_sop`.
- **Owner:** Nguyễn Quế Sơn (Documentation Owner - Team D401-D6)
- **Alert:** Email / Slack khi Freshness > 24 giờ.
