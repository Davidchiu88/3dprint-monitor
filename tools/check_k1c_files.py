#!/usr/bin/env python3
import requests, re, sys
sys.stdout.reconfigure(encoding='utf-8')

# Check K1C directory listing with timestamps
for ip, name in [('192.168.0.205','K1C 紅'), ('192.168.0.92','K1C 黑')]:
    print(f"\n=== {name} ({ip}) - 最近 5 個檔案 ===")
    try:
        r = requests.get(f'http://{ip}/downloads/humbnail/', timeout=5)
        # Parse name + date from HTML table
        items = re.findall(
            r'href="([^"./][^"]*\.png)"[^<]*</a>\s*</td>\s*<td>(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
            r.text
        )
        if not items:
            # Try simpler pattern
            names = re.findall(r'href="([^"./][^"]*\.png)"', r.text)
            dates = re.findall(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', r.text)
            items = list(zip(names, dates)) if len(names)==len(dates) else [(n,'?') for n in names]

        recent = sorted(items, key=lambda x: x[1], reverse=True)[:5]
        for fname, ts in recent:
            print(f"  {ts}  {fname[:-4]}.gcode")
        print(f"  Total: {len(items)} files")
    except Exception as e:
        print(f"  Error: {e}")
