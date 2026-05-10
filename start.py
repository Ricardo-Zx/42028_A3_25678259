"""
Smart Checkout — one-click launcher.
Run from the project root:  python start.py
"""
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

WEBAPP_DIR = Path(__file__).resolve().parent / "webapp"
PORT = 8000


def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    ip = get_lan_ip()
    url = f"http://{ip}:{PORT}"

    print()
    print("=" * 52)
    print("   Smart Checkout — starting server")
    print("=" * 52)
    print(f"   Local URL : http://127.0.0.1:{PORT}")
    print(f"   Phone URL : {url}")
    print()
    print("   📱 To use on your phone:")
    print(f"      1. Connect your phone to the SAME Wi-Fi network")
    print(f"      2. Open  {url}  on your phone")
    print(f"         (or scan the QR code shown on the page)")
    print()
    print("   Press Ctrl+C to stop the server")
    print("=" * 52)
    print()

    # open browser after a short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # start Django
    manage_py = WEBAPP_DIR / "manage.py"
    subprocess.run(
        [sys.executable, str(manage_py), "runserver", f"0.0.0.0:{PORT}"],
        cwd=str(WEBAPP_DIR),
    )


if __name__ == "__main__":
    main()
