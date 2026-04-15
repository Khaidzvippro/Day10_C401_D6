# Quality report — Lab Day 10 (nhóm C401 - D6)

**run_id inject:** `inject-bad`  
**run_id clean:** `sprint3-clean`  
**run_id monitor boundary:** `sprint4-boundary`  
**Ngày:** 15/04/2026

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (Inject: `inject-bad`) | Sau (Clean: `sprint3-clean`) | Ghi chú |
|--------|-------------------------------|-------------------------------|---------|
| raw_records | 10 | 10 | Dữ liệu mẫu ban đầu không đổi |
| cleaned_records | 6 | 6 | Cùng số lượng, khác chất lượng nội dung |
| quarantine_records | 4 | 4 | Các bản ghi lỗi vẫn bị loại ổn định |
| Expectation halt? | FAIL (refund rule) | PASS | Inject cố ý dùng `--skip-validate` để tiếp tục embed |
| embed_upsert | 6 | 6 | Collection vẫn được cập nhật theo snapshot |
| embed_prune_removed | 1 | 1 | Có prune vector stale ở cả hai run |

Nguồn số liệu: `artifacts/logs/run_inject-bad.log`, `artifacts/logs/run_sprint3-clean.log`.

---

## 2. Before / after retrieval (bắt buộc)

So sánh dựa trên các file:
- `artifacts/eval/after_inject_bad.csv`
- `artifacts/eval/after_clean_eval.csv`

### Câu then chốt `q_refund_window`

- **Inject (`after_inject_bad.csv`):** `hits_forbidden=yes`  
  Nghĩa là top-k vẫn chứa context cấm (14 ngày làm việc), dù top1 preview có thể nhìn “đúng”.
- **Clean (`after_clean_eval.csv`):** `hits_forbidden=no`  
  Context stale đã được loại khỏi retrieval sau clean + re-embed.

### Câu versioning `q_leave_version`

- **Inject:** `top1_doc_expected=yes`, `contains_expected=yes`, `hits_forbidden=no`.
- **Clean:** giữ ổn định các chỉ số, chứng minh clean không làm giảm chất lượng ở câu HR 2026.

Kết luận: với dữ liệu inject, hệ có dấu hiệu “rủi ro context stale trong top-k”; sau run clean, tín hiệu này biến mất ở câu refund.

---

## 3. Freshness & monitoring

### SLA baseline
- `SLA = 24 giờ` (theo `FRESHNESS_SLA_HOURS` mặc định).

### Kết quả source boundary (bắt buộc)
- Inject: `FAIL` (`age_hours ~ 120.748 > 24`)
- Clean: `FAIL` (`age_hours ~ 120.756 > 24`)

Giải thích: `latest_exported_at` trong dữ liệu mẫu là `2026-04-10T08:00:00`, nên stale là kỳ vọng của bài lab.

### Kết quả publish boundary (mở rộng)
Run `sprint4-boundary` với `--check-publish-boundary` cho thấy:
- `source boundary`: vẫn `FAIL` (data source cũ)
- `publish boundary`: `publish_age_hours ~ 0.0`, trong SLA

Điều này chứng minh pipeline publish mới, nhưng dữ liệu nguồn vẫn cũ: đúng tinh thần debug data trước debug model.

---

## 4. Corruption inject (Sprint 3)

Lệnh inject:
`python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`

Tín hiệu đúng kỳ vọng trong log:
- `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
- Có dòng cảnh báo: `WARN: expectation failed but --skip-validate → tiếp tục embed`

Mục tiêu của inject là tạo “before” evidence để so sánh định lượng với run clean.

---

## 5. Mở rộng LLM-judge (Distinction track)

Nhóm đã thêm:
- `llm_judge.py`
- các artifact:
  - `artifacts/eval/llm_judge_after_clean.csv`
  - `artifacts/eval/llm_judge_after_inject_bad.csv`
  - `artifacts/eval/llm_judge_grading_after_clean.jsonl`

Vai trò: bổ sung lớp đánh giá ngữ nghĩa bằng LLM; không thay thế `grading_run.py` trong rubric bắt buộc.

---

## 6. Hạn chế & việc chưa làm

- Chưa tích hợp auto-alert thật (Slack/Email webhook) khi freshness FAIL.
- LLM-judge hiện chấm theo top1 preview; chưa đánh giá trực tiếp toàn bộ top-k chunk.
- Cần chuẩn hóa quy ước đặt tên artifact để giảm số file run timestamp khi nộp final.
