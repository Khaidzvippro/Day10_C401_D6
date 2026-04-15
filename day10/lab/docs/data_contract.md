# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` | Batch CSV (entrypoint `etl_pipeline.py`) | duplicate chunk, thiếu `effective_date`, doc_id lạ, stale policy text | `quarantine_records`, expectation FAIL |
| `data/docs/policy_refund_v4.txt` | Canonical local file | stale refund window bị sync ngược từ bản cũ | `refund_no_stale_14d_window` |
| `data/docs/hr_leave_policy.txt` | Canonical local file | lẫn version 2025 (10 ngày) với 2026 (12 ngày) | `hr_leave_no_stale_10d_annual` |
| `data/docs/sla_p1_2026.txt` + `it_helpdesk_faq.txt` | Canonical local file | sai keyword retrieval / drift nội dung | eval before/after + grading_run |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định dạng `<doc_id>_<seq>_<hash16>` |
| doc_id | string | Có | Phải thuộc allowlist trong `contracts/data_contract.yaml` |
| chunk_text | string | Có | Văn bản sau clean (dedupe, stale fix, quality filters) |
| effective_date | date | Có | Chuẩn ISO `YYYY-MM-DD` |
| exported_at | datetime | Có | ISO-8601 từ nguồn export |

Ràng buộc nghiệp vụ chính:
- `chunk_text` tối thiểu 8 ký tự.
- `doc_id` nằm trong tập cho phép (hiện gồm cả `access_control_sop`).
- `hr_leave_policy` phải thỏa cut-off versioning (>= `2026-01-01` theo contract).

---

## 3. Quy tắc quarantine vs drop

- **Quarantine (mặc định):** Không drop im lặng. Bản ghi lỗi chuyển vào `artifacts/quarantine/quarantine_<run_id>.csv` kèm `reason`.
- **Các reason điển hình:** `unknown_doc_id`, `missing_effective_date`, `invalid_effective_date_format`, `duplicate_chunk_text`, `stale_hr_policy_effective_date`, `missing_or_invalid_exported_at`, ...
- **Review ownership:** Tech Lead (Nhật) + Cleaning Owner (Khánh) duyệt nguyên nhân trước khi chấp nhận re-ingest.
- **Re-ingest policy:** Chỉ merge lại sau khi fix ở source hoặc rule được cập nhật có justification trong group report.

Luồng phê duyệt:
1. Xác nhận reason trong quarantine + log cùng `run_id`.
2. Quyết định fix ở source hay fix rule.
3. Chạy lại `etl_pipeline.py run` và so sánh delta `cleaned_records/quarantine_records`.
4. Cập nhật evidence trong `docs/quality_report.md`.

---

## 4. Phiên bản & canonical

- **Source of Truth:** Chính sách `policy_refund_v4` là bản cập nhật nhất cho năm 2026.
- **Canonical sources (repo-relative):**
  - `data/docs/policy_refund_v4.txt`
  - `data/docs/sla_p1_2026.txt`
  - `data/docs/it_helpdesk_faq.txt`
  - `data/docs/hr_leave_policy.txt`
  - `data/docs/access_control_sop.txt`
- **Allowlist hiện hành:** `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`, `access_control_sop`.
- **SLA freshness:** 24 giờ (đo theo `latest_exported_at`; nhóm đã mở rộng thêm publish boundary để quan sát).

---

## 5. Owner, SLA, và vận hành

- **Owner team:** `C401-D6 / Tech Lead + Ingestion Owner (Le Huy Hong Nhat)` (đồng bộ `contracts/data_contract.yaml`).
- **Alert channel (mô phỏng):** `slack:#c401-d6-data-alert`.
- **SLA breach handling:**
  - `age_hours > sla_hours` => xem là stale source, cần triage theo runbook.
  - Nếu publish boundary PASS nhưng source boundary FAIL: pipeline publish đúng, dữ liệu nguồn chưa được refresh.
