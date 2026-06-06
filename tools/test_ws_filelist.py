#!/usr/bin/env python3
"""Test K1C file list via WebSocket (shows all files including no-thumbnail)."""
import sys, requests
sys.stdout.reconfigure(encoding='utf-8')

for name, encoded in [('Creality K1C 紅', 'Creality%20K1C%20%E7%B4%85'),
                       ('Creality K1C 黑', 'Creality%20K1C%20%E9%BB%91')]:
    print(f"\n=== {name} ===")
    r = requests.get(f'http://localhost:7000/api/files/{encoded}', timeout=15)
    d = r.json()
    files = [f for f in (d.get('files') or []) if not f.get('_error')]
    print(f"Total: {len(files)} files")
    for f in files[:5]:
        has_t = '📷' if f.get('thumbnail') else '  '
        print(f"  {has_t} {f['name']}")
    if len(files) > 5:
        print(f"  ... ({len(files)-5} more)")
