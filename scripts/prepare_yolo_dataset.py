"""
Convert RPC val2019 (COCO format) to YOLO format with 80/10/10 stratified split.

Usage:
    python scripts/prepare_yolo_dataset.py
    python scripts/prepare_yolo_dataset.py --rpc_root /path/to/rpc --out data/processed/smart_checkout_yolo
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path


def load_ann(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def find_rpc_root(project_root: Path) -> Path:
    pointer = project_root / "data" / "raw" / "rpc_kagglehub_path.txt"
    if pointer.exists():
        return Path(pointer.read_text().strip())
    for candidate in [
        project_root / "data" / "raw" / "rpc" / "retail_product_checkout",
        project_root / "data" / "raw" / "rpc",
    ]:
        if (candidate / "instances_val2019.json").exists():
            return candidate
    raise FileNotFoundError("Cannot locate rpc_root. Run notebook 01 first.")


def stratified_split(images: list[dict], seed: int = 42) -> tuple[list, list, list]:
    by_level: dict[str, list] = defaultdict(list)
    for img in images:
        by_level[img.get("level", "unknown")].append(img)

    rng = random.Random(seed)
    train, val, test = [], [], []
    for level_imgs in by_level.values():
        rng.shuffle(level_imgs)
        n = len(level_imgs)
        n_val = max(1, round(n * 0.10))
        n_test = max(1, round(n * 0.10))
        test.extend(level_imgs[:n_test])
        val.extend(level_imgs[n_test: n_test + n_val])
        train.extend(level_imgs[n_test + n_val:])
    return train, val, test


def coco_to_yolo(bbox: list[float], img_w: int, img_h: int) -> tuple[float, float, float, float]:
    x, y, w, h = bbox
    cx = (x + w / 2) / img_w
    cy = (y + h / 2) / img_h
    return cx, cy, w / img_w, h / img_h


def write_split(
    split_name: str,
    images: list[dict],
    ann_by_img: dict[int, list],
    cat_to_idx: dict[int, int],
    img_src_dir: Path,
    out_root: Path,
) -> None:
    img_dir = out_root / split_name / "images"
    lbl_dir = out_root / split_name / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    missing = 0
    for img_meta in images:
        src = img_src_dir / img_meta["file_name"]
        if not src.exists():
            missing += 1
            continue

        dst_img = img_dir / img_meta["file_name"]
        if not dst_img.exists():
            shutil.copy2(src, dst_img)

        w, h = img_meta["width"], img_meta["height"]
        lines = []
        for ann in ann_by_img.get(img_meta["id"], []):
            cls_idx = cat_to_idx[ann["category_id"]]
            cx, cy, bw, bh = coco_to_yolo(ann["bbox"], w, h)
            lines.append(f"{cls_idx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        lbl_file = lbl_dir / (src.stem + ".txt")
        lbl_file.write_text("\n".join(lines))

    if missing:
        print(f"  [{split_name}] {missing} images not found in source dir (skipped)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpc_root", default=None, help="Path to rpc dataset root (auto-detected if omitted)")
    parser.add_argument("--out", default="data/processed/smart_checkout_yolo")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    rpc_root = Path(args.rpc_root) if args.rpc_root else find_rpc_root(project_root)
    print(f"RPC root:  {rpc_root}")

    val_json = next(
        (p for p in [rpc_root / "instances_val2019.json",
                     rpc_root / "retail_product_checkout" / "instances_val2019.json"]
         if p.exists()),
        None,
    )
    if val_json is None:
        raise FileNotFoundError(f"instances_val2019.json not found under {rpc_root}")

    data = load_ann(val_json)
    images = data["images"]
    annotations = data["annotations"]
    categories = data["categories"]

    cat_to_idx = {c["id"]: i for i, c in enumerate(categories)}
    class_names = [c["name"] for c in categories]

    ann_by_img: dict[int, list] = defaultdict(list)
    for ann in annotations:
        ann_by_img[ann["image_id"]].append(ann)

    train_imgs, val_imgs, test_imgs = stratified_split(images, seed=args.seed)
    print(f"Split: train={len(train_imgs)}  val={len(val_imgs)}  test={len(test_imgs)}")

    val2019_dir = rpc_root / "val2019"
    if not val2019_dir.exists():
        val2019_dir = rpc_root / "retail_product_checkout" / "val2019"
    if not val2019_dir.exists():
        raise FileNotFoundError(f"val2019 images not found under {rpc_root}")

    out_root = project_root / args.out
    print(f"Output:    {out_root}")

    for split_name, split_imgs in [("train", train_imgs), ("val", val_imgs), ("test", test_imgs)]:
        print(f"Writing {split_name}...")
        write_split(split_name, split_imgs, ann_by_img, cat_to_idx, val2019_dir, out_root)

    yaml_path = project_root / "configs" / "yolo_dataset.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        f"path: {out_root.resolve()}\n"
        f"train: train/images\n"
        f"val:   val/images\n"
        f"test:  test/images\n\n"
        f"nc: {len(class_names)}\n"
        f"names: {class_names}\n"
    )
    print(f"YAML written: {yaml_path}")
    print("Done ✓")


if __name__ == "__main__":
    main()
