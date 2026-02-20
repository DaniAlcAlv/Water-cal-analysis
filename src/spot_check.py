#!/usr/bin/env python3
"""
Interactive config browser (rig-first).

- Directory layout:
    main_dir/
        <computer_name_1>/
            config_a.json
            config_b.json
        <computer_name_2>/
            config_c.json
            ...
- Each JSON minimal shape:
{
  "computer_name": str,
  "rig_name": str,           # e.g., "5A", "12A", "12B"
  "calibration": {
    "water_valve": {
      "output": {
        "interval_average": { str(float): float, ... },
        "slope": float,
        "offset": float,
        "r2": float
      }
    }
  }
}
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------- Configuration ----------
DEFAULT_MAIN_DIR = Path("F:\Data\Rig 2026-2-19")  


# ---------- Data structure ----------
class ConfigRecord:
    def __init__(self, file_path: Path, data: Dict[str, Any]):
        self.file_path = file_path
        self.data = data

    @property
    def computer_name(self) -> Optional[str]:
        return self.data.get("computer_name")

    @property
    def rig_name(self) -> Optional[str]:
        return self.data.get("rig_name")

    def get_water_valve_output(self) -> Dict[str, Any]:
        calib = self.data.get("calibration") or {}
        wv = (calib.get("water_valve") or {}).get("output") or {}
        return wv

    def compact_line(self) -> str:
        """One-line summary for list view under a rig."""
        comp = self.computer_name or "<missing computer>"
        wv = self.get_water_valve_output()
        slope = wv.get("slope")
        offset = wv.get("offset")
        # Render key stats compactly; guard Nones
        def fmt(v):
            if isinstance(v, (int, float)):
                return f"{v:.4g}"
            return str(v) if v is not None else "NA"
        return f"Computer: {comp:<20} | File: {self.file_path.name:<30} | slope={fmt(slope)}, offset={fmt(offset)}"

    def summary(self) -> str:
        """Full details for a selected file."""
        comp = self.computer_name or "<missing>"
        rig = self.rig_name or "<missing>"
        wv = self.get_water_valve_output()

        slope = wv.get("slope")
        offset = wv.get("offset")
        r2 = wv.get("r2")
        interval_avg = wv.get("interval_average") or {}

        # Parse interval_average keys to float when possible and sort
        pairs: List[Tuple[Any, Any]] = []
        for k, v in interval_avg.items():
            try:
                fk = float(k)
                pairs.append((fk, v))
            except (ValueError, TypeError):
                pairs.append((k, v))

        def sort_key(item):
            k, _ = item
            return (0, k) if isinstance(k, float) else (1, str(k))

        pairs.sort(key=sort_key)

        interval_lines = []
        for k, v in pairs:
            disp_k = f"{k:.6g}" if isinstance(k, float) else str(k)
            interval_lines.append(f"      {disp_k}: {v}")

        interval_block = "\n".join(interval_lines) if interval_lines else "      <none>"

        return (
            f"File: {self.file_path}\n"
            f"  Computer: {comp}\n"
            f"  Rig:      {rig}\n"
            f"  Calibration.water_valve.output:\n"
            f"    slope:  {slope}\n"
            f"    offset: {offset}\n"
            f"    r2:     {r2}\n"
            f"    interval_average:\n{interval_block}\n"
        )


# ---------- Discovery & indexing ----------
def discover_configs(main_dir: Path) -> List[ConfigRecord]:
    if not main_dir.exists() or not main_dir.is_dir():
        raise FileNotFoundError(f"Directory not found or not a directory: {main_dir}")

    records: List[ConfigRecord] = []
    for comp_dir in sorted(p for p in main_dir.iterdir() if p.is_dir()):
        for cfg in sorted(comp_dir.glob("*.json")):
            try:
                with cfg.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                records.append(ConfigRecord(cfg, data))
            except json.JSONDecodeError as e:
                print(f"[WARN] Skipping invalid JSON: {cfg} ({e})", file=sys.stderr)
            except Exception as e:
                print(f"[WARN] Error reading {cfg}: {e}", file=sys.stderr)
    return records


def rig_sort_key(rig: Optional[str]) -> Tuple[int, int, str]:
    """
    Sort rigs by <number><letters>, e.g.:
      '5A' -> (0, 5, 'A')
      '12A' -> (0, 12, 'A')
      '12B' -> (0, 12, 'B')
    Malformed / missing go to the end.
    """
    if not rig or not isinstance(rig, str):
        return (1, 1_000_000_000, "")  # sentinel
    rig = rig.strip()
    m = re.fullmatch(r"(\d+)\s*([A-Za-z]+)", rig)
    if not m:
        return (1, 1_000_000_000, rig.upper())
    return (0, int(m.group(1)), m.group(2).upper())


def index_by_rig(records: List[ConfigRecord]) -> Dict[str, List[ConfigRecord]]:
    by_rig: Dict[str, List[ConfigRecord]] = {}
    for rec in records:
        rig = rec.rig_name or "(missing)"
        by_rig.setdefault(rig, []).append(rec)

    # Within each rig, sort by computer then file for stability
    for rig, lst in by_rig.items():
        lst.sort(key=lambda r: ((r.computer_name or "").lower(), r.file_path.name.lower()))
    return by_rig


# ---------- UI helpers ----------
def choose_from_list(options: List[str], prompt: str) -> Optional[int]:
    if not options:
        print("No options available.")
        return None

    while True:
        print(prompt)
        for i, opt in enumerate(options, 1):
            print(f"  {i:3d}) {opt}")
        print("    0) Back / Exit")
        choice = input("Select an option: ").strip()
        if choice == "0":
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return idx - 1
        print("Invalid selection. Please try again.\n")


# ---------- Custom logic hook ----------
def perform_custom_logic(record: ConfigRecord) -> None:
    """
    Placeholder for your domain logic. Modify as needed.
    Example: flag low r².
    """
    wv = record.get_water_valve_output()
    r2 = wv.get("r2")
    if isinstance(r2, (int, float)) and r2 < 0.95:
        print(f"[NOTE] r²={r2} below 0.98 for {record.file_path.name}")
    # Add more logic here as needed.


# ---------- App flow ----------
def interactive_app(main_dir: Optional[Path] = None) -> None:
    """
    Purely interactive flow:
      1) Ask for rig (from a sorted list; numeric-then-letter)
      2) Show all files for that rig with compact info
      3) Let user view full details and run custom logic
      4) Allow returning to rig list or exiting
    """
    main_dir = main_dir or DEFAULT_MAIN_DIR

    try:
        records = discover_configs(main_dir)
    except Exception as e:
        print(f"Error discovering configs in {main_dir}: {e}", file=sys.stderr)
        return

    if not records:
        print("No config files discovered. Nothing to show.")
        return

    rigs_index = index_by_rig(records)
    rig_names_sorted = sorted(rigs_index.keys(), key=rig_sort_key)

    while True:
        idx = choose_from_list(
            [f"Rig {r}  ({len(rigs_index[r])} file(s))" for r in rig_names_sorted],
            "\n=== Select a Rig ==="
        )
        if idx is None:
            print("Goodbye!")
            return

        rig = rig_names_sorted[idx]
        rig_records = rigs_index[rig]

        while True:
            print(f"\n=== Files for Rig {rig} ===")
            for i, rec in enumerate(rig_records, 1):
                print(f"{i:3d}) {rec.compact_line()}")
            print("    0) Back to rigs")

            choice = input("Select a file to view details: ").strip()
            if choice == "0":
                break
            if not choice.isdigit():
                print("Invalid selection. Please enter a number.")
                continue
            file_idx = int(choice)
            if not (1 <= file_idx <= len(rig_records)):
                print("Out of range. Try again.")
                continue

            selected = rig_records[file_idx - 1]
            print("\n--- File Details ---")
            print(selected.summary())

            run = input("Run custom logic on this file? [y/N]: ").strip().lower()
            if run == "y":
                perform_custom_logic(selected)
                print("[Done]\n")


# ---------- Entrypoint ----------
if __name__ == "__main__":
    # If user passes a path, use it; otherwise fall back to DEFAULT_MAIN_DIR.
    # Usage examples:
    #   python config_browser.py
    #   python config_browser.py /custom/path/to/main_dir
    cli_dir = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else None
    interactive_app(cli_dir)