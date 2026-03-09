# spotcheck_model.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import logging

import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger()


# ----------------- Pydantic models  -----------------
class SpotCheckInput(BaseModel):
    valve_open_time_ms: float = Field(..., ge=0, description="Valve open time in milliseconds")
    target_volume_microliters: float = Field(..., gt=0, description="Target drop volume in microliters (must be > 0)")
    repeat_count: int = Field(..., ge=1, description="Number of repeated valve actuations (>= 1)")
    ok_margin_pct: float = Field(10.0, ge=0.0, description="Half-band for OK classification in percent (e.g., 10 -> ±10%)")
    strike_margin_pct: float = Field(15.0, ge=0.0, description="Half-band for Strike classification; must be >= ok_margin_pct")

    @model_validator(mode="after")
    def _validate_margins(self) -> "SpotCheckInput":
        if self.strike_margin_pct < self.ok_margin_pct:
            raise ValueError("strike_margin_pct must be >= ok_margin_pct")
        return self


class SpotCheckOutput(BaseModel):
    total_delivered_grams: float = Field(..., ge=0, description="Total mass delivered in grams")
    drop_volume_microliters: float = Field(..., ge=0, description="Calculated drop volume in microliters")
    error_percentage: float = Field(..., ge=0, description="Percentage error from target volume")
    ok: bool = Field(..., description="Whether the spot check passed tolerance")
    strike: bool = Field(..., description="Whether this result counts as a strike")


class SpotCheckData(BaseModel):
    date: datetime = Field(..., description="ISO8601 timestamp of the spotcheck")
    rig_name: str
    last_calibration_date: datetime = Field(..., description="ISO8601 timestamp of the last calibration")
    notes: Optional[str] = None
    input: SpotCheckInput
    output: SpotCheckOutput

    @field_validator("date", "last_calibration_date")
    @classmethod
    def ensure_tzaware(cls, v: datetime):
        if v.tzinfo is None:
            raise ValueError("Datetime must include timezone")
        return v.astimezone(timezone.utc)


def _timestamp_for_filename(dt: datetime) -> str:
    """Produce a filename-safe UTC timestamp. Example: 2026-03-07T044512Z"""
    return dt.strftime("%Y-%m-%dT%H%M%SZ")


def _default_filename(rig_name: str, dt: datetime) -> str:
    return f"{rig_name}-{_timestamp_for_filename(dt)}.json"


def _safe_write_json(path: Path, payload: dict) -> Path:
    """ Write JSON to 'path'. If a file exists append '(1)', '(2)', ... before the suffix."""
    target = path

    idx = 1
    while target.exists():
        target = path.with_name(f"{path.stem}-({idx}){path.suffix}")
        idx += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return target


# ----------------- Public API -----------------
def save_spotcheck(main_dir: str | Path, sc: SpotCheckData) -> Path:
    """
    Save a single SpotCheckData to JSON at:
      main_dir/<rig_name>/<rig_name>-<UTC timestamp>.json
    Returns the path written.
    """
    main_dir = Path(main_dir)

    rig_dir = main_dir / sc.rig_name
    filename = _default_filename(sc.rig_name, sc.date)
    path = rig_dir / filename

    payload = sc.model_dump(mode="json")

    return _safe_write_json(path, payload)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        raise ValueError("start/end must be timezone-aware")
    return dt.astimezone(timezone.utc)



def compute_output(sc_in: SpotCheckInput, total_delivered_grams: float) -> SpotCheckOutput:
    """
    Compute SpotCheckOutput from SpotCheckInput and measured total mass (g).

    Method:
      - target_total_g = (target_volume_microliters / 1000) * repeat_count
      - ratio = total_delivered_grams / target_total_g
      - error% = |ratio - 1| * 100
      - OK if ratio ∈ [1 - ok_margin, 1 + ok_margin]
      - Strike if ratio ∈ [1 - strike_margin, 1 - ok_margin) ∪ (1 + ok_margin, 1 + strike_margin]
      - Else: Failed (ok=False, strike=False)

    Assumptions:
      - target_volume_microliters > 0
      - repeat_count >= 1
      - total_delivered_grams >= 0
    """
    # Convert target drop volume to grams using water density ~1 g/mL (1 µL = 0.001 g)
    target_total_g = (sc_in.target_volume_microliters / 1000.0) * sc_in.repeat_count
    ratio = float(total_delivered_grams) / target_total_g

    ok_band = sc_in.ok_margin_pct / 100.0
    strike_band = sc_in.strike_margin_pct / 100.0

    lower_ok, upper_ok = 1.0 - ok_band, 1.0 + ok_band
    lower_strike, upper_strike = 1.0 - strike_band, 1.0 + strike_band

    # Classification
    if lower_ok <= ratio <= upper_ok:
        ok_flag = True
        strike_flag = False
    elif (lower_strike <= ratio < lower_ok) or (upper_ok < ratio <= upper_strike):
        ok_flag = False
        strike_flag = True
    else:
        ok_flag = False
        strike_flag = False  # "Failed"

    # Mean per-drop volume (µL) from measured total
    drop_ul = (float(total_delivered_grams) / sc_in.repeat_count) * 1000.0
    err_pct = abs(ratio - 1.0) * 100.0

    return SpotCheckOutput(
        total_delivered_grams=float(total_delivered_grams),
        drop_volume_microliters=drop_ul,
        error_percentage=err_pct,
        ok=ok_flag,
        strike=strike_flag,
    )


def load_dataframe(
    main_dir: str | Path,
    *,
    rig_filter: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    include_path: bool = False,
) -> pd.DataFrame | None:
    """
    Load all valid spotcheck JSONs under `main_dir` (recursively) into a pandas DataFrame.

    - Recursively scans: main_dir/**/*.json
    - Validates/normalizes each file via SpotCheckData (strict tz-aware datetime).
    - Applies inclusive time filters (start <= date <= end) if provided.
    - Flattens nested 'input' and 'output' into prefixed columns.
    - Optionally includes a 'path' column with the source file path.
    - Returns None if no valid records are found.

    Columns:
      date (datetime64[ns, UTC]), rig_name, notes,
      last_calibration_date (datetime64[ns, UTC]),
      input.valve_open_time_ms, input.target_volume_microliters, input.repeat_count,
      output.total_delivered_grams, output.drop_volume_microliters,
      output.error_percentage, output.ok, output.strike,
      days_since_calibration,
      [path] (if include_path=True)
    """
    # Normalize/validate filters to UTC-aware datetimes
    start = _ensure_utc(start)
    end = _ensure_utc(end)

    main_dir = Path(main_dir)
    rows: List[dict] = []

    # Recurse over all JSON files
    for file in main_dir.rglob("*.json"):
        try:
            with file.open("r", encoding="utf-8") as f:
                raw = json.load(f)

            # Validate & normalize with Pydantic (raises if datetimes are naive)
            sc = SpotCheckData.model_validate(raw)

            # Filters
            if start and sc.date < start:
                continue
            if end and sc.date > end:
                continue
            if rig_filter and sc.rig_name != rig_filter:
                continue

            row = {
                "Date": sc.date,  # tz-aware UTC (see validator)
                "Rig": sc.rig_name,
                "Notes": sc.notes,
                "Last calibration": sc.last_calibration_date,
                "I) Valve open time (ms)": sc.input.valve_open_time_ms,
                "I) Target vol (µl)": sc.input.target_volume_microliters,
                "I) Repeat count": sc.input.repeat_count,
                "I) Target weight (g)": sc.input.repeat_count * sc.input.target_volume_microliters / 1000.0,
                "O) Delivered (g)": sc.output.total_delivered_grams,
                "O) Mean Drop (µl)": sc.output.drop_volume_microliters,
                "O) Error %": sc.output.error_percentage,
                "O) OK?": sc.output.ok,
                "O) Strike?": sc.output.strike,
            }
            if include_path:
                row["path"] = str(file)
            rows.append(row)

        except Exception:
            logger.error(f"Error opening/parsing {file} — skipping", exc_info=True)
            continue

    if not rows:
        logger.error("Spotcheck dataframe is empty")
        return None

    df = pd.DataFrame(rows)

    # Normalize datetime columns to UTC-aware dtype in DataFrame
    df["Date"] = pd.to_datetime(df["Date"], utc=True)
    df["Last calibration"] = pd.to_datetime(df["Last calibration"], utc=True)

    # Useful default sort
    df = df.sort_values("Date", ascending=False).reset_index(drop=True)
    return df
