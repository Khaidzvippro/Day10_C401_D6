# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** C401 - D6  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Lê Huy Hồng Nhật | Tech Lead + Ingestion Owner | nhat050403@gmail.com |
| Nguyễn Quốc Khánh | Cleaning Owner | khanhnq352005@gmail.com |
| Nguyễn Tuấn Khải | Quality / Expectation Owner | tuankhaidx2003@gmail.com |
| Phan Văn Tấn | Embed & Eval Owner | tana2k53nvt@gmail.com |
| Lê Công Thành | Monitoring & Docs Owner | lcthanh.htvn@gmail.com |
| Nguyễn Quế Sơn | Documentation & Report Owner | sonnguyenque5@gmail.com |

**Ngày nộp:** 15/04/2026  
**Repo:** Khaidzvippro/Day10_C401_D6  
**run_id chính:** `final-fix` (bản sạch) · `inject-bad` / `anomaly-test` (bản inject lỗi)

---

## 1. Pipeline tổng quan

**Nguồn raw:** `data/raw/policy_export_dirty.csv` — 10 bản ghi mô phỏng export từ hệ thống CS/IT Helpdesk, chứa nhiều loại lỗi có chủ đích (stale date, doc_id lạ, encoding BOM, chunk rỗng, duplicate).

**Chuỗi lệnh chạy end-to-end:**
```bash
# Bản sạch cuối cùng
python etl_pipeline.py run --run-id final-fix

# Bản inject lỗi (Sprint 3 — giả lập sự cố)
python etl_pipeline.py run --run-id anomaly-test --no-refund-fix --skip-validate
```

**Luồng xử lý:** Ingest CSV → Clean (11 rule trong `transform/cleaning_rules.py`) → Validate (9 expectations trong `quality/expectations.py`) → Embed (ChromaDB collection `day10_kb`) → Manifest → Freshness check.

**`run_id`** được ghi ở dòng đầu tiên của mỗi log file (`artifacts/logs/run_<run_id>.log`), kèm 4 metric bắt buộc: `raw_records`, `cleaned_records`, `quarantine_records`, `embed_upsert`.

**Số liệu đại diện (run `final-fix`):**
- `raw_records=10` → `cleaned_records=6` → `quarantine_records=4`
- Expectation: 9/9 PASS → Embed: 6 chunks upsert → Freshness: FAIL (SLA 24h, thực tế 120h)

> [!TIP]
> Chi tiết về kịch bản anomaly và danh mục artifacts: xem [README_ANOMALY.md](reports/README_ANOMALY.md).

---

## 2. Cleaning & Expectation

### 2a. Cleaning Rules mới (≥3 rule — Khánh)

Baseline có 6 rule (allowlist doc_id, normalize ngày, HR stale, refund 14→7 ngày, dedupe chunk_text, missing fields). Khánh bổ sung **5 rule mới** (Rule 7–11):

| Rule mới | Mô tả | Trước (clean run) | Sau (inject/test) | Chứng cứ |
|----------|-------|-------------------|-------------------|----------|
| **Rule 7:** Invalid `exported_at` | Quarantine row có `exported_at` rỗng/sai ISO-8601 | 0 quarantine (data sạch đã pass) | +N quarantine khi inject row `exported_at=""` | `cleaning_rules.py`, reason=`missing_or_invalid_exported_at` |
| **Rule 8:** Short/Trivial chunk | Loại chunk < 20 ký tự hoặc toàn số/ký hiệu | 0 quarantine (data mẫu chunks đủ dài) | +N khi inject chunk `"FAQ"` hoặc `"123"` | `cleaning_rules.py`, reason=`chunk_text_too_short_or_trivial` |
| **Rule 9:** Corrupted encoding | Phát hiện BOM (`\ufeff`), NULL byte (`\x00`) | 0 (data mẫu không chứa BOM) | +N khi inject ký tự lỗi | `cleaning_rules.py`, reason=`corrupted_text_encoding` |
| **Rule 10:** Unknown doc_id | Mở rộng allowlist thêm `access_control_sop`; quarantine doc_id ngoài allowlist | 1 quarantine (`legacy_catalog_xyz_zzz`) | Ngăn doc_id lạ lọt vào embed | `cleaning_rules.py`, reason=`unknown_doc_id` |
| **Rule 11:** Max chunk length | Chặn chunk > 8000 ký tự | 0 (data mẫu chunks ngắn) | +N khi inject chunk siêu dài | `cleaning_rules.py`, reason=`chunk_text_too_long` |

**Tổng hợp metric_impact trên data mẫu (10 raw → 6 cleaned → 4 quarantine):**
- `duplicate_chunk_text`: 1 record (row 2 trùng nội dung)
- `missing_effective_date`: 1 record (row 5 thiếu ngày)
- `stale_hr_policy_effective_date`: 1 record (row 7, HR 2025 bị loại)
- `unknown_doc_id`: 1 record (row 9, `legacy_catalog_xyz_zzz` không trong allowlist)

### 2b. Expectation mới (≥2 expectation — Khải)

Baseline có 6 expectation (E1–E6). Khải bổ sung **3 expectation mới** (E7–E9):

| Expectation | Severity | Mô tả | Kết quả clean run | Kết quả inject |
|-------------|----------|-------|-------------------|----------------|
| **E7:** `exported_at_iso_format` | **halt** | Double-check `exported_at` đúng ISO-8601 datetime sau cleaning | OK (`invalid_exported_at_count=0`) | FAIL nếu bypass cleaning |
| **E8:** `short_chunk_ratio_under_10pct` | **warn** | Tỷ lệ chunk < 20 ký tự không vượt 10% tổng cleaned | OK (`ratio=0.00%`) | WARN nếu inject nhiều chunk ngắn |
| **E9:** `doc_id_in_allowlist` | **halt** | Tất cả `doc_id` phải nằm trong `ALLOWED_DOC_IDS` (đồng bộ với cleaning Rule 10) | OK (`illegal_doc_id_count=0`) | FAIL nếu doc lạ lọt qua |

**Ví dụ expectation FAIL thực tế (log `inject-bad`):**
```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed (chỉ dùng cho demo Sprint 3).
```
→ Pipeline phát hiện 1 violation (chunk vẫn chứa "14 ngày làm việc") nhưng tiếp tục embed vì dùng `--skip-validate`, tạo bằng chứng before/after.

---

## 3. Before / After — Ảnh hưởng retrieval

**Kịch bản inject (Sprint 3):**
```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```
Cố ý giữ nguyên cửa sổ hoàn tiền 14 ngày (stale) và bỏ qua Quality Gate.

**Kết quả định lượng:**

| Metric | Inject (`inject-bad`) | Clean (`final-fix`) | Nguồn |
|--------|----------------------|---------------------|-------|
| `hits_forbidden` (q_refund_window) | **yes** (chứa "14 ngày") | **no** | `artifacts/eval/eval_inject_bad.csv` vs `eval_after_clean.csv` |
| `contains_expected` (q_refund_window) | true | true | Grading JSONL |
| LLM-judge score (GPT-4o-mini) | Unfaithful | **1.0** (Faithful) | `artifacts/eval/llm_judge_after_clean.csv` |
| `embed_prune_removed` | — | **1** (loại vector stale) | Log `sprint3-clean` |

**Bằng chứng Grading JSONL (`artifacts/eval/grading_run.jsonl`):**
- `gq_d10_01`: `contains_expected=true`, `hits_forbidden=false` ✅
- `gq_d10_02`: `contains_expected=true`, `hits_forbidden=false` ✅
- `gq_d10_03`: `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` ✅ (Merit)

---

## 4. Freshness & Monitoring

- **SLA:** 24 giờ (cấu hình trong `contracts/data_contract.yaml` và env `FRESHNESS_SLA_HOURS`).
- **Kết quả:** `FAIL` — dữ liệu mẫu `exported_at=2026-04-10T08:00:00`, trễ ~120 giờ so với thời điểm chạy.
- **Giải thích:** FAIL là **hành vi mong muốn** trên data mẫu cũ, chứng minh hệ thống cảnh báo hoạt động chính xác. Trong production, SLA sẽ áp dụng cho data snapshot mới nhất.
- **Chi tiết vận hành:** Xem `docs/runbook.md` (5 mục Symptom → Detection → Diagnosis → Mitigation → Prevention).

---

## 5. Liên hệ Day 09

Dữ liệu từ pipeline Day 10 phục vụ trực tiếp cho các Agent Day 09 (Multi-Agent Orchestration):
- Day 09 trả lời câu hỏi người dùng qua RAG; Day 10 đảm bảo **corpus đã qua clean, validate và embed** với phiên bản đúng.
- Chroma collection `day10_kb` là snapshot publish mới, thay thế corpus cũ có thể chứa dữ liệu stale.
- Canonical knowledge bám theo `data/docs/` và `contracts/data_contract.yaml` (5 doc_id: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`, `access_control_sop`).
- Nếu không có bước clean Day 10, Agent Day 09 sẽ trả lời sai về quy định hoàn tiền (14 ngày thay vì 7 ngày) — đã chứng minh bằng kịch bản inject.

---

## 6. Rủi ro còn lại & việc chưa làm

- **ChromaDB / Model embedding lỗi:** Nếu model `all-MiniLM-L6-v2` hoặc ChromaDB crash, bước publish cuối thất bại dù manifest/log tồn tại — cần retry logic hoặc alert riêng.
- **Freshness FAIL trên production:** Hiện chưa có auto-alert (Slack/Email) khi freshness check FAIL; phụ thuộc vào việc chạy thủ công `etl_pipeline.py freshness`.
- **`chunk_id` phụ thuộc `seq`:** Nếu logic sắp xếp/dedupe thay đổi giữa hai run, `chunk_id` có thể đổi → prune xóa nhầm vector hợp lệ. Cần test kỹ khi mở rộng rule mới.
- **Expectation E7/E9 halt trên clean data:** Nếu cleaning layer bị bypass hoặc transform làm hỏng format, pipeline sẽ dừng trước embed — đây là thiết kế có chủ đích nhưng cần monitoring log.
- **Mở rộng quy mô:** Hiện chỉ test trên 10 bản ghi mẫu; cần benchmark với dataset lớn hơn (100+ chunks) để đánh giá hiệu năng cleaning + embed.

