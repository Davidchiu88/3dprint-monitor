#!/usr/bin/env python3
"""
Mock test - simulates 4 printers without network access
Run: python tools/test_mock.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.printer_base import PrinterStatus
from src.data_store import DataStore


def make_mock_status(name, printer_type, state, progress=0, nozzle=200, bed=60):
    return PrinterStatus(
        name=name,
        printer_type=printer_type,
        online=True,
        progress=progress,
        temp_nozzle=nozzle,
        temp_nozzle_target=210 if state == "PRINTING" else 0,
        temp_bed=bed,
        temp_bed_target=65 if state == "PRINTING" else 0,
        state=state,
        print_file="benchy.3mf" if state == "PRINTING" else None,
        remaining_time=3600 if state == "PRINTING" else None,
        materials={
            "AMS1-1": {"type": "PLA", "color": "#FF5733", "remain": 80},
            "AMS1-2": {"type": "PETG", "color": "#3498DB", "remain": 45},
        } if printer_type == "bambu_lab" else {},
    )


def run_mock_test():
    print("3D Printer Monitor - Mock Test")
    print("="*60)
    print("Simulating 4 printers with fake data\n")

    store = DataStore(data_dir="data")

    # Simulate initial status for all 4 printers
    printers = [
        make_mock_status("Bambu A1", "bambu_lab", "PRINTING", progress=42.5, nozzle=215, bed=65),
        make_mock_status("Bambu A1 Mini", "bambu_lab", "IDLE", progress=0, nozzle=25, bed=25),
        make_mock_status("Creality K1C #1", "creality_k1c", "PRINTING", progress=87.3, nozzle=200, bed=60),
        make_mock_status("Creality K1C #2", "creality_k1c", "PAUSED", progress=31.0, nozzle=195, bed=58),
    ]

    for status in printers:
        store.save_status(status)
        print(f"  Saved status: {status.name} - {status.state}")

    print("\n" + store.format_status_text())

    summary = store.get_summary()
    print(f"\nSummary: {summary['totals']['online']} online, "
          f"{summary['totals']['printing']} printing, "
          f"{summary['totals']['idle']} idle\n")

    # Simulate updates
    print("Simulating updates every 2 seconds (press Ctrl+C to stop)...")
    progress = [42.5, 0, 87.3, 31.0]
    idx = 0

    try:
        while True:
            time.sleep(2)
            idx += 1
            progress[0] = min(100, progress[0] + 1.5)
            progress[2] = min(100, progress[2] + 0.8)

            store.save_status(make_mock_status("Bambu A1", "bambu_lab", "PRINTING", progress[0], 215, 65))
            store.save_status(make_mock_status("Creality K1C #1", "creality_k1c", "PRINTING", progress[2], 200, 60))

            print(f"\r  Update #{idx}: Bambu A1={progress[0]:.1f}%  K1C#1={progress[2]:.1f}%", end="", flush=True)

    except KeyboardInterrupt:
        print(f"\n\nTest done! Check data/printer_status.json")


if __name__ == "__main__":
    run_mock_test()
