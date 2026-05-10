from __future__ import annotations

import json
from pathlib import Path

from services.checkout import ProductCatalog, build_checkout_summary
from services.inference import YoloCheckoutDetector


PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "yolov8s_best.pt"
PRODUCTS_PATH = PROJECT_ROOT / "configs" / "products.json"
PRICES_PATH = PROJECT_ROOT / "configs" / "prices.json"
DEMO_IMAGE = PROJECT_ROOT / "demo" / "images" / "val_batch0_labels.jpg"
OUTPUT_DIR = PROJECT_ROOT / "demo" / "outputs"


def main() -> None:
    products = json.loads(PRODUCTS_PATH.read_text())
    detector = YoloCheckoutDetector(MODEL_PATH, products)
    catalog = ProductCatalog.from_files(PRODUCTS_PATH, PRICES_PATH)

    result = detector.predict(DEMO_IMAGE, OUTPUT_DIR)
    summary = build_checkout_summary(result.detections, catalog)

    print("Annotated image:", result.annotated_image_path)
    print("Detected items:", summary["num_detected_items"])
    print("Unique items:", summary["num_unique_items"])
    print("Total:", summary["total"])
    print("First rows:")
    for row in summary["rows"][:5]:
        print(row)


if __name__ == "__main__":
    main()
