# ui.sidebar.py
from __future__ import annotations

import streamlit as st

from config import DAYS_FILTER_DEFAULT
from models.watercal_dataset import WaterCalDataset 


def render_filters(all_rigs: list) -> tuple[str, int]:
    """ Renders the rig dropdown and recent-days filter. """
    # Render controls (dropdown will be refreshed later in pages)
    rig_filter = st.sidebar.selectbox("Filter by rig:", options=["All"]+all_rigs, key="rig_filter")
    recent_days = st.sidebar.number_input(
        "Show only records in last N days (0 = all)",
        min_value=0, step=30, key="recent_days", value=DAYS_FILTER_DEFAULT
    )
    return rig_filter, int(recent_days)

def show_skipped_files(rig_ds:WaterCalDataset, wcal_ds:WaterCalDataset): 
    """Added a skipped files info (both datasets if available)"""
    if rig_ds.skipped_files:
        with st.sidebar.expander(f"Rigs - Skipped files: {len(rig_ds.skipped_files)}", expanded=False):
            for p, reason in rig_ds.skipped_files[:20]:
                st.write(f"- `{p}` — {reason}")
            if len(rig_ds.skipped_files) > 20:
                st.caption(f"... and {len(rig_ds.skipped_files) - 20} more")

    if wcal_ds.skipped_files:
        with st.sidebar.expander(f"WaterCal - Skipped files: {len(wcal_ds.skipped_files)}", expanded=False):
            for p, reason in wcal_ds.skipped_files[:20]:
                st.write(f"- `{p}` — {reason}")
            if len(wcal_ds.skipped_files) > 20:
                st.caption(f"... and {len(wcal_ds.skipped_files) - 20} more")