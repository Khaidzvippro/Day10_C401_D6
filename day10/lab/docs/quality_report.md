# Quality report — Lab Day 10 (nhóm)

**run_id:** fix-good  
**Ngày:** 15/04/2026

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (khi inject lỗi) | Sau (khi fix clean rules) | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 10 | 10 | Đọc toàn bộ file export bẩn |
| cleaned_records | 6 | 6 | Tổng data đẩy vào vectordb sau khi lọc |
| quarantine_records | 4 | 4 | Số lượng vi phạm các rule filter |
| Expectation halt? | FAIL (bị chặn) | PASS (không bị halt) | Tắt cờ fix làm expectation chặn thành công document lỗi |

---

## 2. Before / after retrieval (bắt buộc)

> File kết quả được xuất ra tại: 
> - Trước: `artifacts/eval/after_inject_bad.csv`
> - Sau: `artifacts/eval/after_fix_good.csv`

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước:** policy_refund_v4 | Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn (ghi chú: bản sync cũ policy-v3 — lỗi migration). *(hits_forbidden=yes)*  
**Sau:** policy_refund_v4 | Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng. *(hits_forbidden=no)*

**Merit (khuyến nghị):** versioning HR — `q_leave_version` (`contains_expected`, `hits_forbidden`, cột `top1_doc_expected`)  
**Trước:** hr_leave_policy | Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026. *(contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes)*  
**Sau:** hr_leave_policy | Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026. *(contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes)*

---

## 3. Freshness & monitor

> Kết quả `freshness_check`: **FAIL**  

**Giải thích SLA bạn chọn:**  
Chúng tôi thiết lập mức freshness SLA là 24 giờ. Dữ liệu trong đợt export gần nhất có `latest_exported_at` cao nhất là `2026-04-10T08:00:00`. Vì ngày thực thi test hiện tại là `15/04/2026`, độ trễ của dữ liệu (age_hours) là hơn ~121 giờ (vượt 24h). Expectation cảnh báo **FAIL** giúp hệ thống Data Observability chặn các document quá lạc hậu tự động tiêm vào RAG.

---

## 4. Corruption inject (Sprint 3)

> **Mô tả cố ý làm hỏng dữ liệu kiểu gì và cách phát hiện:**
- **Mô tả:** Chạy pipeline với cờ `--no-refund-fix` để ép lọt policy_refund_v4 cũ (phiên bản 14 ngày) cộng thêm cờ `--skip-validate` để bỏ qua lỗi Expectation và tiến hành cho Embed vào ChromaDB. Trực tiếp làm ô nhiễm Vector Database với dữ liệu lạc hậu.
- **Cách phát hiện:** 
  1. Khi đánh giá (eval), document bẩn xuất hiện ngay ở Top 1 Retrieval khiến `hits_forbidden` báo `yes`. 
  2. Nếu không bypass, hàm Expectation `refund_no_stale_14d_window` sẽ tự động quăng lỗi báo có 1 violations và halt ngay ETL workflow trước bước Embed.

---

## 5. Hạn chế & việc chưa làm

- Toàn bộ checklist theo nhóm đã được chạy thành công cùng kết quả grading script xuất sắc đạt hết các metric testing (File `grading_run.jsonl` đã gen ra thành công đầy đủ flag đúng).
- Không còn việc tồn đọng (đã sẵn sàng nộp Artifacts trước 18:00).
