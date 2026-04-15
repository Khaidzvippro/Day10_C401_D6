"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.

Baseline (E1–E6): do instructor cung cấp.
Mở rộng (E7–E9): Nguyễn Tuấn Khải — Quality/Expectation Owner.
  E7 (halt): exported_at phải đúng định dạng ISO-8601 datetime (double-check sau cleaning layer)
             → phát hiện trường hợp cleaning bị bypass hoặc transform làm hỏng format
  E8 (warn): tỷ lệ chunk_text ngắn (<20 ký tự) không vượt 10% — cảnh báo nếu cleaning
             tạo ra quá nhiều chunk rác
  E9 (halt): tất cả doc_id trong cleaned phải nằm trong ALLOWED_DOC_IDS đồng bộ với
             cleaning_rules.py — phát hiện "rò rỉ" doc lạ vào vector store
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?$")


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Trả về (results, should_halt).

    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    results: List[ExpectationResult] = []

    # E1: có ít nhất 1 dòng sau clean
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # E2: không doc_id rỗng
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (r.get("chunk_text") or "")
    ]
    ok3 = len(bad_refund) == 0
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            ok3,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    # E4: chunk_text đủ dài
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            ok5,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    # E6: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (r.get("chunk_text") or "")
    ]
    ok6 = len(bad_hr_annual) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            ok6,
            "halt",
            f"violations={len(bad_hr_annual)}",
        )
    )

    # --- Mở rộng: Nguyễn Tuấn Khải ---

    # E7 (halt): exported_at phải đúng định dạng ISO-8601 datetime sau cleaning layer
    # Tại sao halt: nếu format sai → freshness_check sẽ không parse được → WARN/FAIL sai
    # Metric impact: cleaning Rule 7 (Khánh) quarantine row có exported_at sai/rỗng TRƯỚC khi
    #   vào đây; E7 là lớp double-check — phát hiện nếu cleaning bị bypass (--skip-validate)
    #   hoặc transform pipeline làm hỏng format sau khi clean.
    # Test: chạy inject (--no-refund-fix --skip-validate) với row có exported_at="invalid"
    #   → E7 FAIL (halt) xuất hiện trong log
    bad_exported_fmt = [
        r for r in cleaned_rows
        if not _ISO_DATETIME.match((r.get("exported_at") or "").strip())
    ]
    ok7 = len(bad_exported_fmt) == 0
    results.append(
        ExpectationResult(
            "exported_at_iso_format",
            ok7,
            "halt",
            f"invalid_exported_at_count={len(bad_exported_fmt)}",
        )
    )

    # E8 (warn): tỷ lệ chunk_text ngắn (<20 ký tự) không vượt 10% tổng cleaned
    # Tại sao warn (không halt): một vài chunk tiêu đề ngắn có thể hợp lệ; chỉ cảnh báo
    #   khi tỷ lệ cao → dấu hiệu cleaning rule sinh ra nhiều chunk rác
    # Metric impact: cleaning Rule 8 (Khánh) đã quarantine chunk trivial/ngắn; E8 đo
    #   xem có "lọt lưới" không. Nếu ratio >10% → cleaning chưa đủ mạnh.
    # Test: inject nhiều chunk ngắn qua --skip-validate → E8 WARN với ratio > 10%
    short_20 = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 20]
    ratio_short = len(short_20) / len(cleaned_rows) if cleaned_rows else 0.0
    ok8 = ratio_short <= 0.10
    results.append(
        ExpectationResult(
            "short_chunk_ratio_under_10pct",
            ok8,
            "warn",
            f"short_chunks_lt20={len(short_20)} ratio={ratio_short:.2%} threshold=10%",
        )
    )

    # E9 (halt): tất cả doc_id trong cleaned phải nằm trong ALLOWED_DOC_IDS
    # Đồng bộ với cleaning_rules.py (Khánh đã thêm access_control_sop vào ALLOWED_DOC_IDS)
    # Tại sao halt: doc lạ lọt vào vector store → agent trả lời dựa trên dữ liệu không kiểm soát
    # Metric impact: phát hiện nếu cleaning bị bypass (--skip-validate) với doc_id="legacy_catalog_xyz_zzz"
    # Test: inject row có doc_id="unknown_source" qua --skip-validate → E9 FAIL (halt)
    ALLOWED_DOC_IDS = frozenset({
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
        "access_control_sop",  # đồng bộ với cleaning_rules.py (Khánh thêm Rule 10)
    })
    illegal_doc = [r for r in cleaned_rows if r.get("doc_id", "") not in ALLOWED_DOC_IDS]
    ok9 = len(illegal_doc) == 0
    results.append(
        ExpectationResult(
            "doc_id_in_allowlist",
            ok9,
            "halt",
            f"illegal_doc_id_count={len(illegal_doc)} examples={[r.get('doc_id') for r in illegal_doc[:3]]}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt
