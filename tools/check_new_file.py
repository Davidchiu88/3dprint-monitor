#!/usr/bin/env python3
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

r = requests.get('http://localhost:7000/api/files/Creality%20K1C%20%E9%BB%91', timeout=10)
d = r.json()
files = [f for f in (d.get('files') or []) if not f.get('_error')]
print(f'K1C 黑 via API: {len(files)} files')

# Show newest 3 by name
for f in files[:3]:
    print(f'  {f["name"]}  path={f["path"]}')

# Check for the specific new file
new = next((f for f in files if '0602' in f.get('name', '')), None)
if new:
    print(f'\nNew file VISIBLE: {new["name"]}')
    print(f'Path: {new["path"]}')
else:
    print('\nNew file not yet visible (thumbnail generating...)')
