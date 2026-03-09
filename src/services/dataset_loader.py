# services/dataset_loader.py
from __future__ import annotations
from pathlib import Path
import streamlit as st

from services.cache import dir_fingerprint, load_rig_dataset_cached, load_watercal_dataset_cached, fig_to_png, load_sptck_cached
from models.watercal_dataset import WaterCalDataset #Only for Typehints
import pandas as pd #Only for Typehints

# -------------------------------------------------------------------
# DATASET LOADING
# -------------------------------------------------------------------

def load_datasets(rig_dir, wcal_dir, sc_dir) -> tuple[WaterCalDataset, WaterCalDataset, pd.DataFrame]:
    """Load datasets based on current sidebar directory inputs."""
    print("Loading datasets")

    rig_fp = dir_fingerprint(Path(rig_dir))
    wcal_fp = dir_fingerprint(Path(wcal_dir))
    sc_fp = dir_fingerprint(Path(sc_dir))

    rig_ds  = load_rig_dataset_cached(rig_dir, rig_fp)
    wcal_ds = load_watercal_dataset_cached(wcal_dir, wcal_fp)
    sc_df = load_sptck_cached(sc_dir, sc_fp)

    return rig_ds, wcal_ds, sc_df


def reload_datasets() -> None:
    """ clear cache + rerun."""
    load_rig_dataset_cached.clear()
    load_watercal_dataset_cached.clear()
    load_sptck_cached.clear()
    fig_to_png.clear()
    st.rerun()