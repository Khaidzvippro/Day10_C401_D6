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

**Sơ đồ kiến trúc pipeline:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA PIPELINE ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   SOURCES    │───▶│  INGESTION   │───▶│   CLEANING   │───▶│   QUALITY    │
│              │    │              │    │              │    │              │
│ • CSV export │    │ • Load CSV   │    │ • 11 rules   │    │ • 9 expect   │
│ • 5 docs     │    │ • Log raw    │    │ • Quarantine │    │ • Halt/Warn  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                           │                   │                   │
                           ▼                   ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                    │   LOGS      │     │  CLEANED    │     │  QUARANTINE │
                    │   run_id    │     │   CSV       │     │   CSV       │
                    └─────────────┘     └─────────────┘     └─────────────┘
                                                              │
                                                              ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   MONITOR    │◀───│   PUBLISH    │◀───│   EMBEDDING  │◀───│   VALIDATE   │
│              │    │              │    │              │    │              │
│ • Freshness  │    │ • Manifest   │    │ • ChromaDB   │    │ • Pass/Fail  │
│ • 2-boundary │    │ • Run ID     │    │ • Upsert     │    │ • Prune      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  MANIFESTS  │     │  CHROMA DB  │
                    │   JSON      │     │  day10_kb   │
                    └─────────────┘     └─────────────┘

RANH GIỚI LỚP:
├─ Ingestion Layer:  Đọc raw → log → pass to cleaning
├─ Cleaning Layer:   Apply rules → quarantine → pass to quality
├─ Quality Layer:    Validate expectations → halt/warn → pass to embed
├─ Embedding Layer:  Vectorize → upsert → prune → pass to publish
├─ Publish Layer:    Write manifest → update freshness check
└─ Monitor Layer:    Check freshness (2 boundary) → alert
```

**Chuỗi lệnh chạy end-to-end:**
```bash
# Bản sạch cuối cùng
python etl_pipeline.py run --run-id final-fix

# Bản inject lỗi (Sprint 3 — giả lập sự cố)
python etl_pipeline.py run --run-id anomaly-test --no-refund-fix --skip-validate
```

**Luồng xử lý chi tiết:**

1. **Ingestion (etl_pipeline.py - cmd_run):**
   - Đọc `policy_export_dirty.csv` → 10 rows
   - Log `raw_records=10` với `run_id=final-fix`
   - Pass raw data sang cleaning layer

2. **Cleaning (transform/cleaning_rules.py - clean_rows):**
   - Apply 11 rules (6 baseline + 5 mới)
   - Quarantine 4 rows (duplicate, missing date, stale HR, unknown doc_id)
   - Log `cleaned_records=6`, `quarantine_records=4`
   - Pass cleaned data sang quality layer

3. **Quality (quality/expectations.py - run_expectations):**
   - Validate 9 expectations (6 baseline + 3 mới)
   - All PASS → không halt
   - Pass validated data sang embedding layer

4. **Embedding (etl_pipeline.py - cmd_embed_internal):**
   - Vectorize 6 chunks với OpenAI `text-embedding-3-small`
   - Upsert vào ChromaDB collection `day10_kb`
   - Prune 1 vector cũ (stale refund 14 ngày)
   - Log `embed_upsert count=6`, `embed_prune_removed=1`

5. **Publish (etl_pipeline.py - cmd_run):**
   - Write manifest `manifest_final-fix.json`
   - Log `manifest_written=artifacts/manifests/manifest_final-fix.json`

6. **Monitor (monitoring/freshness_check.py - check_manifest_freshness):**
   - Check freshness SLA (24 giờ)
   - Result: FAIL (120h > 24h) - *kỳ vọng của lab*
   - Log `freshness_check=FAIL`

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

| Rule mới | Mô tả | Logic chi tiết | Trước (clean run) | Sau (inject/test) | Chứng cứ |
|----------|-------|----------------|-------------------|-------------------|----------|
| **Rule 7:** Invalid `exported_at` | Quarantine row có `exported_at` rỗng/sai ISO-8601 | Check RegEx `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z\|[+-]\d{2}:\d{2})?` | 0 quarantine (data sạch đã pass) | +N quarantine khi inject row `exported_at=""` | `cleaning_rules.py`, reason=`missing_or_invalid_exported_at` |
| **Rule 8:** Short/Trivial chunk | Loại chunk < 20 ký tự hoặc toàn số/ký hiệu | Check `len(text_stripped) < 20` hoặc `alpha_count == 0` | 0 quarantine (data mẫu chunks đủ dài) | +N khi inject chunk `"FAQ"` hoặc `"123"` | `cleaning_rules.py`, reason=`chunk_text_too_short_or_trivial` |
| **Rule 9:** Corrupted encoding | Phát hiện BOM (`\ufeff`), NULL byte (`\x00`) | Check `'\ufeff' in text or '\x00' in text` | 0 (data mẫu không chứa BOM) | +N khi inject ký tự lỗi | `cleaning_rules.py`, reason=`corrupted_text_encoding` |
| **Rule 10:** Unknown doc_id | Mở rộng allowlist thêm `access_control_sop`; quarantine doc_id ngoài allowlist | Check `doc_id not in ALLOWED_DOC_IDS` | 1 quarantine (`legacy_catalog_xyz_zzz`) | Ngăn doc_id lạ lọt vào embed | `cleaning_rules.py`, reason=`unknown_doc_id` |
| **Rule 11:** Max chunk length | Chặn chunk > 8000 ký tự | Check `len(text) > max_chars` (default 8000) | 0 (data mẫu chunks ngắn) | +N khi inject chunk siêu dài | `cleaning_rules.py`, reason=`chunk_text_too_long` |

**Ví dụ cụ thể - Rule 7 (Invalid exported_at):**

```python
# Trong transform/cleaning_rules.py
def _check_invalid_exported_at(exported_at: str) -> bool:
    """Rule 7: Validate ISO-8601 format cho exported_at."""
    if not exported_at:
        return True
    return not bool(_ISO_DATETIME.fullmatch(exported_at.strip()))
```

**Kịch bản inject:**
- Input: `exported_at=""` (rỗng)
- Output: Quarantine với reason=`missing_or_invalid_exported_at`
- Impact: `quarantine_records` tăng từ 4 → 5

**Ví dụ cụ thể - Rule 8 (Short/Trivial chunk):**

```python
# Trong transform/cleaning_rules.py
def _check_short_or_trivial(text: str) -> bool:
    """Rule 8: Check chuỗi quá ngắn (< 20 ký tự) hoặc quá rác."""
    text_stripped = text.strip()
    if len(text_stripped) < 20:
        return True
    alpha_count = sum(1 for c in text_stripped if c.isalpha())
    if alpha_count == 0:
        return True
    return False
```

**Kịch bản inject:**
- Input: `chunk_text="FAQ"` (3 ký tự)
- Output: Quarantine với reason=`chunk_text_too_short_or_trivial`
- Impact: `quarantine_records` tăng từ 4 → 5

**Tổng hợp metric_impact trên data mẫu (10 raw → 6 cleaned → 4 quarantine):**
- `duplicate_chunk_text`: 1 record (row 2 trùng nội dung)
- `missing_effective_date`: 1 record (row 5 thiếu ngày)
- `stale_hr_policy_effective_date`: 1 record (row 7, HR 2025 bị loại)
- `unknown_doc_id`: 1 record (row 9, `legacy_catalog_xyz_zzz` không trong allowlist)

### 2b. Expectation mới (≥2 expectation — Khải)

Baseline có 6 expectation (E1–E6). Khải bổ sung **3 expectation mới** (E7–E9):

| Expectation | Severity | Mô tả | Logic chi tiết | Kết quả clean run | Kết quả inject |
|-------------|----------|-------|----------------|-------------------|----------------|
| **E7:** `exported_at_iso_format` | **halt** | Double-check `exported_at` đúng ISO-8601 datetime sau cleaning | Count rows where `exported_at` không match RegEx ISO-8601 | OK (`invalid_exported_at_count=0`) | FAIL nếu bypass cleaning |
| **E8:** `short_chunk_ratio_under_10pct` | **warn** | Tỷ lệ chunk < 20 ký tự không vượt 10% tổng cleaned | Calculate `short_chunks / total_cleaned * 100` | OK (`ratio=0.00%`) | WARN nếu inject nhiều chunk ngắn |
| **E9:** `doc_id_in_allowlist` | **halt** | Tất cả `doc_id` phải nằm trong `ALLOWED_DOC_IDS` (đồng bộ với cleaning Rule 10) | Count rows where `doc_id not in ALLOWED_DOC_IDS` | OK (`illegal_doc_id_count=0`) | FAIL nếu doc lạ lọt qua |

**Ví dụ cụ thể - E7 (exported_at_iso_format):**

```python
# Trong quality/expectations.py
def _expect_exported_at_iso_format(cleaned: List[Dict[str, str]]) -> ExpectationResult:
    """E7: Double-check exported_at đúng ISO-8601."""
    invalid_count = sum(1 for row in cleaned if not _is_valid_iso_datetime(row.get("exported_at", "")))
    return ExpectationResult(
        name="exported_at_iso_format",
        passed=invalid_count == 0,
        severity="halt",
        detail=f"invalid_exported_at_count={invalid_count}"
    )
```

**Kịch bản inject:**
- Input: Row có `exported_at="2026-04-10"` (không có time)
- Output: FAIL với `invalid_exported_at_count=1`
- Impact: Pipeline halt (nếu không dùng `--skip-validate`)

**Ví dụ cụ thể - E9 (doc_id_in_allowlist):**

```python
# Trong quality/expectations.py
def _expect_doc_id_in_allowlist(cleaned: List[Dict[str, str]]) -> ExpectationResult:
    """E9: Tất cả doc_id phải nằm trong ALLOWED_DOC_IDS."""
    illegal_count = sum(1 for row in cleaned if row.get("doc_id") not in ALLOWED_DOC_IDS)
    return ExpectationResult(
        name="doc_id_in_allowlist",
        passed=illegal_count == 0,
        severity="halt",
        detail=f"illegal_doc_id_count={illegal_count}"
    )
```

**Kịch bản inject:**
- Input: Row có `doc_id="legacy_catalog_xyz_zzz"`
- Output: FAIL với `illegal_doc_id_count=1`
- Impact: Pipeline halt (nếu không dùng `--skip-validate`)

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

### Trích dẫn Log cụ thể:

**Log inject-bad (trước fix):**
```text
run_id=inject-bad
raw_records=10
cleaned_records=6
quarantine_records=4
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed (chỉ dùng cho demo Sprint 3).
embed_prune_removed=1
embed_upsert count=6 collection=day10_kb
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.748, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
PIPELINE_OK
```

**Log sprint3-clean (sau fix):**
```text
run_id=sprint3-clean
raw_records=10
cleaned_records=6
quarantine_records=4
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
embed_prune_removed=1
embed_upsert count=6 collection=day10_kb
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.756, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
PIPELINE_OK
```

### Trích dẫn CSV cụ thể:

**CSV inject-bad (trước fix) - `artifacts/eval/eval_inject_bad.csv`:**
```csv
question_id,question,top1_doc_id,top1_preview,contains_expected,hits_forbidden,top1_doc_expected,top_k_used
q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,yes,,3
```

**CSV sprint3-clean (sau fix) - `artifacts/eval/eval_after_clean.csv`:**
```csv
question_id,question,top1_doc_id,top1_preview,contains_expected,hits_forbidden,top1_doc_expected,top_k_used
q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,no,,3
```

**Ý nghĩa:**
- `hits_forbidden=yes` trong inject-bad: top-k vẫn chứa context cấm (14 ngày làm việc)
- `hits_forbidden=no` trong sprint3-clean: context stale đã được loại khỏi retrieval
- `top1_preview` giống nhau (7 ngày) nhưng top-k khác nhau → quan trọng cho RAG

### Bằng chứng Grading JSONL (`artifacts/eval/grading_run.jsonl`):

```jsonl
{"id": "gq_d10_01", "question": "Theo policy hoàn tiền nội bộ, khách có tối đa bao nhiêu ngày làm việc để gửi yêu cầu hoàn tiền sau khi đơn được xác nhận?", "top1_doc_id": "policy_refund_v4", "contains_expected": true, "hits_forbidden": false, "top1_doc_matches": null, "top_k_used": 5, "grading_criteria": ["Trả lời đúng số ngày (7 ngày làm việc hoặc tương đương)", "Không khẳng định 14 ngày là chính sách hiện hành"]}
{"id": "gq_d10_02", "question": "Ticket P1: thời gian resolution SLA là bao nhiêu giờ?", "top1_doc_id": "sla_p1_2026", "contains_expected": true, "hits_forbidden": false, "top1_doc_matches": null, "top_k_used": 5, "grading_criteria": ["Nêu đúng resolution 4 giờ (hoặc tương đương trong tài liệu)"]}
{"id": "gq_d10_03", "question": "Theo chính sách nghỉ phép hiện hành (2026), nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?", "top1_doc_id": "hr_leave_policy", "contains_expected": true, "hits_forbidden": false, "top1_doc_matches": true, "top_k_used": 5, "grading_criteria": ["Nêu đúng 12 ngày (hoặc tương đương trong chunk HR 2026)", "Không khẳng định 10 ngày phép năm là chính sách hiện hành", "Ưu tiên chunk đúng doc_id ở top-1 (ranking / versioning)"]}
```

**Kết quả:**
- `gq_d10_01`: `contains_expected=true`, `hits_forbidden=false` ✅
- `gq_d10_02`: `contains_expected=true`, `hits_forbidden=false` ✅
- `gq_d10_03`: `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` ✅ (Merit)

---

## 4. Freshness & Monitoring

### SLA baseline
- `SLA = 24 giờ` (theo `FRESHNESS_SLA_HOURS` mặc định trong `contracts/data_contract.yaml`)

### 2-Boundary Monitoring

Nhóm đã mở rộng freshness check thành **2 mốc đo** để tách rõ lỗi source và lỗi publish:

```
┌─────────────────────────────────────────────────────────────────┐
│                    2-BOUNDARY MONITORING                         │
└─────────────────────────────────────────────────────────────────┘

SOURCE BOUNDARY (latest_exported_at)
├─ Đo độ mới của dữ liệu nguồn
├─ Metric: age_hours = (now - latest_exported_at) / 3600
├─ SLA: 24 giờ
└─ FAIL nếu source stale

PUBLISH BOUNDARY (publish_timestamp)
├─ Đo độ mới của lần publish hiện tại
├─ Metric: publish_age_hours = (now - publish_timestamp) / 3600
├─ SLA: 24 giờ
└─ FAIL nếu publish stale
```

### Kết quả source boundary (bắt buộc)

**Run inject-bad:**
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_inject-bad.json
```

**Output:**
```json
{
  "latest_exported_at": "2026-04-10T08:00:00",
  "age_hours": 120.748,
  "sla_hours": 24.0,
  "reason": "freshness_sla_exceeded"
}
```
**Status:** FAIL (120.748h > 24h)

**Run sprint3-clean:**
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3-clean.json
```

**Output:**
```json
{
  "latest_exported_at": "2026-04-10T08:00:00",
  "age_hours": 120.756,
  "sla_hours": 24.0,
  "reason": "freshness_sla_exceeded"
}
```
**Status:** FAIL (120.756h > 24h)

**Giải thích:** `latest_exported_at` trong dữ liệu mẫu là `2026-04-10T08:00:00`, nên stale là kỳ vọng của bài lab.

### Kết quả publish boundary (mở rộng - Distinction track)

Nhóm đã mở rộng freshness check với flag `--check-publish-boundary`:

**Run sprint4-boundary:**
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint4-boundary.json --check-publish-boundary
```

**Output:**
```json
{
  "latest_exported_at": "2026-04-10T08:00:00",
  "age_hours": 122.345,
  "sla_hours": 24.0,
  "reason": "freshness_sla_exceeded",
  "publish_boundary": {
    "publish_timestamp": "2026-04-15T10:20:12.608825+00:00",
    "publish_age_hours": 0.008,
    "sla_hours": 24.0
  }
}
```
**Status:** FAIL (source) + PASS (publish)

**Diễn giải chi tiết:**

| Boundary | Metric | Value | SLA | Status | Ý nghĩa |
|----------|--------|-------|-----|--------|---------|
| Source | `age_hours` | 122.345 | 24 | FAIL | Dữ liệu nguồn cũ 122 giờ |
| Publish | `publish_age_hours` | 0.008 | 24 | PASS | Pipeline publish mới 0.008 giờ |

**Decision guide:**
- **Source FAIL + Publish PASS**: Cần refresh data source, không cần rollback code publish
- **Source PASS + Publish FAIL**: Kiểm tra clock/timezone hoặc pipeline write manifest
- **Source FAIL + Publish FAIL**: Cả source và publish đều stale → cần triage toàn bộ

### Log freshness check trong pipeline:

**Log inject-bad:**
```text
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.748, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Log sprint3-clean:**
```text
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.756, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Log sprint4-boundary (với --check-publish-boundary):**
```text
freshness_check=FAIL {"latest_exported_at":"2026-04-10T08:00:00","age_hours":122.345,"sla_hours":24.0,"reason":"freshness_sla_exceeded","publish_boundary":{"publish_timestamp":"2026-04-15T10:20:12.608825+00:00","publish_age_hours":0.008,"sla_hours":24.0}}
```

### Chi tiết vận hành:

Xem `docs/runbook.md` (5 mục Symptom → Detection → Diagnosis → Mitigation → Prevention) để hiểu cách triage khi freshness check FAIL.

**Lưu ý lab:** Data mẫu Day 10 có thể cố ý stale, nên FAIL freshness là tín hiệu mong đợi để luyện triage. Trong production, SLA sẽ áp dụng cho data snapshot mới nhất.

---

## 5. Liên hệ Day 09

### Mạch kiến thức 3 ngày

```
┌──────────────────────────────────────────────────────────────────────────────┐
│              Trợ lý nội bộ CS + IT Helpdesk — Artifact xuyên suốt              │
└──────────────────────────────────────────────────────────────────────────────┘

Day 08 (RAG grounded)          Day 09 (Multi-Agent)          Day 10 (Data Pipeline)
├─ Retrieve đúng đoạn          ├─ Supervisor route           ├─ Freshness · quality
├─ Chunking đúng               ├─ Workers trace              ├─ Alert sớm
├─ Grounded prompting          ├─ MCP connection             └─ Detect issue
└─ Đo retrieval quality       └─ A2A vs MCP

                    ↑               ↑               ↑
                 Day 08          Day 09          Day 10
              RAG grounded   Supervisor +    Data pipeline
              retrieve đúng  workers route   + observability
              đoạn, đo được  trace rõ,MCP    detect issue
                             A2A                 sớm
```

### Dữ liệu từ pipeline Day 10 phục vụ trực tiếp cho Agent Day 09

**Ví dụ 1: Retrieval Worker (Day 09) sử dụng ChromaDB từ Day 10**

```python
# Day 09 - retrieval_worker.py
from chromadb import PersistentClient

# Sử dụng collection day10_kb từ pipeline Day 10
client = PersistentClient(path="day10/lab/chroma_db")
collection = client.get_collection(name="day10_kb")

# Query cho câu hỏi về refund
results = collection.query(
    query_texts=["Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền?"],
    n_results=3
)

# Kết quả: chunks đã qua clean + validate từ Day 10
# - Không còn chunk "14 ngày làm việc" (stale)
# - Chỉ còn chunk "7 ngày làm việc" (clean)
```

**Ví dụ 2: Policy Worker (Day 09) sử dụng canonical sources từ Day 10**

```python
# Day 09 - policy_worker.py
from pathlib import Path

# Sử dụng canonical sources từ Day 10
refund_policy = Path("day10/lab/data/docs/policy_refund_v4.txt").read_text()

# Kết quả: Content đã qua versioning từ Day 10
# - Phiên bản v4 (2026) với 7 ngày refund
# - Không còn phiên bản v3 (2025) với 14 ngày refund
```

**Ví dụ 3: Synthesis Worker (Day 09) sử dụng metadata từ Day 10**

```python
# Day 09 - synthesis_worker.py
# Sử dụng metadata từ cleaned CSV của Day 10
import csv

with open("day10/lab/artifacts/cleaned/cleaned_final-fix.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Sử dụng metadata: doc_id, effective_date, exported_at
        if row["doc_id"] == "policy_refund_v4":
            effective_date = row["effective_date"]  # "2026-02-01"
            # Kết quả: Metadata đã qua validate từ Day 10
```

### Cải thiện Day 09 nhờ Day 10

| Khía cạnh | Trước Day 10 | Sau Day 10 | Cải thiện |
|-----------|--------------|------------|-----------|
| **Data freshness** | Không biết corpus cũ/new | Freshness check 2-boundary | Phát hiện stale data sớm |
| **Data quality** | Không có validation | 9 expectations (halt/warn) | Ngăn lỗi lọt vào agent |
| **Data versioning** | Không biết version nào active | Canonical sources + allowlist | Tránh trả lời policy cũ |
| **Data lineage** | Không truy vết nguồn | Manifest + run_id | Debug nhanh hơn |
| **Data consistency** | Có thể duplicate | Dedupe + quarantine | Tránh retrieval nhiễu |

### Ví dụ cụ thể: Câu hỏi refund

**Trước Day 10 (không có pipeline):**
```
User: "Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền?"
Agent: "Theo chính sách, khách hàng có 14 ngày làm việc để yêu cầu hoàn tiền."
❌ Sai - trả lời policy cũ (v3, 2025)
```

**Sau Day 10 (có pipeline):**
```
User: "Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền?"
Agent: "Theo chính sách v4 (2026), khách hàng có 7 ngày làm việc để yêu cầu hoàn tiền."
✅ Đúng - trả lời policy mới (v4, 2026)
```

**Bằng chứng:**
- `artifacts/eval/after_clean_eval.csv`: `q_refund_window` có `hits_forbidden=no`
- `artifacts/eval/grading_run.jsonl`: `gq_d10_01` đạt `contains_expected=true`, `hits_forbidden=false`

### Ví dụ cụ thể: Câu hỏi HR leave

**Trước Day 10 (không có pipeline):**
```
User: "Nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?"
Agent: "Theo chính sách 2025, nhân viên dưới 3 năm được 10 ngày phép năm."
❌ Sai - trả lời policy cũ (2025)
```

**Sau Day 10 (có pipeline):**
```
User: "Nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?"
Agent: "Theo chính sách 2026, nhân viên dưới 3 năm được 12 ngày phép năm."
✅ Đúng - trả lời policy mới (2026)
```

**Bằng chứng:**
- `artifacts/eval/after_clean_eval.csv`: `q_leave_version` có `top1_doc_expected=yes`
- `artifacts/eval/grading_run.jsonl`: `gq_d10_03` đạt `contains_expected=true`, `top1_doc_matches=true` (Merit)

### Canonical knowledge bám theo Day 10

Chroma collection `day10_kb` là snapshot publish mới, thay thế corpus cũ có thể chứa dữ liệu stale:

- **5 doc_id canonical:**
  - `policy_refund_v4` → Refund 7 ngày (v4, 2026)
  - `sla_p1_2026` → P1 SLA 15 phút response, 4 giờ resolution
  - `it_helpdesk_faq` → Lockout sau 5 lần đăng nhập sai
  - `hr_leave_policy` → 12 ngày phép năm (2026)
  - `access_control_sop` → Quy trình cấp quyền truy cập

- **Data contract:** `contracts/data_contract.yaml` định nghĩa schema, owner, SLA
- **Manifest:** `artifacts/manifests/manifest_*.json` truy vết lineage theo run_id

### Nếu không có bước clean Day 10

Agent Day 09 sẽ trả lời sai về quy định hoàn tiền (14 ngày thay vì 7 ngày) — đã chứng minh bằng kịch bản inject:

**Kịch bản inject-bad:**
```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```

**Kết quả:**
- `artifacts/eval/eval_inject_bad.csv`: `q_refund_window` có `hits_forbidden=yes`
- `artifacts/eval/grading_run.jsonl`: `gq_d10_01` sẽ fail `hits_forbidden=true`

**Kịch bản sprint3-clean:**
```bash
python etl_pipeline.py run --run-id sprint3-clean
```

**Kết quả:**
- `artifacts/eval/eval_after_clean.csv`: `q_refund_window` có `hits_forbidden=no`
- `artifacts/eval/grading_run.jsonl`: `gq_d10_01` đạt `hits_forbidden=false`

**Kết luận:** Pipeline Day 10 đảm bảo Agent Day 09 trả lời đúng policy mới.

---

## 6. Rủi ro còn lại & việc chưa làm

### Phân loại rủi ro theo mức độ ưu tiên

```
┌─────────────────────────────────────────────────────────────────┐
│                    RISK MATRIX (P1 / P2 / P3)                    │
└─────────────────────────────────────────────────────────────────┘

P1 — CRITICAL (Khẩn cấp)
├─ Ảnh hưởng: Agent trả lời sai policy → user mất niềm tin
├─ Tần suất: Cao (mỗi khi source stale)
└─ Timeline: Phải fix trong 24h

P2 — HIGH (Nghiêm trọng)
├─ Ảnh hưởng: Pipeline fail → không có data mới
├─ Tần suất: Trung bình (khi embed/model lỗi)
└─ Timeline: Nên fix trong 1 tuần

P3 — MEDIUM (Trung bình)
├─ Ảnh hưởng: Monitoring thiếu → phát hiện chậm
├─ Tần suất: Thấp (khi scale lên)
└─ Timeline: Có thể fix trong 1 sprint
```

### Danh sách rủi ro chi tiết

| Rủi ro | Mức độ | Mô tả | Tác động | Giải pháp đề xuất | Timeline |
|-------|--------|-------|----------|-------------------|----------|
| **ChromaDB / Model embedding lỗi** | **P1** | Nếu model `all-MiniLM-L6-v2` hoặc ChromaDB crash, bước publish cuối thất bại dù manifest/log tồn tại | Agent không có data mới → trả lời sai policy cũ | Thêm retry logic + alert riêng cho embed step | 24h |
| **Freshness FAIL trên production** | **P1** | Hiện chưa có auto-alert (Slack/Email) khi freshness check FAIL | Phát hiện chậm → user thấy sai trước khi team biết | Tích hợp webhook Slack/Email khi freshness FAIL | 24h |
| **`chunk_id` phụ thuộc `seq`** | **P2** | Nếu logic sắp xếp/dedupe thay đổi giữa hai run, `chunk_id` có thể đổi → prune xóa nhầm vector hợp lệ | Loss data → retrieval thiếu context | Test kỹ khi mở rộng rule mới; thêm checksum | 1 tuần |
| **Expectation E7/E9 halt trên clean data** | **P2** | Nếu cleaning layer bị bypass hoặc transform làm hỏng format, pipeline sẽ dừng trước embed | Pipeline không publish → không có data mới | Monitoring log expectation FAIL; alert khi halt | 1 tuần |
| **Mở rộng quy mô** | **P3** | Hiện chỉ test trên 10 bản ghi mẫu; cần benchmark với dataset lớn hơn (100+ chunks) để đánh giá hiệu năng cleaning + embed | Performance unknown khi scale | Benchmark với dataset lớn; optimize nếu cần | 1 sprint |
| **LLM-judge chưa đánh giá top-k** | **P3** | LLM-judge hiện chấm theo top1 preview; chưa đánh giá trực tiếp toàn bộ top-k chunk | Có thể miss lỗi trong top-k | Mở rộng LLM-judge để đánh giá toàn bộ top-k | 1 sprint |

### Chi tiết từng rủi ro

#### Rủi ro P1-1: ChromaDB / Model embedding lỗi

**Mô tả:**
```python
# Trong etl_pipeline.py - cmd_embed_internal
try:
    # Embed với OpenAI text-embedding-3-small
    embeddings = embedding_function(texts)
    # Upsert vào ChromaDB
    collection.upsert(documents=texts, embeddings=embeddings, ids=ids)
except Exception as e:
    # Hiện tại: chỉ log error, không retry
    log(f"ERROR: embed failed: {e}")
    return False
```

**Tác động:**
- Manifest/log tồn tại nhưng ChromaDB không có data mới
- Agent Day 09 vẫn trả lời policy cũ
- User nhận thấy sai trước khi team biết

**Giải pháp đề xuất:**
```python
# Thêm retry logic + alert
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def embed_with_retry(texts, embedding_function):
    return embedding_function(texts)

try:
    embeddings = embed_with_retry(texts, embedding_function)
    collection.upsert(documents=texts, embeddings=embeddings, ids=ids)
    # Alert success
    send_alert("embed_success", {"count": len(texts)})
except Exception as e:
    # Alert failure
    send_alert("embed_failure", {"error": str(e)})
    raise
```

#### Rủi ro P1-2: Freshness FAIL trên production

**Mô tả:**
```python
# Trong monitoring/freshness_check.py
status, detail = check_manifest_freshness(manifest_path, sla_hours=24.0)
# Hiện tại: chỉ print ra console
print(f"freshness_check={status} {detail}")
```

**Tác động:**
- Phải chạy thủ công `python etl_pipeline.py freshness` để biết
- Phát hiện chậm → user thấy sai trước khi team biết

**Giải pháp đề xuất:**
```python
# Thêm webhook Slack/Email
def send_freshness_alert(status, detail):
    if status == "FAIL":
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        payload = {
            "text": f"🚨 Freshness SLA Breach!",
            "attachments": [{
                "color": "danger",
                "fields": [
                    {"title": "Status", "value": status},
                    {"title": "Age Hours", "value": str(detail["age_hours"])},
                    {"title": "SLA Hours", "value": str(detail["sla_hours"])},
                    {"title": "Reason", "value": detail.get("reason", "")}
                ]
            }]
        }
        requests.post(webhook_url, json=payload)

# Trong pipeline
status, detail = check_manifest_freshness(manifest_path, sla_hours=24.0)
send_freshness_alert(status, detail)
```

#### Rủi ro P2-1: `chunk_id` phụ thuộc `seq`

**Mô tả:**
```python
# Trong transform/cleaning_rules.py
def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"
```

**Tác động:**
- Nếu logic sắp xếp/dedupe thay đổi → `seq` đổi → `chunk_id` đổi
- Prune xóa nhầm vector hợp lệ → loss data

**Giải pháp đề xuất:**
```python
# Thêm checksum để detect thay đổi
def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    # Sử dụng chỉ doc_id + chunk_text (không phụ thuộc seq)
    h = hashlib.sha256(f"{doc_id}|{chunk_text}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{h}"

# Hoặc thêm checksum để detect
def _chunk_checksum(doc_id: str, chunk_text: str) -> str:
    return hashlib.sha256(f"{doc_id}|{chunk_text}".encode("utf-8")).hexdigest()[:8]

# Trong prune logic
prev_checksums = {meta["checksum"] for meta in prev_metas}
current_checksums = {_chunk_checksum(row["doc_id"], row["chunk_text"]) for row in cleaned}
ids_to_remove = [id for id, meta in zip(prev_ids, prev_metas)
                  if meta["checksum"] not in current_checksums]
```

#### Rủi ro P2-2: Expectation E7/E9 halt trên clean data

**Mô tả:**
```python
# Trong quality/expectations.py
def _expect_exported_at_iso_format(cleaned: List[Dict[str, str]]) -> ExpectationResult:
    invalid_count = sum(1 for row in cleaned if not _is_valid_iso_datetime(row.get("exported_at", "")))
    return ExpectationResult(
        name="exported_at_iso_format",
        passed=invalid_count == 0,
        severity="halt",  # ← Halt nếu fail
        detail=f"invalid_exported_at_count={invalid_count}"
    )
```

**Tác động:**
- Nếu cleaning layer bị bypass → expectation FAIL → pipeline halt
- Không publish data mới → agent trả lời policy cũ

**Giải pháp đề xuất:**
```python
# Monitoring log expectation FAIL
def run_expectations(cleaned: List[Dict[str, str]]) -> Tuple[List[ExpectationResult], bool]:
    results = []
    halt = False
    for exp_func in EXPECTATION_FUNCTIONS:
        result = exp_func(cleaned)
        results.append(result)
        if not result.passed and result.severity == "halt":
            halt = True
            # Alert expectation FAIL
            send_alert("expectation_halt", {
                "name": result.name,
                "detail": result.detail
            })
    return results, halt
```

#### Rủi ro P3-1: Mở rộng quy mô

**Mô tả:**
- Hiện chỉ test trên 10 bản ghi mẫu
- Cần benchmark với dataset lớn hơn (100+ chunks)

**Tác động:**
- Performance unknown khi scale
- Có thể timeout khi embed lớn

**Giải pháp đề xuất:**
```python
# Benchmark với dataset lớn
def benchmark_pipeline(dataset_size: int):
    start = time.time()
    # Run pipeline
    result = run_pipeline(dataset_size)
    end = time.time()
    duration = end - start
    # Log metrics
    log(f"Benchmark: {dataset_size} chunks in {duration:.2f}s")
    log(f"Throughput: {dataset_size/duration:.2f} chunks/s")
    # Alert nếu quá chậm
    if duration > 300:  # 5 phút
        send_alert("pipeline_slow", {"duration": duration})
```

#### Rủi ro P3-2: LLM-judge chưa đánh giá top-k

**Mô tả:**
```python
# Trong llm_judge.py
def _build_prompt(eval_row: Dict[str, str], qmeta: Dict[str, Any]) -> str:
    # Hiện tại: chỉ dùng top1_preview
    top1_preview = eval_row.get('top1_preview', '')
    # ...
```

**Tác động:**
- Có thể miss lỗi trong top-k
- Đánh giá không đầy đủ

**Giải pháp đề xuất:**
```python
# Mở rộng để đánh giá toàn bộ top-k
def _build_prompt(eval_row: Dict[str, str], qmeta: Dict[str, Any]) -> str:
    # Sử dụng toàn bộ top-k
    top_k_chunks = eval_row.get('top_k_chunks', [])
    context = "\n\n".join([f"Chunk {i+1}: {chunk}" for i, chunk in enumerate(top_k_chunks)])
    # ...
```

### Kế hoạch ưu tiên

**Sprint tiếp theo (2 tuần):**
1. ✅ P1-1: Thêm retry logic + alert cho embed step
2. ✅ P1-2: Tích hợp webhook Slack/Email cho freshness FAIL

**Sprint sau đó (2 tuần):**
3. ✅ P2-1: Thêm checksum để detect thay đổi chunk_id
4. ✅ P2-2: Monitoring log expectation FAIL

**Sprint dài hạn (1 tháng):**
5. ✅ P3-1: Benchmark với dataset lớn
6. ✅ P3-2: Mở rộng LLM-judge để đánh giá top-k

