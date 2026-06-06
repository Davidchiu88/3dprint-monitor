#!/usr/bin/env python3
"""Test download for all printers."""
import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')

API = 'http://localhost:7000'

# Get one file from each printer and try to download it
tests = [
    ('K1C 紅', 'Creality%20K1C%20%E7%B4%85'),
    ('K1C 黑', 'Creality%20K1C%20%E9%BB%91'),
    ('Bambu A1 Mini', 'Bambu%20A1%20Mini'),
    ('Bambu A1 #2', 'Bambu%20A1%20%232'),
]

for name, enc in tests:
    print(f"\n=== {name} ===")
    # Get file list
    r = requests.get(f'{API}/api/files/{enc}', timeout=12)
    d = r.json()
    files = [f for f in (d.get('files') or []) if not f.get('_error')]
    if not files:
        print(f"  No files (err: {[f for f in (d.get('files') or []) if f.get('_error')][:1]})")
        continue

    # Try to download first file
    f = files[0]
    print(f"  File: {f['name']}")
    print(f"  Path: {f.get('path','?')}")

    try:
        t0 = time.time()
        r2 = requests.get(
            f'{API}/api/files/{enc}/download',
            params={'file': f.get('path', f['name'])},
            timeout=15,
            stream=True
        )
        size = 0
        for chunk in r2.iter_content(8192):
            size += len(chunk)
            if size > 10000: break  # Just test first 10KB
        print(f"  Download: HTTP {r2.status_code} ~{size}B in {time.time()-t0:.1f}s {'✅' if r2.status_code==200 else '❌'}")
        if r2.status_code != 200:
            print(f"  Error: {r2.text[:100]}")
    except Exception as e:
        print(f"  Download FAIL: {type(e).__name__}: {str(e)[:80]}")
