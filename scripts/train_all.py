"""
Train YOLOv5nu, YOLOv8n, YOLOv8s for 300 epochs on the RPC checkout dataset.
Auto-resumes from last checkpoint if interrupted.

Usage:
    python scripts/train_all.py
"""
import os
from pathlib import Path

import torch
from ultralytics import YOLO

ROOT    = Path(__file__).resolve().parent.parent
YAML    = ROOT / "configs" / "yolo_dataset.yaml"
RUNS    = ROOT / "runs" / "train"
EPOCHS   = 300
PATIENCE = 50
IMGSZ    = 640
BATCH    = 8
WORKERS  = 4
device  = "0" if torch.cuda.is_available() else "cpu"

os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".ultralytics"))

MODELS = [
    {"weights": "yolov5nu.pt", "name": "yolov5nu_300ep"},
    {"weights": "yolov8n.pt",  "name": "yolov8n_300ep"},
    {"weights": "yolov8s.pt",  "name": "yolov8s_300ep"},
]

print(f"Device: {device}  Batch: {BATCH}  Epochs: {EPOCHS}")
print(f"YAML: {YAML}\n")

for cfg in MODELS:
    run_dir   = RUNS / cfg["name"]
    last_ckpt = run_dir / "weights" / "last.pt"
    resuming  = last_ckpt.exists()
    print(f"{'Resuming' if resuming else 'Starting'}: {cfg['name']}")
    model = YOLO(str(last_ckpt) if resuming else cfg["weights"])
    model.train(
        data=str(YAML),
        epochs=EPOCHS,
        patience=PATIENCE,
        imgsz=IMGSZ,
        batch=BATCH,
        workers=WORKERS,
        device=device,
        project=str(RUNS),
        name=cfg["name"],
        exist_ok=True,
        resume=resuming,
    )
    print(f"{cfg['name']} done ✓\n")
