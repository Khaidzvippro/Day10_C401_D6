# Hướng dẫn & Phân tích Minh chứng Sự cố (Anomaly Test & Final Fix)

Tài liệu này giải thích chi tiết quá trình giả lập lỗi rò rỉ dữ liệu (Stale Data Anomaly) và cách hệ thống tự động khắc phục, kèm theo danh sách các file minh chứng (artifacts) được sinh ra.

---

## 1. Mục đích
Chứng minh tính hiệu quả của các rule kiểm soát chất lượng (Quality Layer) và biến đổi lôgic (Business Transformation) bằng cách:
1. Cố tình tắt rào chắn bảo vệ để theo dõi dữ liệu lỗi lọt vào hệ thống (Anomaly).
2. Kích hoạt lại rào chắn để thấy hệ thống làm sạch dữ liệu tự động (Final Fix).

---

## 2. Bước 1: Giả lập lỗi rò rỉ dữ liệu (`anomaly-test`)

**Mô tả:**
Chạy pipeline nhưng cố tình bỏ qua bước xử lý lỗi chính sách hoàn tiền (`--no-refund-fix`) và tắt Data Quality Validator (`--skip-validate`). Lúc này, văn bản chứa chính sách cũ ("14 ngày làm việc") sẽ không bị chặn mà đi thẳng vào VectorDB.

**Lệnh thực thi:**
```bash
python etl_pipeline.py run --run-id anomaly-test --no-refund-fix --skip-validate
```

**Các Output (Artifacts) sinh ra làm minh chứng:**
- `artifacts/cleaned/cleaned_anomaly-test.csv`: Chứa dữ liệu "đã lọt lưới" đưa vào ChromaDB, bao gồm cả nội dung "14 ngày làm việc".
- `artifacts/quarantine/quarantine_anomaly-test.csv`: Chỉ chứa các lỗi định dạng encoding, character length, v.v., còn lỗi business logic đã bị bỏ qua.
- `artifacts/manifests/manifest_anomaly-test.json`: Bản ghi metadata cho lần chạy này.
- `reports/individual/anomaly_test_result.jsonl`: Kết quả chạy RAG Evaluation (Grading) xác nhận hệ thống sinh ảo giác do đọc tài liệu cũ (`hits_forbidden = true`).

---

## 3. Bước 2: Khôi phục và Sửa lỗi (`final-fix`)

**Mô tả:**
Chạy lại pipeline bình thường để bật lại `Rule 6: _clean_refund_policy` và `Data Expectations`. Hệ thống sẽ bắt lỗi, tự động sửa chuỗi "14 ngày" thành "7 ngày" trước khi đưa vào CSDL, đồng thời cập nhật lại ChromaDB không còn vector độc hại.

**Lệnh thực thi:**
```bash
python etl_pipeline.py run --run-id final-fix
```

**Các Output (Artifacts) sinh ra làm minh chứng:**
- `artifacts/cleaned/cleaned_final-fix.csv`: Dữ liệu chuẩn cuối cùng, chính sách hoàn tiền đã được cập nhật thành "7 ngày làm việc". VectorDB trở nên an toàn 100%.
- `artifacts/quarantine/quarantine_final-fix.csv`: Bao gồm các file bị cách ly (như cũ) và nếu có expectation HALT thì sẽ nằm dồn vào đây hoặc cảnh báo.
- `artifacts/manifests/manifest_final-fix.json`: Bản ghi metadata cho pipeline ổn định.

---

**Kết luận:** 
Hai lần chạy song song trên cấp đủ bằng chứng vật lý khẳng định vai trò của Data Observability & Transformation. Sự cố bị tóm gọn khi bật Pipeline chuẩn.
