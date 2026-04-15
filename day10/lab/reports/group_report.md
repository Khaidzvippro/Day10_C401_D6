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
Pipeline thực hiện chuỗi: Ingest CSV -> Clean (11 rule) -> Validate (9 expectations) -> Embed (ChromaDB) -> Freshness check. Hệ thống hỗ trợ so sánh giữa chế độ chuẩn (`khai-clean`) và chế độ kiểm thử (`inject-bad`).

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**
`python etl_pipeline.py run --run-id khai-clean`

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
Chúng tôi sử dụng lệnh `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate` để cố ý giữ lại dữ liệu stale (14 ngày) và bỏ qua các bước kiểm tra chất lượng.

**Kết quả định lượng (từ CSV / bảng):**
- **Inject:** `hits_forbidden=yes` cho câu hỏi hoàn tiền (kết quả retrieval chứa thông tin cũ 14 ngày).
- **Clean:** `hits_forbidden=no`. Đặc biệt, chúng tôi triển khai **LLM-judge** (GPT-4o-mini) đạt điểm `llm_score=1` (Faithful) cho 100% các câu hỏi kiểm thử sau clean.
- **Metric:** Pruning layer loại bỏ chính xác 1 vector cũ khi rerun bản sạch (`embed_prune_removed=1`).

---

**Freshness & Monitoring:**
SLA được thiết lập là 24 giờ. Kết quả check trên mẫu dữ liệu ngày 10/04 là `FAIL` (trễ 119 giờ), chứng minh hệ thống cảnh báo hoạt động chính xác khi gặp dữ liệu cũ.

---

Dữ liệu từ pipeline này phục vụ trực tiếp cho các Agent Day 09, giúp tránh lỗi trả lời sai về quy định hoàn tiền đã lỗi thời.

---

## 6. Rủi ro còn lại & việc chưa làm

- …
