#!/usr/bin/env python3
"""Try more K1C SSH credentials + check banner."""
import sys, socket, paramiko
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'

# Check what port 22 actually sends (might not be SSH)
print("=== Port 22 banner ===")
try:
    s = socket.socket(); s.settimeout(5)
    s.connect((ip, 22))
    banner = s.recv(256)
    print(f"  Banner: {banner.decode(errors='replace')[:100]!r}")
    s.close()
except Exception as e:
    print(f"  Error: {e}")

# Extended password list based on community research
# K1/K1C common passwords
extra_creds = [
    ('root', 'creality_2023'),
    ('root', 'creality2023'),
    ('root', 'K1C'),
    ('root', 'k1c'),
    ('root', ''),           # empty password
    ('root', 'klipper'),
    ('root', 'mainsail'),
    ('root', 'fluidd'),
    ('root', 'cr-10'),
    ('root', 'creality1234'),
    ('root', '3dprint'),
    ('root', 'printer'),
    ('admin', 'admin'),
    ('root', 'creality_k1'),
    ('root', 'bblp'),
]

print("\n=== Extended credential test ===")
for user, passwd in extra_creds:
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=22, username=user, password=passwd,
                    timeout=5, banner_timeout=8,
                    look_for_keys=False, allow_agent=False)
        print(f"✅ CONNECTED: {user}:{passwd!r}")
        _, out, _ = ssh.exec_command('whoami && ls /usr/data/printer_data/gcodes/ | head -3')
        print(f"  {out.read().decode(errors='replace').strip()[:200]}")
        ssh.close()
        break
    except paramiko.AuthenticationException:
        print(f"  ✗ {user}:{passwd!r}")
    except paramiko.SSHException as e:
        print(f"  SSH ERR {user}:{passwd!r}: {str(e)[:50]}")
        break
    except Exception as e:
        print(f"  ERR {user}:{passwd!r}: {type(e).__name__}")
        break
