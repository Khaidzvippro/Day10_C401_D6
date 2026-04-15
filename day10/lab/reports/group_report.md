# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** D401 - D6  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Lê Huy Hồng Nhật | Tech Lead | nhat050403@gmail.com |
| Nguyễn Quốc Khánh | Retrieval Owner | khanhnq352005@gmail.com |
| Lê Nguyễn Quang Khải | Retrieval Owner | tuankhaidx2003@gmail.com |
| Võ Văn Tấn | Eval Owner | tana2k53nvt@gmail.com |
| Đào Công Thành | Eval Owner | lcthanh.htvn@gmail.com |
| Nguyễn Quế Sơn | Documentation Owner | sonnguyenque5@gmail.com |

**Ngày nộp:** 15/04/2026  
**Repo:** Khaidzvippro/Day10_C401_D6  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

_________________

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

_________________

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| Rule 7: Invalid exported_at | 0 quarantine | Tăng khi date sai format | `cleaning_rules.py` |
| Rule 8: Short/Trivial context | 0 quarantine | Loại bỏ chunk rác/ngắn | `cleaning_rules.py` |
| Rule 9: Corrupted encoding (BOM) | 0 quarantine | Loại bỏ ký tự lỗi | `cleaning_rules.py` |
| Rule 11: Max chunk length | 0 quarantine | Cắt giảm context quá dài | `cleaning_rules.py` |

**Rule chính (baseline + mở rộng):**

- **Rule 7:** Kiểm soát ISO-8601 format cho `exported_at` để đảm bảo tính đồng nhất thời gian.
- **Rule 8:** Lọc bỏ các chunk quá ngắn (< 20 ký tự) hoặc không chứa thông tin hữu ích (toàn số/ký hiệu).
- **Rule 9:** Phát hiện và loại bỏ các ký tự lỗi encoding (BOM, NULL) gây sai lệch vector embedding.
- **Rule 11:** Giới hạn độ dài tối đa của chunk (8000 ký tự) để tối ưu hóa context window cho LLM.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Sử dụng cờ `--skip-validate` trong kịch bản Sprint 3 để quan sát hệ thống vẫn cho phép nạp dữ liệu lỗi vào Vector DB, từ đó so sánh hiệu quả của Quality Gate.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

_________________

**Kết quả định lượng (từ CSV / bảng):**

_________________

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

_________________

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- …
