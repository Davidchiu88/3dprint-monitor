#!/usr/bin/env python3
import requests, re, sys
sys.stdout.reconfigure(encoding='utf-8')

for ip, name in [('192.168.0.205', 'K1C 紅'), ('192.168.0.92', 'K1C 黑')]:
    try:
        r = requests.get(f'http://{ip}/downloads/original/', timeout=5)
        # gcode files with timestamps
        items = re.findall(
            r'href="([^"./][^"]*\.(?:gcode|3mf|bgcode))"[^<]*</a>\s*</td>\s*<td>(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
            r.text
        )
        if not items:
            names = re.findall(r'href="([^"./][^"]*\.gcode)"', r.text)
            dates = re.findall(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', r.text)
            items = list(zip(names, dates)) if len(names) == len(dates) else [(n, '?') for n in names]

        recent = sorted(items, key=lambda x: x[1], reverse=True)[:8]
        print(f"\n{name} - 最近 8 個 gcode 檔案：")
        for n, ts in recent:
            print(f"  {ts}  {n}")
        print(f"  Total in original/: {len(items)} files")
    except Exception as e:
        print(f"\n{name}: {e}")
