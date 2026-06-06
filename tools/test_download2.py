#!/usr/bin/env python3
"""Test downloads with fresh file listing."""
import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')
API = 'http://localhost:7000'

for name, enc in [
    ('Bambu A1 Mini', 'Bambu%20A1%20Mini'),
    ('Bambu A1 #2',   'Bambu%20A1%20%232'),
    ('K1C 紅',        'Creality%20K1C%20%E7%B4%85'),
]:
    print(f"\n=== {name} ===")
    # Fresh file list (with fixed paths)
    r = requests.get(f'{API}/api/files/{enc}', timeout=12)
    d = r.json()
    files = [f for f in (d.get('files') or []) if not f.get('_error')]
    if not files:
        err = next((f for f in (d.get('files') or []) if f.get('_error')), None)
        print(f"  No files: {err}")
        continue

    f = files[0]
    print(f"  File: {f['name']}")
    print(f"  Path: {f.get('path', '?')}")  # Should now have /cache/ prefix for Bambu

    t0 = time.time()
    r2 = requests.get(
        f'{API}/api/files/{enc}/download',
        params={'file': f.get('path', f['name'])},
        timeout=20
    )
    elapsed = time.time() - t0
    print(f"  HTTP {r2.status_code} in {elapsed:.1f}s", end='')
    if r2.status_code == 200:
        print(f" size={len(r2.content)} bytes ✅")
    elif r2.status_code == 501:
        print(f" - {r2.json().get('detail','?')} (expected)")
    else:
        print(f" ❌ - {r2.text[:100]}")
