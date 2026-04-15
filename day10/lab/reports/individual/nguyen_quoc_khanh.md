# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Quốc Khánh
**Vai trò:** Cleaning Owner (Sprint 1-2)
**Ngày nộp:** 15/04/2026
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
- `transform/cleaning_rules.py`: Tái cấu trúc pipeline clean data, thêm 4 rule mới (`_check_invalid_exported_at`, `_check_short_or_trivial`, `_check_corrupted_encoding` và `_check_too_long`). Bổ sung `access_control_sop` vào cấu hình `ALLOWED_DOC_IDS`.
- `quality/expectations.py`: Cập nhật mã nguồn báo cáo lỗi cho các rule bị vi phạm.
- `docs/quality_report.md`: Tổng hợp bảng thông số Group Report Sprint 3.

**Kết nối với thành viên khác:**
Tôi nhận file CSV Raw từ Ingestion Owner (Nhật), phân tích để bổ sung các filter bắt rác, sau đó trả output ra `artifacts/cleaned/` cho Tấn (Embed Owner) đẩy vào ChromaDB. Tôi cung cấp bảng `metric_impact` cho nhóm tổng hợp.

**Bằng chứng (commit / comment trong code):**
Commit trên nhánh `khanhnq`: `feat(embedding): switch to OpenAI...` và `chore(eval): generate test...`. Code cụ thể nằm ở `clean_rows()` trong `cleaning_rules.py`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Về độ dài Chunk (Token Limits):** Tôi nhận thấy việc đưa vào RAG những chunk văn bản quá ngắn (ví dụ chỉ <8 ký tự) hoặc quá dài (>1000 ký tự) đều gây lãng phí chi phí embedding và làm nhiễu không gian vector. Do đó tôi thiết kế Rule 8 & 11 (ngưỡng min 8, max 1000 characters). Những text này sẽ bị đẩy vào **quarantine_records** thay vì lưu trữ. Thay vì dùng `halt` làm chết toàn bộ luồng, tôi quyết định xử lý theo dạng **warn** (log ra và loại bỏ tĩnh ở Python layer) để không chắn đường các văn bản hợp lệ khác trong cùng lô batch. 

**Về định dạng exported_at (ISO-8601):** Nếu `exported_at` bị trống hoặc sai định dạng múi giờ, hàm theo dõi Freshness SLA (Sprint 4) sẽ bị crash hoặc chạy sai. Quyết định của tôi là tạo Rule 7 sử dụng RegEx `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?` bắt buộc match toàn vẹn.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Sự cố Refund Stale Data (Bypass Rule):** Để chứng minh hiệu quả của Rule 6 (Business Fix), tôi đã cố ý bypass logic convert 14 ngày làm việc về 7 ngày bằng lệnh `--no-refund-fix --skip-validate`.

**Triệu chứng & Hệ quả:** Việc loại bỏ rule bảo vệ này ngay lập tức làm bài test chuẩn `grading_questions.json` thất bại thảm hại ở câu hỏi đầu tiên `gq_d10_01`. Metric chấm file JSONL kết quả cho thấy `hits_forbidden = true` (Vector RAG nhặt nguyên đoạn dính "14 ngày làm việc" lạc hậu về để trả lời user). Chi tiết sự cố tôi đã trích xuất ra file kết quả thực thi lỗi tại `reports/individual/anomaly_test_result.jsonl`. Quá trình pipeline chạy cũng phát hiện lỗi này làm trigger hàm Expectation từ Quality layer báo log: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`.

**Cách Fix:** Việc thiết lập bắt buộc đoạn pipeline phải giữ vững Rule Clean Replace String và không chạy bypass Expectation (`--skip-validate`) đã giúp loại bỏ dữ liệu sai từ trứng nước, trả lại kết quả `hits_forbidden = false`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**run_id:** `inject-bad` (trước) vs `fix-good` (sau)
**Log Metric:** `expectation[refund_no_stale_14d_window]` bị `FAIL (halt) :: violations=1` khi nhận dữ liệu rác, và trạng thái `OK` khi được fix rule. `quarantine_records` nhận 4 lỗi.

**CSV (`after_fix_good.csv`):** 
- Câu hỏi `q_refund_window`: `hits_forbidden` đã chuyển từ `yes` (trước fix) sang `no`. 
- Top 1 Document trả về đúng quy định mới: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng." thay vì dính lỗi policy cũ 14 ngày.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ phát triển cơ chế cảnh báo tự động `Slack/Teams Webhook`. Khi tệp CSV sinh ra có `quarantine_records` vượt mức 10% tổng số `raw_records`, một alert kèm snippet mã lỗi (ví dụ: `ValueError: Corrupted Encoding BOM`) sẽ bắn thẳng vào kênh Data Engineer để đội ngũ Data Sources có thể kiểm tra định dạng export phía thượng nguồn theo thời gian thực thay vì đợi chạy file eval.
