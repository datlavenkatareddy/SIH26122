"""
Shared CSV/XLSX reading and structured-progress-row detection for claim
intake. Used by both /api/v1/claims/file (generic file upload) and
/api/v1/claims/schedule-export (explicit P6/MSP progress export) so the two
endpoints don't maintain two different ideas of "which column is the
activity id".

Two distinct CSV/XLSX shapes show up in this project's real sample data:
  1. The canonical baseline schedule (sample_data/canonical/schedule.csv) --
     that's schedule *import*, handled entirely by shared/schedule.py via
     POST /api/v1/schedules. Not this module's concern.
  2. Field/discipline PROGRESS reports (sample_data/input/progress-report-csv,
     discipline-report-xlsx) -- one row per activity, with an activity-id
     column plus today's quantity/percentage. THIS is what this module
     detects and parses: each such row is one claim, not one file.

A file that doesn't look like shape 2 (no recognizable activity-id column)
is reported as such via read_tabular_file()/detect_progress_columns() so
the caller can fall back to free-text LLM extraction instead.
"""
import io
from dataclasses import dataclass
from datetime import date as date_type
from typing import Any, Optional

import pandas as pd

from backend.shared.discipline_normalize import normalize_discipline
from backend.shared.schemas import ClaimMode, Discipline, EventType, ExtractedClaimFields

# Column name variants actually seen across this project's sample field
# reports (progress-report-csv, discipline-report-xlsx) plus the schedule
# export shape already supported by /claims/schedule-export. Matching is
# case-insensitive and whitespace-trimmed (see _col below) so header casing
# differences don't matter.
#
# Deliberately does NOT include "task id"/"l6 task id": in this project's
# real progress-report fixtures, that column holds a per-report sub-task
# suffix (e.g. "CIV-PS3-TR-0180-01"), not the schedule's real activity_id
# (e.g. "CIV-PS3-TR-0180", which lives in "Activity ID"/"L5 Activity ID" in
# those same files). Treating it as the activity id would silently attach
# every claim to an id that doesn't exist in schedule_activities, degrading
# every match from EXACT_ID to a fuzzy fallback for no reason. A file with
# only a "Task ID"-style column and no genuine activity-id column falls back
# to free-text LLM extraction instead (see read_tabular_file's caller),
# which can use the row's full context rather than a single mislabeled cell.
_ACTIVITY_ID_COLUMNS = ("activity id", "l5 activity id")
_NAME_COLUMNS = ("activity name", "work description", "activity")
_DISCIPLINE_COLUMNS = ("discipline",)
_QTY_COLUMNS = ("today actual",)
_PRIOR_QTY_COLUMNS = ("prior actual",)
_PCT_COLUMNS = ("progress pct", "cumulative pct", "% complete", "progress")
_STATUS_COLUMNS = ("status", "status and evidence")
_DATE_COLUMNS = ("report date", "date", "data date")
_UOM_COLUMNS = ("unit", "uom")


@dataclass
class ProgressColumnMap:
    activity_col: str
    name_col: Optional[str]
    discipline_col: Optional[str]
    qty_col: Optional[str]
    prior_qty_col: Optional[str]
    pct_col: Optional[str]
    status_col: Optional[str]
    date_col: Optional[str]
    uom_col: Optional[str]


def _col(col_map: dict[str, str], *candidates: str) -> Optional[str]:
    for name in candidates:
        if name in col_map:
            return col_map[name]
    return None


def detect_progress_columns(columns: list[str]) -> Optional[ProgressColumnMap]:
    """
    Inspect a DataFrame's column names and decide whether this looks like a
    structured per-activity progress report (has a recognizable activity-id
    column). Returns None if it doesn't -- e.g. a narrative report, a sheet
    of unrelated data, or a table whose header row pandas didn't align with
    real headers (common with title/banner rows before the real header, see
    read_tabular_file's header-row search below).
    """
    col_map = {str(c).strip().lower(): c for c in columns}
    activity_col = _col(col_map, *_ACTIVITY_ID_COLUMNS)
    if activity_col is None:
        return None
    return ProgressColumnMap(
        activity_col=activity_col,
        name_col=_col(col_map, *_NAME_COLUMNS),
        discipline_col=_col(col_map, *_DISCIPLINE_COLUMNS),
        qty_col=_col(col_map, *_QTY_COLUMNS),
        prior_qty_col=_col(col_map, *_PRIOR_QTY_COLUMNS),
        pct_col=_col(col_map, *_PCT_COLUMNS),
        status_col=_col(col_map, *_STATUS_COLUMNS),
        date_col=_col(col_map, *_DATE_COLUMNS),
        uom_col=_col(col_map, *_UOM_COLUMNS),
    )


def _read_csv_robust(contents: bytes) -> pd.DataFrame:
    """
    CSV reading tolerant of the real-world variation the task calls out:
    a UTF-8 BOM (common from Excel "Save As CSV" on Windows), and a
    delimiter other than ',' (some exports use ';' or tab). pandas' C parser
    can't sniff the delimiter itself; the python engine with sep=None can.
    """
    text: str
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = contents.decode("latin-1")

    if not text.strip():
        raise ValueError("CSV file is empty.")

    try:
        df = pd.read_csv(io.StringIO(text))
        # A wrong delimiter (';', tab, ...) doesn't necessarily raise --
        # pandas happily returns a single garbage column containing the
        # whole line. Only trust a 1-column result if the source text
        # itself only had one column-worth of content (no ';'/tab
        # anywhere); otherwise fall through to delimiter sniffing below.
        if df.shape[1] > 1 or not any(ch in text for ch in (";", "\t")):
            return df
    except Exception:
        pass
    # Fall back to delimiter sniffing for non-comma-separated exports.
    return pd.read_csv(io.StringIO(text), sep=None, engine="python")


def _find_header_row(df: pd.DataFrame, max_scan: int = 10) -> int:
    """
    Some real XLSX exports (see discipline-report-xlsx sample fixtures)
    put a title/banner row (report name, project/date line) before the
    actual column headers, so pandas' default header=0 misreads the title
    as the header and the real header row as data. Scan the first few rows
    for one that contains a recognizable activity-id column name, and
    report its 0-based offset (0 = the header pandas already used, i.e. no
    correction needed).
    """
    if detect_progress_columns(list(df.columns)) is not None:
        return 0
    limit = min(max_scan, len(df))
    for i in range(limit):
        row_values = [str(v).strip() for v in df.iloc[i].tolist()]
        if detect_progress_columns(row_values) is not None:
            return i + 1  # header is this row; data starts after it
    return 0


def _reheader(df: pd.DataFrame, header_offset: int) -> pd.DataFrame:
    if header_offset == 0:
        return df
    new_header = df.iloc[header_offset - 1]
    reheadered = df.iloc[header_offset:].copy()
    reheadered.columns = [str(c).strip() for c in new_header]
    return reheadered.reset_index(drop=True)


def read_tabular_file(filename: str, contents: bytes) -> dict[str, pd.DataFrame]:
    """
    Read a .csv/.xlsx/.xls upload into {sheet_name: DataFrame}. CSV has an
    implicit single sheet named "". XLSX/XLS reads EVERY sheet (not just
    the first, which is the actual root cause of the Excel intake bug --
    pandas.read_excel defaults to sheet_name=0) and, per-sheet, corrects for
    a title row pushing the real header down (see _find_header_row).

    Raises ValueError for a file that can't be parsed at all (corrupt/empty/
    wrong format) -- the caller is expected to turn that into a clear 422,
    not swallow it into an empty result.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "csv":
        try:
            df = _read_csv_robust(contents)
        except Exception as e:
            raise ValueError(f"Could not parse CSV file: {e}") from e
        if df.empty:
            raise ValueError("CSV file has no data rows.")
        offset = _find_header_row(df)
        return {"": _reheader(df, offset)}

    if ext in ("xlsx", "xls"):
        try:
            sheets = pd.read_excel(io.BytesIO(contents), sheet_name=None, header=0)
        except Exception as e:
            raise ValueError(f"Could not parse Excel file: {e}") from e
        if not sheets:
            raise ValueError("Excel file has no sheets.")
        result: dict[str, pd.DataFrame] = {}
        for name, df in sheets.items():
            if df.empty:
                continue
            offset = _find_header_row(df)
            result[name] = _reheader(df, offset)
        if not result:
            raise ValueError("Excel file has no data rows in any sheet.")
        return result

    raise ValueError(f"Unsupported tabular file extension '.{ext}'")


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_pct(value: Any) -> Optional[float]:
    """
    Parse a percentage-complete cell to a 0-100 scale. Excel stores a
    percentage-formatted cell (e.g. displayed "91.7%") as the raw fraction
    0.917, not 91.7 -- pandas/openpyxl read that stored value, not the
    display string, so a column literally named "Progress" (as opposed to
    "Progress Pct", which this project's CSV exports already write on a
    0-100 scale) needs the fraction converted. A value already on a 0-100
    scale is returned unchanged. This can't perfectly distinguish "1" as a
    100%-complete fraction from a genuine "1%" reading, but the latter is
    not a realistic progress claim in this domain, so treating any 0 < v<=1
    value as a fraction is the correct call in practice.
    """
    pct = to_float(value)
    if pct is None:
        return None
    if 0 < pct <= 1:
        return pct * 100
    return pct


def build_claim_from_row(
    row: dict[str, Any],
    cols: ProgressColumnMap,
    discipline_hint: Optional[str] = None,
) -> Optional[tuple[str, ExtractedClaimFields]]:
    """
    Turn one structured progress-report row into (raw_claim_text,
    ExtractedClaimFields), with NO LLM call -- the row's own columns are the
    ground truth. Returns None if the row has no actual progress on it (a
    not-yet-started activity with 0 quantity and 0%/no percentage isn't a
    progress claim, matching the same gate schedule-export already applied
    against its own sample data).

    Shared by /api/v1/claims/file's structured CSV/XLSX path and
    /api/v1/claims/schedule-export, so both endpoints treat an "Activity
    ID" + "Today Actual"/"Progress Pct" row identically.

    discipline_hint: fallback discipline (raw text, e.g. a sheet name like
    "Civil") used when the row itself has no discipline column -- some real
    per-discipline XLSX exports (see discipline-report-xlsx fixtures) convey
    discipline via one sheet per discipline rather than a column at all.
    """
    activity_id = str(row.get(cols.activity_col) or "").strip()
    if not activity_id or activity_id.lower() == "nan":
        return None

    pct = normalize_pct(row.get(cols.pct_col)) if cols.pct_col else None
    qty = to_float(row.get(cols.qty_col)) if cols.qty_col else None

    has_progress_data = (pct is not None and pct > 0) or (qty is not None and qty > 0)
    if not has_progress_data:
        return None

    name = str(row.get(cols.name_col) or "").strip() if cols.name_col else ""
    discipline_raw = str(row.get(cols.discipline_col) or "").strip() if cols.discipline_col else ""
    status_val = str(row.get(cols.status_col) or "").strip() if cols.status_col else ""
    uom = str(row.get(cols.uom_col) or "").strip() if cols.uom_col else None
    if uom and uom.lower() == "nan":
        uom = None

    discipline_normalized = (
        normalize_discipline(discipline_raw)
        if discipline_raw
        else normalize_discipline(discipline_hint)
        if discipline_hint
        else None
    )
    discipline = (
        discipline_normalized
        if discipline_normalized in Discipline._value2member_map_
        else None
    )

    event_date: Optional[date_type] = None
    if cols.date_col:
        try:
            parsed = pd.to_datetime(row.get(cols.date_col))
            if pd.notna(parsed):
                event_date = parsed.date()
        except Exception:
            pass

    # A percentage column, when present, is the authoritative cumulative
    # progress signal (matches this project's real progress-report
    # convention). Only fall back to reporting the quantity as an
    # incremental contribution when no percentage was given at all --
    # otherwise a row with both columns (the common case) would need to
    # pick one arbitrarily to satisfy claim_mode's mutual-exclusivity rule.
    if pct is not None:
        claim_mode = ClaimMode.CUMULATIVE_PCT
        claimed_pct = pct
        claimed_quantity = None
        claimed_uom = None
    else:
        claim_mode = ClaimMode.INCREMENTAL_QUANTITY
        claimed_pct = None
        claimed_quantity = qty
        claimed_uom = uom

    # Prior==0 with real progress today is the row's own evidence that this
    # is the FIRST report of work on this activity -- not a guess, the
    # source report itself says so via its own Prior Actual column. That's
    # exactly what event_type=ACTUAL_START means, and the only way
    # institutional-memory/forecast's actual_start ever gets populated:
    # upsert_approved_actual() only ever sets it from an ACTUAL_START event's
    # own event_date (backend/shared/actuals.py), by design, to guarantee
    # every actual_start in approved_actuals traces back to something a
    # human actually reported -- never inferred/backfilled after the fact.
    prior_qty = to_float(row.get(cols.prior_qty_col)) if cols.prior_qty_col else None
    is_first_progress = prior_qty is not None and prior_qty == 0 and has_progress_data

    if pct is not None and pct >= 100:
        event_type = EventType.ACTUAL_FINISH
    elif is_first_progress:
        event_type = EventType.ACTUAL_START
    else:
        event_type = EventType.PROGRESS_UPDATE

    extracted = ExtractedClaimFields(
        event_date=event_date,
        reported_activity_id=activity_id,
        discipline=discipline,
        action=name or None,
        event_type=event_type,
        claim_mode=claim_mode,
        claimed_quantity=claimed_quantity,
        claimed_uom=claimed_uom,
        claimed_pct=claimed_pct,
        language_detected="English",
    )

    raw_text = f"Progress report for {activity_id}: {name} — {status_val}".strip(" —")
    return raw_text, extracted
