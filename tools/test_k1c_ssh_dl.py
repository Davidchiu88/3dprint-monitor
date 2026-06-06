#!/usr/bin/env python3
import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')

API = 'http://localhost:7000'

for name, enc in [('K1C 紅', 'Creality%20K1C%20%E7%B4%85'),
                   ('K1C 黑', 'Creality%20K1C%20%E9%BB%91')]:
    print(f"\n=== {name} ===")
    r = requests.get(f'{API}/api/files/{enc}', timeout=10)
    files = [f for f in (r.json().get('files') or []) if not f.get('_error')]
    if not files:
        print("  No files")
        continue
    f = files[0]
    print(f"  File: {f['name']}")
    print(f"  Path: {f['path']}")
    t0 = time.time()
    r2 = requests.get(f'{API}/api/files/{enc}/download',
                      params={'file': f['path']}, timeout=30)
    elapsed = time.time() - t0
    if r2.status_code == 200:
        print(f"  ✅ HTTP 200 in {elapsed:.1f}s - {len(r2.content):,} bytes")
        # Save to temp to verify
        fname = f['name']
        with open(f'data/test_dl_{fname}', 'wb') as fp:
            fp.write(r2.content)
        print(f"  Saved to data/test_dl_{fname}")
    elif r2.status_code == 501:
        print(f"  ❌ 501: {r2.json().get('detail','?')}")
    else:
        print(f"  ❌ HTTP {r2.status_code}: {r2.text[:100]}")
