# WaterCal Analysis – Overview

## Structure
watercal/
├─ watercal_register.py   # Single calibration (model, validation, regression, calculator)
├─ watercal_dataset.py    # Multi-record loader + indexing + filtering
├─ PyGUI.py               # Terminal UI
└─ WebGUI.py              # Streamlit Web UI


## Purpose
Manages water valve calibrations and allows a calculation of:
Volume (µL) → Valve open time (ms)
(using regression if within calibrated range)


## Supported data layouts

### WaterCal JSON
If WaterCal JSON is used, rig/computer info can be taken from the input rig_json logged in the same directory.
### Expected Layout
main_dir/
    any_subdir/
        water_calibration.json 
        behavior/logs/rig_input.json

#### water_calibration.json Contains the calibration data:
- measurements
- interval_average
- slope / offset / R²
- date / notes
#### behavior/logs/rig_input.json contains 
- computer_name 
- rig_name


### Rig JSON

#### Expected Layout
rig_jsons_main_dir/
    <computer_name>/
        *.json  

#### *.json Contains:
- computer_name
- rig_name (ex: 5A, 12B)
- calibration.water_valve

## Capabilities

### Loading
- Reads all JSON files in directory tree
- Accepts Rig JSON or WaterCal JSON
- Skips invalid files (logged)
- Groups records by:
  - rig_name
  - rig number (numeric prefix)
  - computer_name

### Filtering
- All records
- Valid only
- With errors
- With warnings
- By rig name
- By rig number
- Recent calibrations

### Calculator
- Converts µL → ms
- Checks calibrated bounds

### Validation & Quality Checks
Load / Parse
- JSON read errors
- Schema validation failures

Schema Validation Issues
- repeat_count ≤ 20
- < 2 measurements
- invalid interval_average
- non-positive values

Data Consistency
- missing interval_average entries
- mismatch vs measured averages
- regression mismatch

Regression Quality
- low R²
- abnormal slope
- excessive offset


## UI

### PyGUI
- Terminal menu grouped by rig #
- Shows slope / offset / R²
- Displays warnings/errors
- Plot support
- Built-in calculator

### WebGUI
- Streamlit interface
- Interactive filtering + plotting


## Logging

Enable debug info with:

import logging
logging.basicConfig(level=logging.INFO)