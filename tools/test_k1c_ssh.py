#!/usr/bin/env python3
"""Test K1C SSH access - try common default credentials."""
import sys, socket
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'

# Check if paramiko is available
try:
    import paramiko
    print("paramiko: available")
except ImportError:
    print("paramiko: NOT installed")
    print("Install: pip install paramiko")
    sys.exit(1)

# K1C common credentials
creds = [
    ('root', 'creality'),
    ('root', 'crealityroot'),
    ('root', '1234'),
    ('root', 'password'),
    ('root', 'root'),
    ('pi', 'raspberry'),
    ('creality', 'creality'),
]

for user, passwd in creds:
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=22, username=user, password=passwd, timeout=5, banner_timeout=5)
        print(f"✅ SSH CONNECTED: {user}:{passwd}")

        # List gcode files
        stdin, stdout, stderr = ssh.exec_command('ls /usr/data/printer_data/gcodes/*.gcode 2>/dev/null | head -5')
        output = stdout.read().decode(errors='replace').strip()
        print(f"  Gcode files:\n{output[:300]}")

        # Check disk space
        _, out, _ = ssh.exec_command('df -h /usr/data')
        print(f"  Disk: {out.read().decode(errors='replace').strip()}")

        ssh.close()
        break
    except paramiko.AuthenticationException:
        print(f"  ✗ {user}:{passwd} - auth failed")
    except Exception as e:
        print(f"  ERR {user}:{passwd} - {type(e).__name__}: {str(e)[:50]}")
        break
