# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

> User / agent thấy gì? (VD: trả lời “14 ngày” thay vì 7 ngày)

---

## Detection

Metric chính đang báo incident là freshness check trên manifest:

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_2026-04-15T08-05Z.json
```

Kết quả:

```text
FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.761, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Diễn giải:

- `latest_exported_at` là mốc dữ liệu mới nhất trong export, nên được ưu tiên để đo freshness của data source.
- `age_hours = 120.761` nghĩa là dữ liệu đã cũ khoảng 120.8 giờ tại thời điểm check.
- `sla_hours = 24.0` là ngưỡng cam kết dữ liệu không được cũ quá 24 giờ.
- Vì `120.761 > 24.0`, status là `FAIL` với lý do `freshness_sla_exceeded`.
- Điều này cho thấy pipeline có thể vẫn chạy xong, nhưng dữ liệu đầu vào vẫn stale theo SLA nên agent có rủi ro trả lời theo policy cũ.

Lưu ý cho lab:

- Với data mẫu Day 10, freshness `FAIL` có thể là hợp lý vì file raw được cố ý để timestamp cũ nhằm dạy cách phát hiện stale data.
- Nếu nhóm muốn `PASS`, cần cập nhật timestamp nguồn hoặc giải thích lại SLA áp cho snapshot demo thay vì áp cứng cho dữ liệu mẫu lịch sử.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/manifest_2026-04-15T08-05Z.json` và chạy lại `python etl_pipeline.py freshness --manifest ...` | Xác nhận `latest_exported_at=2026-04-10T08:00:00`, `age_hours=120.761`, `sla_hours=24.0`, nguyên nhân là `freshness_sla_exceeded` |
| 2 | Đối chiếu log cùng `run_id` để xem `raw_records`, `cleaned_records`, `quarantine_records` | Xác nhận pipeline có chạy xong nhưng dữ liệu nguồn vẫn stale; phân biệt lỗi source freshness với lỗi pipeline crash |
| 3 | Mở `artifacts/quarantine/*.csv` | Kiểm tra có policy/doc nào bị quarantine do lỗi định dạng, thiếu trường, hoặc version conflict |
| 4 | Chạy `python eval_retrieval.py` và xem dòng `q_refund_window` | Xác nhận retrieval có đang trả chunk stale / `hits_forbidden` hay không |
| 5 | Chỉ sau các bước trên mới xem prompt/model | Tránh debug model trước khi loại trừ lỗi freshness, quality, và retrieval |

---

## Mitigation

- Chạy lại pipeline với dữ liệu export mới hơn hoặc quay về run sạch không inject.
- Re-embed để Chroma phản ánh cleaned snapshot mới nhất thay vì giữ context stale.
- Chạy lại freshness check trên manifest mới và xác nhận status không còn `FAIL` do dữ liệu quá cũ.
- Chạy lại `eval_retrieval.py` để xác nhận câu `q_refund_window` không còn lấy chunk stale.
- Nếu là môi trường production, tạm cảnh báo corpus stale hoặc hạn chế trả lời các policy nhạy cảm cho đến khi sync hoàn tất.

---

## Prevention

- Giữ freshness check như một bước bắt buộc sau mỗi lần publish manifest.
- Thiết lập alert khi `freshness_check=FAIL` để team phát hiện stale data trước khi user thấy câu trả lời sai.
- Làm rõ owner và SLA của nguồn policy export trong data contract / runbook.
- Bổ sung expectation hoặc rule để phát hiện policy stale, wrong version, hoặc dữ liệu refund không nhất quán.
- Nếu muốn nâng cao observability, thêm `publish_timestamp` vào manifest để đo thêm publish boundary, không chỉ source boundary.
