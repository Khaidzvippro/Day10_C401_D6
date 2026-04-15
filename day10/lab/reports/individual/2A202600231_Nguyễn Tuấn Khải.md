# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Tuấn Khải  
**Vai trò:** Quality / Expectation Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** 400–650 từ

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `quality/expectations.py` — thêm 3 expectation mới E7, E8, E9 vào hàm `run_expectations()`
- `eval_retrieval.py` — mở rộng thêm flag `--llm-judge` gọi OpenAI GPT đánh giá faithfulness của context retrieved, bổ sung 3 cột vào CSV output: `llm_faithful`, `llm_score`, `llm_reason`
- `requirements.txt` — thêm `openai>=1.0.0`

**Kết nối với thành viên khác:**

Tôi phụ thuộc vào Khánh (Cleaning Owner) — sau khi Khánh push `cleaning_rules.py` với Rule 7–11, tôi đọc code và điều chỉnh E7 để không bị duplicate logic với cleaning layer. E9 cũng cần đồng bộ `ALLOWED_DOC_IDS` với `cleaning_rules.py` (Khánh thêm `access_control_sop` ở Rule 10). Tôi cũng phối hợp với Tấn (Embed Owner) để xác nhận `hits_forbidden` thay đổi đúng sau inject.

**Bằng chứng:**

Commit trên nhánh `Khaidz` — file `quality/expectations.py` có comment rõ từng expectation: tên, severity, metric impact, cách test.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Tại sao E7 kiểm tra ISO-8601 format thay vì chỉ check rỗng**

Ban đầu tôi thiết kế E7 chỉ check `exported_at != ""` với severity `halt`. Sau khi đọc code Khánh, tôi nhận ra Rule 7 của cleaning layer đã quarantine mọi row có `exported_at` rỗng hoặc sai format trước khi vào expectation suite — nghĩa là E7 check rỗng sẽ luôn pass, trở thành expectation trivial không có giá trị.

Tôi điều chỉnh E7 sang kiểm tra **ISO-8601 datetime format** bằng regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?$`. Lý do giữ `halt`: nếu `exported_at` sai format thì `freshness_check.py` không parse được timestamp, dẫn đến freshness báo `WARN` sai thay vì `FAIL` thật — đây là lỗi nghiêm trọng về observability. E7 đóng vai trò defense-in-depth: phát hiện kể cả khi cleaning bị bypass qua `--skip-validate`. Quyết định này đòi hỏi hiểu toàn bộ pipeline chứ không chỉ nhìn một tầng đơn lẻ.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Freshness FAIL trên clean data — phát hiện qua log Sprint 2**

Khi chạy `python etl_pipeline.py run --run-id khai-sprint2`, pipeline báo `PIPELINE_OK` nhưng cuối log xuất hiện:

```
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 119.92, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Dữ liệu CSV mẫu có `exported_at=2026-04-10T08:00:00` — cũ ~5 ngày so với thời điểm chạy, vượt SLA 24 giờ. Tôi xác nhận đây không phải lỗi code mà là hành vi đúng: CSV mẫu dùng timestamp cố định để mô phỏng tình huống data stale thực tế.

Sự cố này đồng thời giúp tôi phát hiện rằng regex E7 cần chấp nhận format không có timezone suffix (vd `2026-04-10T08:00:00` không có `Z`), vì `parse_iso()` trong `freshness_check.py` xử lý được bằng cách gán UTC mặc định. Nếu E7 dùng regex strict yêu cầu timezone thì sẽ false-positive trên data sạch, gây halt oan. Tôi điều chỉnh regex để timezone suffix là optional.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**Run inject-bad** (`--no-refund-fix --skip-validate`): chunk policy refund với "14 ngày làm việc" được embed vào vector store.

```
question_id,contains_expected,hits_forbidden
q_refund_window,yes,yes   ← chunk stale lọt top-k
q_leave_version,yes,no
```

**Run khai-clean** (pipeline chuẩn, `run_id=khai-clean`): pipeline prune vector cũ (`embed_prune_removed=1`), chunk stale bị xóa khỏi collection.

```
question_id,contains_expected,hits_forbidden,llm_score
q_refund_window,yes,no,1   ← stale chunk đã prune
q_leave_version,yes,no,1
```

LLM-judge xác nhận 4/4 câu `llm_score=1` sau clean — context đủ faithful để trả lời chính xác.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ thay thế expectation suite thủ công bằng **Pydantic model** validate schema cleaned:

```python
class CleanedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    chunk_text: str
    effective_date: str
    exported_at: str

    @field_validator("exported_at")
    def must_be_iso_datetime(cls, v): ...
```

Cách này đủ điều kiện Distinction theo SCORING.md, đồng thời tự động mở rộng khi data contract thêm field mới mà không cần sửa từng expectation thủ công.
