#!/usr/bin/env python3
"""Clear K1C completed job and test upload."""
import asyncio, json, websockets, time, requests, sys
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'

async def send_stop():
    async with websockets.connect(f'ws://{ip}:9999', ping_interval=None, open_timeout=5) as ws:
        await ws.send(json.dumps({'method': 'set', 'params': {'stop': 1}}))
        print("Stop command sent")
        await asyncio.sleep(1)

async def get_state():
    async with websockets.connect(f'ws://{ip}:9999', ping_interval=None, open_timeout=5) as ws:
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        d = json.loads(raw)
        state = d.get('state', '?')
        state_name = {0: 'IDLE', 1: 'PRINTING', 2: 'PAUSED', 4: 'IDLE(finished)'}.get(state, str(state))
        print(f"State: {state} = {state_name}")
        return state

print(f"K1C 紅 ({ip}) — 清除已完成工作")
print("Before:")
asyncio.run(get_state())

print("\nSending stop...")
asyncio.run(send_stop())
time.sleep(3)

print("After stop:")
new_state = asyncio.run(get_state())

if new_state == 0:
    print("\n現在是 IDLE，測試上傳...")
    test_gcode = b"; Test\nG28\n"
    try:
        r = requests.post(f'http://{ip}/upload/test_probe.gcode',
                          files={'file': ('test_probe.gcode', test_gcode)}, timeout=15)
        d = r.json()
        if d.get('code') == 200:
            print("上傳成功！")
            # Cleanup
            asyncio.run((lambda: None)())  # just trigger loop
            async def cleanup():
                async with websockets.connect(f'ws://{ip}:9999', ping_interval=None, open_timeout=5) as ws:
                    await ws.send(json.dumps({'method':'set','params':{'opGcodeFile':'deleteprt:/usr/data/printer_data/gcodes/test_probe.gcode'}}))
                    await asyncio.sleep(1)
            asyncio.run(cleanup())
            print("測試檔案已清除")
        else:
            print(f"上傳失敗 code={d.get('code')}")
    except Exception as e:
        print(f"上傳錯誤: {e}")
else:
    print(f"\n狀態不是 IDLE ({new_state})，可能需要等一下或手動確認列印完成")
