#!/usr/bin/env python3
"""Directly call the list_files function to find the 500 error."""
import sys, traceback
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

# Simulate what api_server does
from src.api_server import _get_controller

name = "Bambu A1 Mini"
print(f"Getting controller for: {name}")
try:
    c = _get_controller(name)
    print(f"Controller: {type(c).__name__ if c else None}")
    if c:
        print(f"  ip={c.ip}, device_id={c.device_id[:6]}...")
        print("Calling list_files()...")
        result = c.list_files()
        print(f"Result: {result}")
except Exception as e:
    print(f"EXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
