# Quality report — Lab Day 10 (C401 - D6)

**run_id:** `final-fix`  
**Ngày:** 15/04/2026

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (Anomaly `inject-bad`) | Sau (Final Fix `final-fix`) | Ghi chú |
|--------|-------|-----|---------| 
| raw_records | 10 | 10 | Dữ liệu mẫu ban đầu |
| cleaned_records | 6 | 6 | Số lượng chunk hợp lệ sau 11 rule lọc |
| quarantine_records | 4 | 4 | 4 bản ghi bị loại (xem chi tiết bên dưới) |
| Expectation halt? | **FAIL** (E3: violations=1, skip) | **PASS** (9/9 OK) | Quality Gate hoạt động đúng |
| embed_prune_removed | — | 1 (khi rerun sau inject) | Vector stale bị loại |

**Chi tiết 4 bản ghi quarantine (từ `artifacts/quarantine/quarantine_final-fix.csv`):**

| Row | doc_id | Reason | Mô tả |
|-----|--------|--------|-------|
| 2 | `policy_refund_v4` | `duplicate_chunk_text` | Nội dung trùng lặp (Rule 5 baseline) |
| 5 | `policy_refund_v4` | `missing_effective_date` | Thiếu `effective_date` (Rule 4 baseline) |
| 7 | `hr_leave_policy` | `stale_hr_policy_effective_date` | Chính sách HR 2025 lỗi thời (Rule 3 baseline) |
| 9 | `legacy_catalog_xyz_zzz` | `unknown_doc_id` | Doc_id không trong allowlist (Rule 1 + Rule 10 mở rộng) |

---

## 2. Before / after retrieval (bắt buộc)

> Bằng chứng thực nghiệm so sánh hiệu quả xử lý dữ liệu.

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước (Anomaly `inject-bad`):** `hits_forbidden=yes` — context chứa thông tin "14 ngày làm việc" sai lệch.  
**Sau (Final Fix `final-fix`):** `hits_forbidden=no` — thông tin được fix thành 7 ngày, LLM-judge score=1 (Faithful).

**Bằng chứng artifact:**
- `artifacts/eval/eval_inject_bad.csv` — kết quả retrieval khi inject
- `artifacts/eval/eval_after_clean.csv` — kết quả retrieval sau clean
- `artifacts/eval/llm_judge_after_clean.csv` — LLM-judge đánh giá Faithful
- `artifacts/eval/grading_run.jsonl` — 3 câu grading đều PASS

**Merit (khuyến nghị):** versioning HR — `q_leave_version`  
**Trước:** Chứa các chính sách năm 2025 (10 ngày phép).  
**Sau:** Chỉ chứa các chính sách năm 2026 (12 ngày phép) nhờ Rule 3 trong `cleaning_rules.py`.

---

## 3. Expectation suite (E1–E9)

**Baseline (E1–E6):** do instructor cung cấp — tất cả PASS trên clean run.

**Mở rộng (E7–E9):** do Nguyễn Tuấn Khải bổ sung trong `quality/expectations.py`:

| Expectation | Severity | Kết quả clean | Kết quả inject | Log evidence |
|-------------|----------|---------------|----------------|-------------|
| E7: `exported_at_iso_format` | **halt** | OK (`count=0`) | FAIL nếu bypass cleaning | Đảm bảo freshness check parse được |
| E8: `short_chunk_ratio_under_10pct` | **warn** | OK (`ratio=0.00%`) | WARN khi inject chunk ngắn | Phát hiện cleaning chưa đủ mạnh |
| E9: `doc_id_in_allowlist` | **halt** | OK (`count=0`) | FAIL nếu doc lạ lọt qua | Đồng bộ với Rule 10 của Khánh |

**Ví dụ FAIL thực tế (log `inject-bad`):**
```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed (chỉ dùng cho demo Sprint 3).
```

---

## 4. Freshness & monitor

- **SLA:** 24 giờ (cấu hình `contracts/data_contract.yaml`).
- **Kết quả:** `FAIL` — dữ liệu mẫu `exported_at=2026-04-10T08:00:00`, trễ ~120 giờ.
- **Giải thích:** Đây là **hành vi mong muốn** để mô phỏng tình trạng data stale trên data mẫu cũ. Hệ thống cảnh báo hoạt động chính xác.
- **Log evidence:** `freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.095, "sla_hours": 24.0}`

---

## 5. Corruption Simulation (Anomaly Test)

Chúng tôi thực hiện kịch bản hỏng dữ liệu có chủ đích bằng lệnh:
```bash
python etl_pipeline.py run --run-id anomaly-test --no-refund-fix --skip-validate
```

**Các lỗi được inject:**
1. Giữ nguyên cửa sổ hoàn tiền 14 ngày (Stale Data) — E3 FAIL (halt) nhưng `--skip-validate` cho phép tiếp tục.
2. Chấp nhận các bản ghi có định dạng ngày tháng không chuẩn.
3. Bỏ qua việc lọc các phiên bản chính sách nhân sự cũ (2025).

**Kết quả:** Vector DB chứa thông tin sai → retrieval trả `hits_forbidden=yes` → chứng minh tầm quan trọng của Quality Gate.

---

## 6. Hạn chế & việc chưa làm

- Chưa tích hợp auto-alert qua Slack/Email khi Freshness check FAIL.
- Cần mở rộng bộ Rule để xử lý các tài liệu PDF phức tạp hơn trong tương lai.
- Số liệu chỉ test trên 10 bản ghi mẫu; cần benchmark trên dataset lớn hơn.
- `chunk_id` phụ thuộc `seq` — cần kiểm tra lại khi thay đổi logic sắp xếp.

