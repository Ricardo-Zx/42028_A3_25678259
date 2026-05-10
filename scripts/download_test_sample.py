"""
Download a stratified sample of test2019 images from Kaggle without
pulling the full 25 GB dataset.

Usage:
    python scripts/download_test_sample.py --n 200 --out demo/test_sample
    python scripts/download_test_sample.py --n 600 --out data/test_sample  # 200 per level
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


DATASET_SLUG = "diyer22/retail-product-checkout-dataset"
KAGGLE_PREFIX = "retail_product_checkout/test2019"


def load_images(json_path: Path) -> list[dict]:
    with json_path.open(encoding="utf-8") as f:
        return json.load(f)["images"]


def stratified_sample(images: list[dict], n: int, seed: int) -> list[dict]:
    by_level: dict[str, list[dict]] = defaultdict(list)
    for img in images:
        by_level[img.get("level", "unknown")].append(img)

    rng = random.Random(seed)
    levels = sorted(by_level)
    per_level = n // len(levels)
    remainder = n % len(levels)

    sampled: list[dict] = []
    for i, level in enumerate(levels):
        pool = by_level[level]
        take = per_level + (1 if i < remainder else 0)
        sampled.extend(rng.sample(pool, min(take, len(pool))))

    rng.shuffle(sampled)
    return sampled


def download_image(filename: str, out_dir: Path) -> bool:
    dest = out_dir / filename
    if dest.exists():
        return True

    kaggle_path = f"{KAGGLE_PREFIX}/{filename}"
    result = subprocess.run(
        ["kaggle", "datasets", "download",
         "-d", DATASET_SLUG,
         "-f", kaggle_path,
         "-p", str(out_dir),
         "--unzip"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", default="configs/instances_test2019.json",
                        help="Path to instances_test2019.json (already downloaded)")
    parser.add_argument("--n", type=int, default=200,
                        help="Total images to download (split evenly across easy/medium/hard)")
    parser.add_argument("--out", default="demo/test_sample",
                        help="Output directory for downloaded images")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    annotations_path = Path(args.annotations)
    if not annotations_path.exists():
        # also try Downloads
        fallback = Path.home() / "Downloads" / "instances_test2019.json"
        if fallback.exists():
            annotations_path = fallback
        else:
            sys.exit(f"Cannot find {annotations_path}. Pass --annotations <path>.")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading image list from {annotations_path} ...")
    images = load_images(annotations_path)
    sample = stratified_sample(images, args.n, args.seed)

    print(f"Downloading {len(sample)} images → {out_dir}")
    ok = fail = 0
    for i, img in enumerate(sample, 1):
        filename = img["file_name"]
        success = download_image(filename, out_dir)
        if success:
            ok += 1
        else:
            fail += 1
        if i % 20 == 0 or i == len(sample):
            print(f"  {i}/{len(sample)}  ok={ok}  fail={fail}")

    print(f"\nDone. {ok} downloaded, {fail} failed → {out_dir}")


if __name__ == "__main__":
    main()
