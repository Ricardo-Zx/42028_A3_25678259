"""
Smart Checkout — one-click launcher.
Run from the project root:  python start.py
"""
import os
import platform
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

WEBAPP_DIR = Path(__file__).resolve().parent / "webapp"
PORT = 8000


def _is_usable_lan_ip(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        nums = [int(part) for part in parts]
    except ValueError:
        return False
    if nums[0] == 127 or nums[0] == 0:
        return False
    if nums[0] == 169 and nums[1] == 254:
        return False
    return (
        nums[0] == 10
        or (nums[0] == 172 and 16 <= nums[1] <= 31)
        or (nums[0] == 192 and nums[1] == 168)
    )


def _ip_priority(ip: str) -> int:
    if ip.startswith("192.168."):
        return 0
    if ip.startswith("10."):
        return 1
    if ip.startswith("172."):
        return 2
    return 3


def _mac_interface_ip(name: str) -> str | None:
    if platform.system() != "Darwin":
        return None
    try:
        result = subprocess.run(
            ["ipconfig", "getifaddr", name],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None
    ip = result.stdout.strip()
    return ip if _is_usable_lan_ip(ip) else None


def get_lan_ip() -> str:
    candidates: list[str] = []

    for interface in ("en0", "en1"):
        ip = _mac_interface_ip(interface)
        if ip:
            candidates.append(ip)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if _is_usable_lan_ip(ip):
            candidates.append(ip)
    except Exception:
        pass

    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if _is_usable_lan_ip(ip):
                candidates.append(ip)
    except Exception:
        pass

    unique = sorted(set(candidates), key=_ip_priority)
    return unique[0] if unique else "127.0.0.1"


def get_phone_url() -> str:
    override = os.environ.get("SMART_CHECKOUT_PHONE_URL") or os.environ.get("SMART_CHECKOUT_PHONE_HOST")
    if override:
        override = override.strip().rstrip("/")
        if override.startswith("http://") or override.startswith("https://"):
            return override
        if ":" in override:
            return f"http://{override}"
        return f"http://{override}:{PORT}"
    return f"http://{get_lan_ip()}:{PORT}"


def main():
    local_url = f"http://127.0.0.1:{PORT}"
    phone_url = get_phone_url()
    os.environ["SMART_CHECKOUT_PHONE_URL"] = phone_url
    manage_py = WEBAPP_DIR / "manage.py"

    print()
    print("=" * 52)
    print("   Smart Checkout — starting server")
    print("=" * 52)
    print(f"   Local URL : {local_url}")
    print(f"   Phone URL : {phone_url}")
    print()
    print("   📱 To use on your phone:")
    print(f"      1. Connect your phone to the SAME Wi-Fi network")
    print(f"      2. Open  {phone_url}  on your phone")
    print(f"         (or scan the QR code shown on the page)")
    print("      3. If this Phone URL does not work, use your computer's Wi-Fi IP instead")
    print()
    print("   Press Ctrl+C to stop the server")
    print("=" * 52)
    print()

    print("   Preparing database tables...")
    migrate = subprocess.run(
        [sys.executable, str(manage_py), "migrate", "--noinput"],
        cwd=str(WEBAPP_DIR),
    )
    if migrate.returncode != 0:
        print()
        print("   Database migration failed. Please check the error above.")
        sys.exit(migrate.returncode)

    # open browser after a short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(local_url)

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # start Django
    subprocess.run(
        [sys.executable, str(manage_py), "runserver", f"0.0.0.0:{PORT}"],
        cwd=str(WEBAPP_DIR),
    )


if __name__ == "__main__":
    main()
