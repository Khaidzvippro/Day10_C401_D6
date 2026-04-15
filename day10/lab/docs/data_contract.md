# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `policy_export_dirty.csv` | Batch CSV | Stale dates, corrupted encoding | `quarantine_records` > 0 |
| `data/docs/` | Local Files | Missing metadata, encoding | `raw_records` match count |

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

- **Quarantine:** Bản ghi bị flag sẽ được đẩy vào `artifacts/quarantine/*.csv`.
- **Review:** Tech Lead và Documentation Owner sẽ review định kỳ.
- **Merge:** Sau khi sửa lỗi ở nguồn, dữ liệu sẽ được re-ingest.

---

## 4. Phiên bản & canonical

- **Source of Truth:** Chính sách `policy_refund_v4` là bản cập nhật nhất cho năm 2026.
- **Canonical Path:** `/home/son/Day10_C401_D6/day10/lab/data/raw/`
