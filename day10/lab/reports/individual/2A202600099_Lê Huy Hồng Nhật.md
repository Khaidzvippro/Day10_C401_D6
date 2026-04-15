# Báo cáo cá nhân — Lab Day 10

**Họ và tên:** Lê Huy Hồng Nhật  
**MSSV:** 2A202600099  
**Vai trò:** Tech Lead + Ingestion Owner (điều phối merge và tích hợp artifact)  
**Độ dài:** ~520 từ

---

## 1. Phụ trách

Trong Day 10, tôi chịu trách nhiệm chính ở `etl_pipeline.py`, `contracts/data_contract.yaml`, `artifacts/manifests/`, và điều phối tích hợp nhánh nhóm vào `nhat` rồi cập nhật `main`.

Các phần tôi trực tiếp làm:

- Vận hành pipeline end-to-end, đảm bảo log có đủ `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`.
- Tạo/duy trì manifest cho các run chính: `sprint1`, `inject-bad`, `sprint3-clean`, `sprint4-boundary`.
- Đồng bộ contract với code cleaning (đặc biệt allowlist/canonical cho `access_control_sop`).
- Tích hợp kết quả từ các nhánh `khanhnq`, `tan`, `Khaidz` vào `nhat`, sau đó merge sang `main`.
- Resolve conflict khi merge docs và artifacts để giữ phiên bản “nộp được” nhất quán.

**Bằng chứng:** chuỗi commit của tôi trên `nhat/main` gồm các commit tích hợp artifacts, logs, LLM-judge, docs refinement và merge conflict resolution (theo lịch sử git log).

---

## 2. Quyết định kỹ thuật

**(a) Quyết định về monitoring boundary**

Tôi mở rộng freshness check thành 2 mốc:

- source boundary: `latest_exported_at`
- publish boundary: `publish_timestamp`

Mục tiêu là tách rõ “pipeline vừa publish” với “data source còn stale”. Điều này giúp tránh kết luận sai rằng pipeline hỏng, trong khi thực tế lỗi nằm ở độ mới dữ liệu nguồn.

**(b) Quyết định về quy trình tích hợp**

Do nhóm làm song song nhiều nhánh, tôi ưu tiên:

1. Pull/fetch theo nhánh owner,
2. commit theo cụm thay đổi (artifacts, docs, code),
3. merge vào `nhat` trước,
4. chỉ đưa sang `main` khi đã sạch conflict.

Quy trình này giúp giảm rủi ro mất artifact quan trọng (logs/manifest/eval).

---

## 3. Sự cố / anomaly

Sự cố lớn nhất tôi gặp là conflict khi merge `nhat` vào `main`, tập trung ở docs và một số artifact inject:

- `day10/lab/docs/data_contract.md`
- `day10/lab/docs/quality_report.md`
- `day10/lab/artifacts/*inject-bad*`

Nguyên nhân: `main` và `nhat` cùng sửa cùng block nội dung trong thời gian gần nhau.

Cách xử lý:

- đọc toàn bộ conflict marker,
- giữ bản docs refined có số liệu thực từ logs/eval,
- chuẩn hóa path manifest/cleaned theo format repo,
- commit conflict resolution riêng để truy vết rõ.

Kết quả: merge hoàn tất, `main` nhận đúng phiên bản docs + artifacts nhất quán với run thực tế.

---

## 4. Before / after (evidence)

**Log evidence:**

- `run_inject-bad.log`: `expectation[refund_no_stale_14d_window] FAIL (halt)` và tiếp tục do `--skip-validate`.
- `run_sprint3-clean.log`: expectation refund chuyển về `OK (halt)`.
- `run_sprint4-boundary.log`: thể hiện đồng thời source boundary FAIL và publish boundary PASS.

**CSV/JSONL evidence:**

- `artifacts/eval/after_inject_bad.csv`: `q_refund_window` có `hits_forbidden=yes`.
- `artifacts/eval/after_clean_eval.csv`: `q_refund_window` về `hits_forbidden=no`.
- `artifacts/eval/grading_run.jsonl`: đủ 3 câu `gq_d10_01..03`, đạt điều kiện pass rubric.

---

## 5. Cải tiến thêm 2 giờ

Nếu có thêm 2 giờ, tôi sẽ làm 2 việc:

1. Tạo script “artifact curate” để tự gom bộ nộp tối thiểu (`sprint1`, `inject-bad`, `sprint3-clean`, `sprint4-boundary`) và đưa phần còn lại vào `archive/` nhằm giảm nhiễu.
2. Tự động hóa cảnh báo freshness (webhook Slack/Email) khi source boundary FAIL nhưng publish boundary PASS, kèm runbook link để thao tác triage ngay.

