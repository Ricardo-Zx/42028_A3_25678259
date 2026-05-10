"""
Download the RPC dataset from Kaggle (val2019 + JSON files only, ~1.4 GB extracted).
Requires kaggle CLI credentials at ~/.kaggle/kaggle.json.

Usage:
    python scripts/download_dataset.py
"""
import subprocess
import sys
import zipfile
from pathlib import Path

DATASET  = "diyer22/retail-product-checkout-dataset"
ZIP_PATH = Path("/tmp/rpc_dataset.zip")

ROOT    = Path(__file__).resolve().parent.parent
RPC_OUT = ROOT / "data" / "raw" / "rpc"
RPC_OUT.mkdir(parents=True, exist_ok=True)

subprocess.run([sys.executable, "-m", "pip", "install", "kaggle", "-q"], check=True)

if not ZIP_PATH.exists():
    print("Downloading dataset zip (~25 GB)...")
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", DATASET, "-p", "/tmp"],
        check=True,
    )
    default_zip = Path("/tmp/retail-product-checkout-dataset.zip")
    if default_zip.exists():
        default_zip.rename(ZIP_PATH)
    print("Download complete ✓")
else:
    print("Zip already exists ✓")

print("Extracting val2019 and JSON files only...")
extracted = 0
with zipfile.ZipFile(ZIP_PATH) as zf:
    for member in zf.namelist():
        if "val2019" in member or member.endswith(".json"):
            zf.extract(member, RPC_OUT)
            extracted += 1
print(f"Extracted {extracted} files ✓")

ZIP_PATH.unlink()
print("Zip deleted ✓")

rpc_root = None
for candidate in [RPC_OUT / "retail_product_checkout", RPC_OUT]:
    if (candidate / "instances_val2019.json").exists() or (candidate / "val2019").exists():
        rpc_root = candidate
        break

pointer = ROOT / "data" / "raw" / "rpc_kagglehub_path.txt"
pointer.write_text(str(rpc_root))

print(f"rpc_root: {rpc_root}")
print(f"val2019:  {(rpc_root / 'val2019').exists()}")
print(f"JSON:     {(rpc_root / 'instances_val2019.json').exists()}")
print("Done ✓")
