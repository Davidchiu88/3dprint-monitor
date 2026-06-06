#!/usr/bin/env python3
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')
names = ['Bambu A1 Mini', 'Bambu A1', 'Creality K1C 紅']
for name in names:
    try:
        r = requests.get(f'http://localhost:7000/api/camera/{requests.utils.quote(name)}/snapshot', timeout=25)
        ct = r.headers.get('content-type','')
        print(f'{name}: {r.status_code} {len(r.content)} bytes {ct}')
        if r.status_code != 200:
            print(f'  Error: {r.text[:150]}')
    except Exception as e:
        print(f'{name}: EXCEPTION {e}')
