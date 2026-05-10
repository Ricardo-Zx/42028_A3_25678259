# A3 Smart Checkout Webapp

This project is the deployment-oriented application layer for Assignment 3.

It is intentionally separated from the original `retail-checkout-detection` prototype, which remains the experiment and notebook repository.

## Purpose

This repository is for:

- Django backend and frontend development
- YOLOv8n inference integration
- checkout item aggregation
- price lookup and total bill calculation

This repository is **not** for:

- model training
- evaluation experiments
- notebook reporting

## Current Assets

- `models/yolov8n_best.pt`: final demonstration detector
- `configs/products.json`: SKU metadata
- `configs/prices.json`: price table for checkout calculation
- `demo/images/`: demo images exported from evaluation outputs
- `notebooks/`: final reporting notebooks copied back from AWS
- `figures/`: exported notebook figures
- `runs/train/`: extended-training run outputs used by the notebooks

## Project Structure

- `webapp/`: Django project and apps
- `models/`: model weights
- `configs/`: SKU and pricing metadata
- `demo/`: demo inputs for local testing
- `services/`: reusable inference and checkout logic
- `scripts/`: AWS-side dataset and training scripts retained for reproducibility
- `notebooks/`: report notebooks (`01`, `02`, `03`)
- `figures/`: exported plots and comparison visuals
- `runs/train/`: 300-epoch training runs for YOLOv5nu / YOLOv8n / YOLOv8s

## Run The Web App

Recommended:

```bash
python start.py
```

This launcher:

- starts Django on `0.0.0.0:8000`
- prints both local and LAN URLs
- opens the browser automatically
- makes phone testing on the same Wi-Fi easier

Manual fallback:

```bash
cd webapp
python manage.py runserver
```

## Reproducibility Notes

- Application/demo model: `YOLOv8n`
- Training scripts are kept under `scripts/`
- Extended training outputs are kept under `runs/train/`
- Final report notebooks and exported figures are stored locally for reuse
