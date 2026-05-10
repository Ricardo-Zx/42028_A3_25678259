# Scripts

All data preparation and training is handled by scripts. Notebooks are for analysis and presentation only.

## Run order

```
1. python scripts/download_dataset.py
2. python scripts/prepare_yolo_dataset.py
3. nohup python scripts/train_all.py > /tmp/train.log 2>&1 &
4. (optional) python scripts/download_test_sample.py
```

---

## `download_dataset.py`

Downloads the RPC dataset from Kaggle and extracts only the files needed for training.

- Downloads the full zip (~25 GB) to `/tmp`
- Extracts only `val2019/` images + all `.json` annotation files (~1.4 GB)
- Deletes the zip immediately after extraction
- Writes the dataset path to `data/raw/rpc_kagglehub_path.txt` (used by other scripts and notebooks)

**Requires:** `~/.kaggle/kaggle.json` with valid Kaggle credentials.

**Why not train2019?** train2019 contains 53,739 single-item product photos (1 annotation per image), unsuitable for multi-item checkout scene detection. val2019 contains 6,000 checkout scenes averaging 12.3 items per image and is used as the training source.

---

## `prepare_yolo_dataset.py`

Converts the RPC val2019 COCO-format annotations into YOLO format with an 80/10/10 stratified split.

- Reads `data/raw/rpc_kagglehub_path.txt` to locate the dataset
- Splits val2019 images 80/10/10 by difficulty level (easy/medium/hard), ensuring each subset is balanced
- Copies images and writes YOLO `.txt` label files to `data/processed/smart_checkout_yolo/`
- Generates `configs/yolo_dataset.yaml`

**Why 80/10/10 over 70/15/15?** With only 6,000 scenes and 200 classes, +600 training images (~14% gain) helps rare SKUs generalise. 600 images per eval set (200 per difficulty level) is sufficient for stable mAP estimates.

---

## `train_all.py`

Trains YOLOv5nu, YOLOv8n, and YOLOv8s sequentially for up to 300 epochs with early stopping.

- Reads `configs/yolo_dataset.yaml` for dataset paths
- Auto-resumes from `last.pt` if a previous run was interrupted
- Saves weights to `runs/train/<model_name>/weights/`
- Results CSV at `runs/train/<model_name>/results.csv` (used by notebooks for visualisation)

**Key parameters:**

| Parameter | Value | Reason |
|-----------|-------|--------|
| `epochs` | 300 | Upper bound for the extended training comparison |
| `patience` | 50 | Early stopping — halts if mAP doesn't improve for 50 epochs |
| `batch` | 8 | Reduced from 16 to prevent RAM exhaustion on SageMaker (T4, 16 GB) |
| `imgsz` | 640 | Standard YOLO input resolution |

**Why terminal instead of notebook?** Running `model.train()` inside a Jupyter kernel on SageMaker caused kernel crashes at ~epoch 28 due to memory accumulation from MLflow logs and validation results. The terminal process has no kernel memory limit.

---

## `download_test_sample.py`

Downloads a stratified sample of test2019 images for the difficulty-level analysis in `03_model_comparison.ipynb`.

```bash
python scripts/download_test_sample.py --n 300 --out demo/test_sample
```

- `--n` total images (split evenly across easy/medium/hard)
- `--out` output directory
- `--annotations` path to `instances_test2019.json` (default: `configs/instances_test2019.json`)
