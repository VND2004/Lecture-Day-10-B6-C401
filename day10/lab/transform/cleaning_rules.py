"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
        "access_control_sop",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        # Rule name: effective_date_iso_calendar_valid
        # ISO đúng pattern nhưng phải là ngày tồn tại trong lịch thực.
        try:
            datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return "", "invalid_effective_date_calendar"
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        try:
            dt = datetime.strptime(f"{yyyy}-{mm}-{dd}", "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d"), ""
        except ValueError:
            return "", "invalid_effective_date_calendar"
    return "", "invalid_effective_date_format"


def _parse_exported_at(raw: str) -> datetime | None:
    """
    Parse exported_at sang UTC datetime để so sánh chronology.

    Chấp nhận một số format phổ biến trong lab:
    - ISO 8601 có timezone hoặc 'Z'
    - ISO 8601 không timezone (coi là UTC)
    - Unix epoch (giây)
    - dd/mm/YYYY HH:MM:SS và YYYY/mm/dd HH:MM:SS
    """
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


def _normalize_chunk_text(text: str) -> str:
    """
    Rule name: normalize_chunk_text_format_noise

    Chuẩn hóa format chunk_text:
    - strip HTML tags
    - normalize whitespace dư
    - giữ newline nội dung nhưng chuẩn hóa về '\n'
    """
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    no_html = _HTML_TAG_RE.sub(" ", raw)

    lines = []
    for line in no_html.split("\n"):
        compact = " ".join(line.split())
        if compact:
            lines.append(compact)
    return "\n".join(lines).strip()


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_doc_id_allowlist: bool = True,
    apply_effective_date_cleaning: bool = True,
    apply_required_field_check: bool = True,
    apply_hr_stale_filter: bool = True,
    apply_text_normalization: bool = True,
    apply_chronology_check: bool = True,
    apply_dedupe: bool = True,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Normalize chunk_text: strip HTML, chuẩn hoá whitespace/newline.
    5) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    6) Quarantine: chronology lỗi khi exported_at < effective_date.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        if apply_doc_id_allowlist and doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm = eff_raw
        if apply_effective_date_cleaning:
            eff_norm, eff_err = _normalize_effective_date(eff_raw)
            if eff_err == "empty_effective_date":
                quarantine.append({**raw, "reason": "missing_effective_date"})
                continue
            if eff_err == "invalid_effective_date_format":
                quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
                continue
            if eff_err == "invalid_effective_date_calendar":
                quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
                continue

        if (
            apply_hr_stale_filter
            and doc_id == "hr_leave_policy"
            and _ISO_DATE.match(eff_norm)
            and eff_norm < "2026-01-01"
        ):
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        if apply_text_normalization:
            text = _normalize_chunk_text(text)

        if apply_required_field_check and not eff_norm:
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue

        if apply_required_field_check and not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # Rule name: exported_before_effective_date
        # Nếu parse được exported_at và exported_at < effective_date thì quarantine.
        if apply_chronology_check:
            exported_dt = _parse_exported_at(exported_at)
            if exported_dt is not None:
                try:
                    effective_dt = datetime.strptime(eff_norm, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    effective_dt = None
            else:
                effective_dt = None
            if exported_dt is not None and effective_dt is not None:
                if exported_dt < effective_dt:
                    quarantine.append(
                        {
                            **raw,
                            "reason": "exported_before_effective_date",
                            "effective_date_normalized": eff_norm,
                        }
                    )
                    continue

        if apply_dedupe:
            key = _norm_text(text)
            if key in seen_text:
                quarantine.append({**raw, "reason": "duplicate_chunk_text"})
                continue
            seen_text.add(key)

        fixed_text = text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at or "",
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
