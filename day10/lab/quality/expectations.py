"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


DOCS_DIR = Path(__file__).resolve().parents[1] / "data" / "docs"

@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def _allowed_doc_ids_from_docs() -> set[str]:
    """Use data/docs/*.txt filenames as the source catalog for valid doc_id values."""
    if not DOCS_DIR.is_dir():
        return set()
    return {p.stem for p in DOCS_DIR.glob("*.txt") if p.is_file()}


def _parse_exported_at(raw: str) -> datetime | None:
    """Parse exported_at về UTC datetime để validate chronology sau clean."""
    s = (raw or "").strip()
    if not s:
        return None

    if s.isdigit():
        try:
            return datetime.fromtimestamp(int(s), tz=timezone.utc)
        except (OverflowError, ValueError):
            return None

    iso_candidate = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_candidate)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    for fmt in ("%d/%m/%Y %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


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
    allowed_doc_ids = _allowed_doc_ids_from_docs()
    unknown_doc = [
        r
        for r in cleaned_rows
        if allowed_doc_ids and (r.get("doc_id") or "").strip() not in allowed_doc_ids
    ]
    ok_allowlist = len(unknown_doc) == 0
    results.append(
        ExpectationResult(
            "doc_id_in_docs_allowlist",
            ok_allowlist,
            "halt",
            f"unknown_doc_id_count={len(unknown_doc)} allowed_doc_ids={sorted(allowed_doc_ids)}",
        )
    )

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

    # E6: effective_date phải là ngày hợp lệ lịch (không chỉ đúng regex)
    calendar_bad = []
    for r in cleaned_rows:
        s = (r.get("effective_date") or "").strip()
        try:
            datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            calendar_bad.append(r)
    ok6 = len(calendar_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_calendar_valid",
            ok6,
            "halt",
            f"invalid_calendar_rows={len(calendar_bad)}",
        )
    )

    # E7: chronology consistency exported_at không được nhỏ hơn effective_date
    chronology_bad = []
    for r in cleaned_rows:
        exported_dt = _parse_exported_at(r.get("exported_at") or "")
        if exported_dt is None:
            continue
        try:
            effective_dt = datetime.strptime((r.get("effective_date") or "").strip(), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        if exported_dt < effective_dt:
            chronology_bad.append(r)
    ok7 = len(chronology_bad) == 0
    results.append(
        ExpectationResult(
            "exported_not_before_effective",
            ok7,
            "halt",
            f"chronology_violations={len(chronology_bad)}",
        )
    )

    # E8: chunk_text sau clean phải được normalize format (không HTML/space bẩn/CRLF)
    format_bad = []
    for r in cleaned_rows:
        txt = r.get("chunk_text") or ""
        if re.search(r"<[^>]+>", txt):
            format_bad.append(r)
            continue
        if "\r" in txt:
            format_bad.append(r)
            continue
        if txt.strip() != txt:
            format_bad.append(r)
            continue
        if "\n\n" in txt:
            format_bad.append(r)
            continue
        lines = txt.split("\n")
        if any("  " in line for line in lines):
            format_bad.append(r)
            continue
    ok8 = len(format_bad) == 0
    results.append(
        ExpectationResult(
            "chunk_text_normalized_format",
            ok8,
            "halt",
            f"format_violations={len(format_bad)}",
        )
    )

    # E9: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (r.get("chunk_text") or "")
    ]
    ok9 = len(bad_hr_annual) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            ok9,
            "halt",
            f"violations={len(bad_hr_annual)}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt
