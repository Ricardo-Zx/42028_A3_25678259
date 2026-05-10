from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProductCatalog:
    products: dict[str, dict[str, Any]]
    prices: dict[str, float]

    @classmethod
    def from_files(cls, products_path: str | Path, prices_path: str | Path) -> "ProductCatalog":
        products = json.loads(Path(products_path).read_text())
        prices_raw = json.loads(Path(prices_path).read_text())
        prices = {sku_name: float(price) for sku_name, price in prices_raw.items()}
        return cls(products=products, prices=prices)

    def lookup_product(self, sku_name: str) -> dict[str, Any]:
        return self.products.get(
            sku_name,
            {
                "sku_name": sku_name,
                "display_name": "Unknown item",
                "sku_class": "unknown",
                "category_name": "Unknown",
                "barcode": None,
            },
        )

    def lookup_price(self, sku_name: str) -> float:
        return float(self.prices.get(sku_name, 0.0))


def make_display_name(product: dict[str, Any]) -> str:
    sku_name = product.get("sku_name", "unknown")
    display_name = product.get("display_name", "")
    if sku_name.startswith("unknown_"):
        class_id = sku_name.split("_", 1)[-1]
        return f"Unknown Item (Class {class_id})"
    if display_name:
        return display_name
    sku_parts = sku_name.split("_", 1)
    if len(sku_parts) == 2 and sku_parts[0].isdigit():
        return f"{sku_parts[1].replace('_', ' ').title()} {sku_parts[0]}"
    return sku_name.replace("_", " ").title()


def aggregate_skus(detections: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for detection in detections:
        sku_name = detection["sku_name"]
        counter[sku_name] += 1
    return counter


def build_checkout_summary(
    detections: list[dict[str, Any]],
    catalog: ProductCatalog,
) -> dict[str, Any]:
    counts = aggregate_skus(detections)

    conf_by_sku: dict[str, list[float]] = {}
    for d in detections:
        conf_by_sku.setdefault(d["sku_name"], []).append(d["confidence"])

    rows: list[dict[str, Any]] = []
    total = 0.0

    for sku_name, quantity in counts.items():
        product = catalog.lookup_product(sku_name)
        unit_price = catalog.lookup_price(sku_name)
        subtotal = unit_price * quantity
        confs = conf_by_sku.get(sku_name, [])
        rows.append(
            {
                "sku_name": sku_name,
                "display_name": make_display_name(product),
                "display_name_cn": product.get("display_name", sku_name),
                "sku_class": product.get("sku_class", "unknown"),
                "category_name": product.get("category_name", "Unknown"),
                "barcode": product.get("barcode"),
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "avg_conf": round(sum(confs) / len(confs) * 100, 1) if confs else 0.0,
            }
        )
        total += subtotal

    rows.sort(key=lambda row: (-row["quantity"], row["sku_name"]))

    return {
        "num_detected_items": sum(counts.values()),
        "num_unique_items": len(rows),
        "rows": rows,
        "total": total,
    }
