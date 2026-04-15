# Runbook — Lab Day 10 (incident handling)

---

## Symptom

- Agent trả lời sai policy (vd: refund window lệch) dù pipeline vừa chạy.
- `freshness_check=FAIL` trong log/CLI.
- `hits_forbidden=yes` ở file eval cho câu `q_refund_window`.
- Expectation `halt` fail ở run inject hoặc run sạch bị regress.

---

## Detection

### A. Freshness check (source boundary)

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_2026-04-15T08-05Z.json
```

Ví dụ kết quả:

```text
FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.761, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

### B. Freshness check (2 boundary: source + publish)

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint4-boundary.json --check-publish-boundary
```

Ví dụ kết quả:

```text
FAIL {"latest_exported_at":"2026-04-10T08:00:00","age_hours":122.345,"sla_hours":24.0,"reason":"freshness_sla_exceeded","publish_boundary":{"publish_timestamp":"2026-04-15T10:20:12.608825+00:00","publish_age_hours":0.008,"sla_hours":24.0}}
```

Diễn giải nhanh:

- `latest_exported_at` là mốc dữ liệu mới nhất trong export, nên được ưu tiên để đo freshness của data source.
- `age_hours` là độ cũ của data source tại thời điểm kiểm tra.
- `sla_hours = 24.0` là ngưỡng cam kết dữ liệu không được cũ quá 24 giờ.
- `publish_boundary.publish_age_hours` đo độ mới của lần publish hiện tại.
- Nếu source FAIL nhưng publish PASS: hệ publish chạy mới, nhưng dữ liệu nguồn vẫn stale.

Lưu ý lab: data mẫu Day 10 có thể cố ý stale, nên FAIL freshness là tín hiệu mong đợi để luyện triage.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Xác định run gần nhất qua `artifacts/manifests/manifest_<run_id>.json` | Có đúng file manifest của run cần điều tra |
| 2 | Chạy freshness cả mode thường và mode `--check-publish-boundary` | Phân biệt source stale hay publish stale |
| 3 | Đối chiếu log cùng `run_id` (`run_<run_id>.log`) | Xác nhận `raw_records`, `cleaned_records`, `quarantine_records`, expectation status |
| 3 | Mở `artifacts/quarantine/*.csv` | Kiểm tra có policy/doc nào bị quarantine do lỗi định dạng, thiếu trường, hoặc version conflict |
| 4 | So sánh `after_inject_bad.csv` và `after_clean_eval.csv` | Kiểm tra `hits_forbidden` ở `q_refund_window` đã giảm từ `yes` về `no` |
| 5 | Chỉ sau các bước trên mới debug prompt/model | Tránh tối ưu sai tầng |

Decision guide:
- **Source FAIL + Publish PASS**: cần refresh data source, không cần rollback code publish.
- **Source PASS + Publish FAIL**: kiểm tra clock/timezone hoặc pipeline write manifest.
- **Expectation halt FAIL trên clean run**: điều tra regress ở cleaning/expectations trước embed.

---

## Mitigation

1. Chạy lại pipeline clean:
   ```bash
   python etl_pipeline.py run --run-id sprint3-clean
   ```
2. Kiểm tra freshness:
   ```bash
   python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3-clean.json --check-publish-boundary
   ```
3. Re-run eval:
   ```bash
   python eval_retrieval.py --out artifacts/eval/after_clean_eval.csv
   ```
4. Nếu vẫn stale source: escalates owner ingest/source system, giữ cảnh báo trong report.
5. Với incident policy nhạy cảm: tạm hạn chế trả lời auto cho nhóm câu hỏi bị ảnh hưởng.

---

## Prevention

- Giữ freshness check như một bước bắt buộc sau mỗi lần publish manifest.
- Thiết lập alert khi `freshness_check=FAIL` để team phát hiện stale data trước khi user thấy câu trả lời sai.
- Làm rõ owner và SLA của nguồn policy export trong data contract / runbook.
- Bổ sung expectation hoặc rule để phát hiện policy stale, wrong version, hoặc dữ liệu refund không nhất quán.
- Duy trì 2-boundary monitoring (`latest_exported_at` + `publish_timestamp`) để tách bạch lỗi source và lỗi publish.
- Chuẩn hóa naming run (`sprint1`, `inject-bad`, `sprint3-clean`, `sprint4-boundary`) để truy vết nhanh.
