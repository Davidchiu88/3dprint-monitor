#!/usr/bin/env python3
import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')

data = b'; K1C upload test\nG28\nG1 X100 Y100 Z5 F3000\n'

for name, enc in [('K1C 紅', 'Creality%20K1C%20%E7%B4%85'),
                   ('K1C 黑', 'Creality%20K1C%20%E9%BB%91')]:
    print(f"\n=== {name} ===")
    t0 = time.time()
    try:
        r = requests.post(
            f'http://localhost:7000/api/files/{enc}',
            files={'file': (f'test_upload_{name}.gcode', data)},
            timeout=25
        )
        d = r.json()
        elapsed = time.time() - t0
        print(f"Time: {elapsed:.1f}s")
        print(f"ok={d.get('ok')}  file={d.get('filename')}  size={d.get('size')}")
        if not d.get('ok'):
            print(f"Error: {d}")
    except Exception as e:
        print(f"FAILED: {e}")
