#!/usr/bin/env python3
"""Test sync_all (download all to disk)."""
import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')

API = 'http://localhost:7000'

# Test with K1C 紅 (has SSH)
name = 'Creality K1C 紅'
enc  = 'Creality%20K1C%20%E7%B4%85'
save_dir = r'D:\印表機檔案_test'  # use test dir

print(f"Starting sync_all for {name}...")
r = requests.post(f'{API}/api/files/{enc}/sync_all', params={'base_dir': save_dir}, timeout=10)
d = r.json()
print(f"Job started: ok={d.get('ok')}, job_id={d.get('job_id')}, save_dir={d.get('save_dir')}")

if not d.get('ok'):
    print(f"Error: {d}")
    sys.exit(1)

job_id = d['job_id']

# Poll progress for 30 seconds
for i in range(20):
    time.sleep(3)
    r2 = requests.get(f'{API}/api/files/{enc}/sync_all/{job_id}', timeout=5)
    s = r2.json()
    print(f"  [{i+1}] {s.get('pct',0)}% | {s.get('done',0)}/{s.get('total',0)} | "
          f"current: {s.get('current','')[:30]} | status: {s.get('status','?')}")
    if s.get('status') in ('done', 'error'):
        print(f"\nFinal: status={s['status']}, done={s['done']}, skipped={s.get('skipped',0)}")
        if s.get('errors'):
            print(f"Errors: {s['errors'][:3]}")
        break

# Check files were saved
import os
if os.path.exists(save_dir):
    files = list(os.scandir(save_dir))
    if files:
        sub = list(os.scandir(files[0].path))[:3]
        print(f"\nSaved to {files[0].path}: {len(list(os.scandir(files[0].path)))} files")
        for f in sub:
            print(f"  {f.name} ({f.stat().st_size//1024} KB)")
