from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image
from ultralytics import YOLO


@dataclass
class DetectionResult:
    detections: list[dict[str, Any]]
    annotated_image_path: str


class YoloCheckoutDetector:
    def __init__(self, model_path: str | Path, products: dict[str, dict[str, Any]]) -> None:
        self.model_path = Path(model_path)
        self.model = YOLO(str(self.model_path))
        self.id_to_sku = self._build_id_to_sku(products)

    @staticmethod
    def _build_id_to_sku(products: dict[str, dict[str, Any]]) -> dict[int, str]:
        mapping: dict[int, str] = {}
        for sku_name, metadata in products.items():
            yolo_id = int(metadata["yolo_id"])
            mapping[yolo_id] = sku_name
        return mapping

    def predict(
        self,
        image_path: str | Path,
        output_dir: str | Path,
        conf: float = 0.25,
    ) -> DetectionResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = self.model.predict(
            source=str(image_path),
            conf=conf,
            verbose=False,
        )
        result = results[0]

        plotted = result.plot()
        annotated = Image.fromarray(plotted[..., ::-1])
        annotated_image_path = output_dir / Path(image_path).name
        annotated.save(annotated_image_path)

        detections: list[dict[str, Any]] = []
        if result.boxes is not None:
            xyxy = result.boxes.xyxy.tolist()
            confs = result.boxes.conf.tolist()
            clss = result.boxes.cls.tolist()
            for bbox, score, class_id in zip(xyxy, confs, clss):
                yolo_id = int(class_id)
                sku_name = self.id_to_sku.get(yolo_id, f"unknown_{yolo_id}")
                detections.append(
                    {
                        "sku_name": sku_name,
                        "yolo_id": yolo_id,
                        "confidence": float(score),
                        "bbox_xyxy": [float(value) for value in bbox],
                    }
                )
        return DetectionResult(
            detections=detections,
            annotated_image_path=str(annotated_image_path),
        )
