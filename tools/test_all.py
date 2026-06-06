#!/usr/bin/env python3
"""Quick test: connect all 4 printers and print live status."""
import sys, time, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.WARNING)

from src.bambu_monitor import BambuLabMonitor
from src.creality_monitor import CrealityK1CMonitor

printers = [
    BambuLabMonitor('Bambu A1 Mini', {'ip':'192.168.0.30','device_id':'XXXXXXXXXXXXXXX','access_code':'XXXXXXXX'}),
    BambuLabMonitor('Bambu A1',      {'ip':'192.168.0.58','device_id':'XXXXXXXXXXXXXXX','access_code':'XXXXXXXX'}),
    CrealityK1CMonitor('K1C Red',    {'ip':'192.168.0.205'}),
    CrealityK1CMonitor('K1C Black',  {'ip':'192.168.0.92'}),
]

print('Connecting all printers...')
for p in printers:
    ok = p.connect()
    print(f'  {p.name}: {"CONNECTED" if ok else "FAILED"}')

print('\nWaiting 8s for data...\n')
time.sleep(8)

for p in printers:
    s = p.get_status()
    if s:
        nozzle = f'{s.temp_nozzle:.0f}C' if s.temp_nozzle is not None else '?'
        bed    = f'{s.temp_bed:.0f}C'    if s.temp_bed    is not None else '?'
        prog   = f'{s.progress:.1f}%'    if s.progress    is not None else '?'
        print(f'[{s.name}]')
        print(f'  State:   {s.state}')
        print(f'  Progress:{prog}')
        print(f'  Nozzle:  {nozzle}  Bed: {bed}')
        if s.print_file:
            safe = s.print_file[:40].encode('ascii','replace').decode()
            print(f'  File:    {safe}')
        if s.remaining_time:
            m = s.remaining_time // 60
            print(f'  ETA:     {m//60}h {m%60}m')
    else:
        print(f'[{p.name}] no data yet')
    print()

for p in printers:
    p.disconnect()
print('Done.')
