# To run> streamlit run src/WebGUI.py --server.port 8501 --server.address 0.0.0.0

import logging
from pathlib import Path

import streamlit as st

from watercal_dataset import WaterCalDataset, DEFAULT_MAIN_DIR
from watercal_model import WaterCalRecord

# ------------- Streamlit Page Config -------------
st.set_page_config(page_title="Water Calibration Dashboard", layout="wide")
st.title("💧 Water Calibration Dashboard")

# ------------- Logging (optional) -------------
# Configure once; adjust level as needed. In production you might configure elsewhere.
logging.basicConfig(
    level=logging.INFO,  # switch to DEBUG for more detail
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def format_status(record: WaterCalRecord) -> str:
    """Return a compact status string for warnings/errors."""
    if record.errors:
        return f"❌ {record.n_errors}"
    if record.warnings:
        return f"⚠️ {record.n_warnings}"
    return "✅"


# ------------- Sidebar Controls -------------
st.sidebar.header("Settings")

main_dir_input = st.sidebar.text_input("Shared JSON folder:", str(DEFAULT_MAIN_DIR))
main_path = Path(main_dir_input)


if not main_path.exists():
    st.error(f"Folder not found: {main_path}", icon="🚨")
    st.stop()

# Load dataset
with st.spinner("Loading calibration data..."):
    # ds = WaterCalDataset.load_from_rigs(main_path)
    ds = WaterCalDataset.load_from_water_cal_dir(r"C:\Data\Water-cal")

# Skipped files panel
if ds.skipped_files:
    with st.sidebar.expander(f"Skipped files: {len(ds.skipped_files)}", expanded=False):
        # Show the first 20; huge lists can overwhelm the UI
        for p, reason in ds.skipped_files[:20]:
            st.write(f"- `{p}` — {reason}")
        if len(ds.skipped_files) > 20:
            st.caption(f"... and {len(ds.skipped_files) - 20} more")

if not ds.records:
    st.warning("No calibration files found after filtering.", icon="⚠️")
    st.stop()

# Filters
rig_names = sorted({r.rig_name for r in ds.records if r.rig_name})
rig_filter = st.sidebar.selectbox("Filter by rig:", ["All"] + rig_names)
errors_only = st.sidebar.checkbox("Show only records with errors", value=False)
warnings_only = st.sidebar.checkbox("Show only records with warnings", value=False)
recent_days = st.sidebar.number_input("Show only records in last N days (0 = all)", min_value=0, value=0, step=30)

# Apply filters
filtered = ds.records
if rig_filter != "All":
    filtered = [r for r in filtered if r.rig_name == rig_filter]
if errors_only:
    filtered = [r for r in filtered if r.errors]
if warnings_only:
    filtered = [r for r in filtered if r.warnings]
if recent_days and recent_days > 0:
    # Use the dataset helper to avoid tz pitfalls; then keep only those in filtered
    recent = set(ds.recent_only(max_age_days=int(recent_days)))
    filtered = [r for r in filtered if r in recent]

st.subheader(f"Found {len(filtered)} calibration file(s)")

# ------------- Main List -------------
for i, rec in enumerate(filtered, 1):
    slope, offset, r2 = rec.preferred_coefficients
    status = format_status(rec)
    date_str = rec.date.strftime("%Y-%m-%d") if rec.date else "NoDate"

    title = f"{i}. {rec.record_id} — {rec.rig_name} @ {rec.computer_name} [{status}]"
    with st.expander(title, expanded=False):
        cols = st.columns([1, 2], gap="large")

        with cols[0]:
            st.markdown(f"**Date:** {date_str}")
            st.markdown(f"**Regression:** `W = {slope:.5f}·t {offset:+.5f}`  (R² = `{r2:.3f}`)")

            # Warnings/Errors
            if rec.warnings:
                st.warning("Warnings:\n\n- " + "\n- ".join(rec.warnings))
            if rec.errors:
                st.error("Errors:\n\n- " + "\n- ".join(rec.errors))

            # Calculator
            microliters = st.number_input(
                "Volume (µL) → Valve open time (ms):",
                min_value=0.0,
                step=1.0,
                key=f"vol_{i}"
            )
            if microliters > 0:
                inside_bounds, low_vol, hi_vol = rec.check_bounds(microliters, unit="microliters")
                if not inside_bounds:
                    st.warning(f"{microliters:.0f} µL is outside calibrated range ({low_vol:.0f}–{hi_vol:.0f} µL).")
                else:
                    t_ms = rec.calc_milliseconds_from_microliters(microliters)
                    st.success(f"Estimated valve open time: **{t_ms:.2f} ms**")

        with cols[1]:
            fig, _ = rec.plot(show_slope_band = True, draw = False)
            st.pyplot(fig, width='stretch')