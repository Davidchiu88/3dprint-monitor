#!/usr/bin/env python3
"""
One-command startup: printer monitoring + API server.

Usage:
    python run.py              # monitoring + API on port 7000
    python run.py --port 8080  # custom port
    python run.py --no-api     # monitoring only
"""

import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def start_api(port: int, host: str = "0.0.0.0") -> None:
    import uvicorn
    config = uvicorn.Config(
        "src.api_server:app",
        host=host,
        port=port,
        log_level="warning",
    )
    uvicorn.Server(config).run()


def main() -> None:
    parser = argparse.ArgumentParser(description="3D Printer Monitor")
    parser.add_argument("--port",   type=int, default=7000)
    parser.add_argument("--host",   default="0.0.0.0")
    parser.add_argument("--no-api", action="store_true")
    args = parser.parse_args()

    if not args.no_api:
        t = threading.Thread(target=start_api, args=(args.port, args.host),
                             daemon=True, name="api-server")
        t.start()
        time.sleep(1.5)
        print(f"\n  API server : http://localhost:{args.port}")
        print(f"  Status URL : http://localhost:{args.port}/api/status")
        print(f"  Web page   : printers.html -> 設定 API 位址為上面的 URL\n")

    from src.main import PrinterMonitoringSystem
    PrinterMonitoringSystem().start()


if __name__ == "__main__":
    main()
