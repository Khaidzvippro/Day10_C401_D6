# Quality report — Lab Day 10 (nhóm)

**run_id:** inject-bad / fix-good
**Ngày:** 15/04/2026

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (inject-bad) | Sau (fix-good) | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 10 | 10 | Tổng dòng raw csv |
| cleaned_records | 6 | 6 | Tổng sau chunking |
| quarantine_records | 4 | 4 | Số lượng vi phạm |
| Expectation halt? | Có (FAIL) | Không (OK) | Cảnh báo Refund 14-days (version cũ) đã bị filter thành công |

---

## 2. Before / after retrieval (bắt buộc)

> Đính kèm 2 file: `artifacts/eval/after_inject_bad.csv` (trước) và `artifacts/eval/after_fix_good.csv` (sau).

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước (lỗi policy-v3):** Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn (ghi chú: bản sync cũ policy-v3 — lỗi migration). *(hits_forbidden=yes)*
**Sau (đúng policy-v4):** Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng. *(hits_forbidden=no)*

**Merit (khuyến nghị):** versioning HR — `q_leave_version` (`contains_expected`, `hits_forbidden`, cột `top1_doc_expected`)
**Trước:** hr_leave_policy | Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026. (contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes)
**Sau:** hr_leave_policy | Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026. (contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes)

---

## 3. Freshness & monitor

> Kết quả `freshness_check`: **FAIL**  
**SLA chọn:** 24h  
**Giải thích:** Data bị export có `latest_exported_at` vào lúc "2026-04-10T08:00:00" nên age là 121h > SLA 24h quy định. Giúp cảnh báo team source export đồng bộ bị dán độ trễ quá lâu so với hiện hành. Do test là mốc 15/04 báo fail.

---

## 4. Corruption inject (Sprint 3)

> **Mô tả hỏng dữ liệu:** Dùng command `--no-refund-fix` để cho lọt văn bản refund `policy-v3` bị lỗi "14 ngày" vào DB do lỗi đồng bộ, cùng lúc bypass quá trình validate `--skip-validate`.  
**Cách phát hiện:** Do có rule `refund_no_stale_14d_window` trong expectations, khi disable bypass, pipeline đã halt đúng lỗi và vector chunk của text này trả về `hits_forbidden = yes` trong hàm log eval khi user truy vấn RAG của mình. 

---

## 5. Hạn chế & việc chưa làm

- Cần chạy thêm file test `grading_questions.json` sau 17:00.
