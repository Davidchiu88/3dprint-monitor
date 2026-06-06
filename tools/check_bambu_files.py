#!/usr/bin/env python3
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

printers = [
    ('Bambu A1 Mini', 'Bambu%20A1%20Mini'),
    ('Bambu A1',      'Bambu%20A1'),
    ('Bambu A1 #2',   'Bambu%20A1%20%232'),
    ('K1C 紅',        'Creality%20K1C%20%E7%B4%85'),
]

for name, enc in printers:
    r = requests.get(f'http://localhost:7000/api/files/{enc}', timeout=12)
    d = r.json()
    files = [f for f in (d.get('files') or []) if not f.get('_error')]
    err = next((f for f in (d.get('files') or []) if f.get('_error')), None)
    if err:
        print(f'{name}: ❌ {err["_error"]}')
    else:
        print(f'{name}: ✅ {len(files)} files')
        for f in files[:3]:
            print(f'   - {f["name"]}')
