# Báo Cáo Chi Tiết: Validation Sự Cố Data Pipeline (Anomaly Report)

**Người thực hiện:** Nguyễn Quốc Khánh
**Ngày thực hiện:** 15/04/2026

---

## 1. Bối cảnh Sự Cố (Context)

Trong hệ thống RAG (Retrieval-Augmented Generation) của dự án, độ chính xác của tài liệu trả về phụ thuộc rất lớn vào chất lượng dữ liệu văn bản được nạp vào VectorDB. 
Một trong những lỗi nghiêm trọng nhất có thể xảy ra ở tầng Data Pipeline là rò rỉ các quy định cũ (Stale Data), dẫn đến việc RAG cung cấp thông tin sai lệch cho người dùng. 
Đặc biệt, trong chính sách hoàn tiền có sự thay đổi từ "14 ngày làm việc" (quy định cũ) xuống "7 ngày làm việc" (quy định mới).

---

## 2. Kịch bản Giả lập Lỗi (Anomaly Injection)

Để chứng minh tính sống còn của việc áp dụng business rule trong tầng biến đổi (Transformation Layer) và tầng kiểm định chất lượng (Quality Layer), tôi đã thực hiện một kiểm thử cưỡng bức:

1. **Vô hiệu hóa bộ lọc (Bypass Rules)**: Thực thi ETL Pipeline với cờ `--no-refund-fix --skip-validate`. 
2. **Mục đích**: Để cho đoạn text chứa chính sách cũ ("14 ngày làm việc") đi lọt qua lưới lọc và được nạp vào ChromaDB.
3. **Lệnh thực thi**:
   ```bash
   python etl_pipeline.py run --run-id anomaly-test --no-refund-fix --skip-validate
   ```

---

## 3. Quá trình Đánh Giá (Evaluation) và Triệu Chứng Lỗi

Ngay sau khi VectorDB bị nhiễm độc dữ liệu cũ, tôi tiến hành chạy tập câu hỏi đánh giá chuẩn `grading_questions.json` để kiểm tra độ chính xác của hệ thống RAG.

**Lệnh thực thi Eval**:
```bash
python grading_run.py --questions data/grading_questions.json --out reports/individual/anomaly_test_result.jsonl
```

**Triệu chứng & Hậu quả**:
Lỗi hiển thị rõ ràng thông qua số liệu (metrics) đầu ra của hệ thống:
- Hệ thống thất bại ở câu hỏi nghiệp vụ `gq_d10_01` (chính sách hoàn tiền).
- Metric chỉ ra `hits_forbidden = true`, nghĩa là chuỗi cấm ("14 ngày làm việc") đã lọt top K kết quả trả về của VectorDB.
- Người dùng cuối sẽ nhận được câu trả lời sai luật hiện hành do LLM được cung cấp context (văn bản) lỗi thời.

Trích xuất JSONL lỗi (`anomaly_test_result.jsonl`):
```json
{"question_id": "gq_d10_01", "contains_expected": false, "hits_forbidden": true, "top1_doc_matches": false}
```

---

## 4. Cơ chế Bảo vệ & Khắc phục (The Fix)

Sau khi ghi nhận hệ quả của sự cố, tôi tiến hành khôi phục hàng rào bảo vệ:

1. **Tái kích hoạt Data Quality Expectations**: Loại bỏ cờ `--skip-validate`. Bất kỳ lô dữ liệu nào còn chứa lỗi "14 ngày" sẽ làm hàm expectation `expectation[refund_no_stale_14d_window]` trigger trạng thái `FAIL (halt)`, lập tức ngắt pipeline trước khi đẩy vào ChromaDB.
2. **Tái kích hoạt Business Fix**: Loại bỏ cờ `--no-refund-fix`. Rule 6 trong `cleaning_rules.py` sẽ tự động tìm và thay thế chuỗi lỗi thời, làm sạch dữ liệu từ trứng nước.
3. **Làm sạch VectorDB**: 
   ```bash
   python etl_pipeline.py run --run-id final-fix
   ```

**Biện chứng thành công**: 
Chạy lại evaluate sau khi fix, metric xác nhận `hits_forbidden = false`, `contains_expected = true`. Top 1 Document hiện về đúng nội dung: *"Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."* 

Chứng thực rõ ràng vai trò của **Data Observability** (biết khi nào dữ liệu sai) và **Data Cleaning** (sửa dữ liệu sai) trong đường ống ETL.
