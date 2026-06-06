#!/usr/bin/env python3
import paramiko, sys, time
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ip, port=22, username='root', password='creality_2023',
            timeout=15, banner_timeout=15, look_for_keys=False, allow_agent=False,
            disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
print("SSH connected!")

fname = '/usr/data/printer_data/gcodes/3DBenchy.gcode'
t0 = time.time()
_, stdout, stderr = ssh.exec_command(f'cat "{fname}"')
data = stdout.read()
err = stderr.read().decode(errors='replace').strip()
elapsed = time.time() - t0

print(f"Size: {len(data)} bytes in {elapsed:.1f}s")
print(f"Error: {err[:80] if err else 'none'}")
if data:
    print(f"First bytes: {data[:30]!r}")
ssh.close()
print("Done!")
