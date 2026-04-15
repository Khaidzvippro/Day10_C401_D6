"""
Kiểm tra freshness từ manifest pipeline (SLA đơn giản theo giờ).

Sinh viên mở rộng: đọc watermark DB, so sánh với clock batch, v.v.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Cho phép "2026-04-10T08:00:00" không có timezone
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def check_manifest_freshness(
    manifest_path: Path,
    *,
    sla_hours: float = 24.0,
    now: datetime | None = None,
    check_publish_boundary: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """
    Trả về ("PASS" | "WARN" | "FAIL", detail dict).

    Đọc trường `latest_exported_at` hoặc max exported_at trong cleaned summary.
    """
    now = now or datetime.now(timezone.utc)
    if not manifest_path.is_file():
        return "FAIL", {"reason": "manifest_missing", "path": str(manifest_path)}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    ts_raw = data.get("latest_exported_at") or data.get("run_timestamp")
    dt = parse_iso(str(ts_raw)) if ts_raw else None
    if dt is None:
        return "WARN", {"reason": "no_timestamp_in_manifest", "manifest": data}

    source_age_hours = (now - dt).total_seconds() / 3600.0
    detail: Dict[str, Any] = {
        "latest_exported_at": ts_raw,
        "age_hours": round(source_age_hours, 3),
        "sla_hours": sla_hours,
    }

    status = "PASS" if source_age_hours <= sla_hours else "FAIL"
    if status == "FAIL":
        detail["reason"] = "freshness_sla_exceeded"

    if check_publish_boundary:
        publish_raw = data.get("publish_timestamp") or data.get("run_timestamp")
        publish_dt = parse_iso(str(publish_raw)) if publish_raw else None
        if publish_dt is None:
            detail["publish_boundary"] = {"reason": "missing_publish_timestamp"}
            return "WARN", detail

        publish_age_hours = (now - publish_dt).total_seconds() / 3600.0
        detail["publish_boundary"] = {
            "publish_timestamp": publish_raw,
            "publish_age_hours": round(publish_age_hours, 3),
            "sla_hours": sla_hours,
        }
        if publish_age_hours > sla_hours:
            detail["publish_boundary"]["reason"] = "publish_boundary_sla_exceeded"
            status = "FAIL"

    return status, detail
