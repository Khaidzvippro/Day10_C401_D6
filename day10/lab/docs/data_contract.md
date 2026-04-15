# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — Đã đồng bộ 100% với phiên bản 1.0 của nhóm C401 - D6.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `policy_export_dirty.csv` | Batch CSV | Stale dates, Corrupted encoding | `quarantine_records` > 0 |
| `data/docs/` | Local Files | Missing metadata, Version conflict | `effective_date` < cutoff |
| `access_control_sop` | Local Files | Unknown doc_id (Rule 10) | `illegal_doc_id_count` > 0 |

**Nhóm:** C401 - D6  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Lê Huy Hồng Nhật | Tech Lead | nhat050403@gmail.com |
| Nguyễn Quốc Khánh | Retrieval Owner | khanhnq352005@gmail.com |
| Nguyễn Tuấn Khải | Quality Owner | tuankhaidx2003@gmail.com |
| Phan Văn Tấn | Eval Owner | tana2k53nvt@gmail.com |
| Lê Công Thành | Eval Owner | lcthanh.htvn@gmail.com |
| Nguyễn Quế Sơn | Documentation Owner | sonnguyenque5@gmail.com |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Hash duy nhất của nội dung và doc_id |
| doc_id | string | Có | Phải thuộc allowlist trong contract |
| chunk_text | string | Có | Văn bản đã làm sạch và fix stale data |
| effective_date | date | Có | ISO YYYY-MM-DD |
| exported_at | datetime | Có | ISO-8601 từ hệ thống nguồn |

---

## 3. Quy tắc quarantine vs drop

- **Quarantine:** Bản ghi bị flag (Rule 7-11) được đẩy vào `artifacts/quarantine/*.csv`.
- **Halt (E7, E9):** Dừng pipeline nếu định dạng ngày tháng sai lệch nghiêm trọng hoặc doc_id lạ lọt lưới (phát hiện `access_control_sop` vi phạm).
- **Review:** Tech Lead (Nhật) và Documentation Owner (Sơn) review định kỳ.

---

## 4. Phiên bản & canonical

- **Source of Truth:** Chính sách `policy_refund_v4` và `access_control_sop`.
- **Owner:** C401-D6 (Documentation: Nguyen Que Son / Tech Lead: Le Huy Hong Nhat)
- **Alert:** Kênh Slack `#c401-d6-data-alert` (SLA freshness > 24 giờ).
