#!/usr/bin/env python3
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
try:
    data = json.load(open('data/printer_status.json', encoding='utf-8'))
    print(f'Total printers: {len(data)}')
    for name, s in data.items():
        prog = s.get('progress', 0)
        nt = s.get('temp_nozzle')
        nb = s.get('temp_bed')
        ns = '?' if nt is None else f'{float(nt):.0f}C'
        bs = '?' if nb is None else f'{float(nb):.0f}C'
        ts = s.get('timestamp', '')[:19]
        state = s.get('state', '?')
        print(f'  {name}: {state} {prog}% N={ns} B={bs} [{ts}]')
except FileNotFoundError:
    print('No data file yet')
except Exception as e:
    print(f'Error: {e}')
