# Quality report — Lab Day 10 (nhóm D401 - D6)

**run_id:** `[PLACEHOLDER]` (Lấy từ Tech Lead sau khi chạy pipeline)
**Ngày:** 15/04/2026

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (Inject) | Sau (Clean) | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 10 | 10 | Dữ liệu mẫu ban đầu |
| cleaned_records | `[TBD]` | `[TBD]` | Sau khi qua bộ lọc cleaning_rules.py |
| quarantine_records | `[TBD]` | `[TBD]` | Bản ghi bị loại bỏ do lỗi |
| Expectation halt? | FAIL | PASS | Kiểm tra Quality Gate |

---

## 2. Before / after retrieval (bắt buộc)

> Bằng chứng thực nghiệm so sánh hiệu quả của việc xử lý dữ liệu.

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước (Inject):** Hệ thống trả về thông tin "14 ngày làm việc" (do dùng dữ liệu cũ chưa fix).
**Sau (Clean):** Hệ thống trả về thông tin "7 ngày làm việc" và có tag `[cleaned: stale_refund_window]`.

**Merit (khuyến nghị):** versioning HR — `q_leave_version`
**Trước:** Chứa các chính sách năm 2025 (10 ngày phép).
**Sau:** Chỉ chứa các chính sách năm 2026 (12 ngày phép) nhờ Rule 3 trong cleaning_rules.

---

## 3. Freshness & monitor

- **SLA:** 24 giờ.
- **Kết quả:** `[TBD]` (Cần chạy `freshness_check.py` trên manifest thật).

---

## 4. Corruption inject (Sprint 3)

Chúng tôi thực hiện kịch bản hỏng dữ liệu có chủ đích bằng lệnh:
`python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`

**Các lỗi được inject:**
1. Giữ nguyên cửa sổ hoàn tiền 14 ngày (Stale Data).
2. Chấp nhận các bản ghi có định dạng ngày tháng không chuẩn.
3. Bỏ qua việc lọc các phiên bản chính sách nhân sự cũ (2025).

---

## 5. Hạn chế & việc chưa làm

- Chưa tích hợp auto-alert qua Slack/Email khi Freshness check FAIL.
- Cần mở rộng bộ Rule để xử lý các tài liệu PDF phức tạp hơn trong tương lai.
