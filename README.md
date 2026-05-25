# Smart Retail Checkout Web Application

This project is the deployment-oriented prototype for Assignment 3. It implements a smart retail checkout workflow around a trained YOLOv8n detector, including image input, product detection, SKU mapping, bill review, receipt generation and checkout history.

The local package is intended for running and demonstrating the checkout web application. Model training was completed separately in the AWS SageMaker environment and is not required for normal local use.

## What This Package Contains

- `webapp/`: Django web application, pages and database models.
- `services/`: reusable YOLO inference and checkout calculation logic.
- `models/yolov8n_best.pt`: final deployed detector used by the checkout prototype.
- `configs/products.json`: SKU metadata, including YOLO class IDs, names, barcodes and categories.
- `configs/prices.json`: product price table used for subtotal, GST and total calculation.
- `webapp/static/demo_candidates/`: preset checkout-scene images for quick testing.
- `figures/`: exported figures used in the final report.
- `notebooks/`: reporting notebooks copied back from the training environment.
- `scripts/`: dataset preparation and training scripts kept for reproducibility reference.

## What This Package Is Not For

This package is not the full training environment. The final model was trained on AWS SageMaker, not inside the local web application project.

The local project does not include the full RPC dataset or require retraining before use. To reproduce training from scratch, use the scripts under `scripts/` together with the RPC dataset and a suitable GPU environment. The normal demo workflow only needs the included `models/yolov8n_best.pt` file.

## Requirements

Recommended environment:

- Python 3.10 or 3.11
- macOS, Windows or Linux
- Enough disk space for the model and Python packages
- A GPU is optional for running the demo; CPU inference works but may be slower

Install Python dependencies from the project root:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then install the dependencies:

```bash
pip install -r requirements.txt
```

If PyTorch installation fails on your machine, install the correct PyTorch build for your platform first, then run the command above again. Ultralytics depends on PyTorch for YOLO inference.

## Quick Start

From the project root:

```bash
python start.py
```

The launcher starts Django on port `8000`, prints both local and LAN URLs, and opens the local desktop URL in the browser.

On first launch, `start.py` also runs Django database migrations automatically. This creates the local SQLite tables needed for checkout sessions, receipts and history records.

Use this URL on the same computer:

```text
http://127.0.0.1:8000
```

To stop the server, press `Ctrl+C` in the terminal.

## Manual Start

If the launcher does not work, start Django manually:

```bash
cd webapp
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Then open:

```text
http://127.0.0.1:8000
```

## How To Use The Demo

1. Open the desktop web interface.
2. Start a checkout session.
3. Submit a checkout-scene image using one of the available input methods:
   - upload a local image;
   - select a preset demo image;
   - scan the QR code and capture an image from a mobile phone.
4. Wait for YOLOv8n detection to finish.
5. Review the generated bill on the checkout review page.
6. Adjust quantities, remove incorrect items, manually add missed products or retake the image if needed.
7. Confirm the checkout to generate the receipt.
8. Open the history page to review previous checkout records.

## Mobile Capture

For mobile capture, the phone and the computer running Django must be connected to the same Wi-Fi network.

After running `python start.py`, the terminal prints a phone-accessible LAN URL such as:

```text
http://192.168.x.x:8000
```

Open that URL on the phone or scan the QR code shown on the desktop checkout page. The phone acts only as an image capture device; final review and checkout confirmation remain on the desktop interface.

If the printed phone URL starts with a Docker, VPN or virtual-network address and does not work on the phone, use the computer's real Wi-Fi IP address instead. The desktop browser should still use `http://127.0.0.1:8000`.

Note: the QR code on the page uses a browser-side QR library loaded from a CDN. If the QR code does not appear, use the printed phone URL directly.

## Model And Data Notes

- The deployed model is `models/yolov8n_best.pt`.
- The system maps YOLO class IDs to products through `configs/products.json`.
- Prices are loaded from `configs/prices.json`.
- The prepared training dataset was based on the RPC `val2019` checkout-scene subset.
- The local package does not include the full RPC dataset.
- Model training and evaluation were performed separately; local execution is for inference and checkout workflow demonstration.

## Useful Commands

Run a smoke test for inference and checkout summary generation:

```bash
python smoke_test.py
```

Run Django database migrations if the SQLite database is missing or recreated:

```bash
cd webapp
python manage.py migrate
```

Start the web application manually:

```bash
cd webapp
python manage.py runserver 0.0.0.0:8000
```

## Troubleshooting

- If `ultralytics` or `torch` is missing, run `pip install -r requirements.txt`.
- If the model cannot be loaded, check that `models/yolov8n_best.pt` exists.
- If product names or prices are missing, check `configs/products.json` and `configs/prices.json`.
- If mobile capture does not connect, confirm that the phone and computer are on the same Wi-Fi network and use the LAN URL printed by `start.py`.
- If the port is already in use, stop the old server process or change the port in `start.py`.
