# services/cache.py
from __future__ import annotations

from pathlib import Path
from io import BytesIO
from typing import List, Tuple

import hashlib
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd #Only for Typehints

from models.watercal_dataset import WaterCalDataset  
from models.watercal_model import WaterCalRecord     # only for type hints
from models.spotcheck_model import load_dataframe


# ----------- Hashing -----------
def record_plot_fingerprint(rec: WaterCalRecord) -> str:
    """
    Deterministic key for a record's plot image. Minimal but stable:
    coefficients + date. (Per your preference, coefficients are sufficient.)
    """
    s, o, r2 = rec.preferred_coefficients
    date_str = rec.date.isoformat() if rec.date else ""
    raw = f"{s:.6f}|{o:.6f}|{r2:.6f}|{date_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def dir_fingerprint(root: Path) -> str:
    """
    Creates a fingerprint from all *.json files under 'root' so the cache
    invalidates when contents change (path + mtime + size).
    """
    h = hashlib.md5()
    if not root.exists():
        return "missing"
    for p in sorted(root.rglob("*.json")):
        try:
            stat = p.stat()
            h.update(str(p).encode())
            h.update(str(stat.st_mtime_ns).encode())
            h.update(str(stat.st_size).encode())
        except Exception:
            # Ensure a stable hash even if a file temporarily fails stat()
            h.update(f"err:{p}".encode())
    return h.hexdigest()

# ----------- Reload Utility -----------
def clear_dataset_caches() -> None:
    """Clear dataset caches (used by Reload button)."""
    load_rig_dataset_cached.clear()
    load_watercal_dataset_cached.clear()


# ----------- Streamlit caches -----------
@st.cache_data(show_spinner=False)
def load_watercal_dataset_cached(water_cal_dir: str, dir_fp: str) -> WaterCalDataset:
    """
    Cached dataset loader for 'water-cal' directory.
    The 'dir_fp' argument is intentionally unused, but included so cache invalidates
    when the directory fingerprint changes.
    """
    return WaterCalDataset.load_from_water_cal_dir(water_cal_dir)

@st.cache_data(show_spinner=False)
def load_rig_dataset_cached(rig_dir_str: str, dir_fp: str) -> WaterCalDataset:
    """
    Cached dataset loader for 'rig jsons' directory.
    The 'dir_fp' argument is intentionally unused, but included so cache invalidates
    when the directory fingerprint changes.
    """
    return WaterCalDataset.load_from_rigs(rig_dir_str)

@st.cache_data(show_spinner=False)
def load_sptck_cached(df_dir: str, dir_fp: str) -> pd.DataFrame:
    """
    Cached dataset loader for 'rig jsons' directory.
    The 'dir_fp' argument is intentionally unused, but included so cache invalidates
    when the directory fingerprint changes.
    """
    return load_dataframe(df_dir)

@st.cache_data(show_spinner=False)
def fig_to_png(_fig, cache_key: str, dpi: int = 180) -> bytes:
    """
    Cache the expensive 'Matplotlib Figure -> PNG bytes' conversion.

    `_fig` is intentionally prefixed with underscore so Streamlit ignores it in the cache key.
    The cache depends only on `cache_key` (provide a stable fingerprint).
    """
    buf = BytesIO()
    _fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(_fig)
    buf.seek(0)
    return buf.read()

@st.cache_data(show_spinner=False)
def list_spotcheck_files(dir_path: str) -> List[Tuple[str, float, float]]:
    """
    Lightweight listing of *.json under a spotcheck directory.
    Returns list of (relative_path, size_bytes, mtime_ts).
    """
    root = Path(dir_path)
    out: List[Tuple[str, float, float]] = []
    if not root.exists():
        return out
    for p in sorted(root.rglob("*.json")):
        try:
            stat = p.stat()
            out.append((str(p.relative_to(root)), float(stat.st_size), float(stat.st_mtime)))
        except Exception:
            continue
    return out