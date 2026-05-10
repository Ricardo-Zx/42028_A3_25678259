# 42028: Deep Learning and Convolutional Neural Network  
## Assignment 3 Project Report Draft

**Project Title:** AI-Assisted Smart Checkout System for 200-SKU Retail Product Detection  
**Team Name and Project Number:** [Add team name / project number]  
**Team Members:** [Add full names and student IDs]  
**Date:** [Add submission date]

---

## Abstract

This project develops a closed-set smart checkout prototype that detects retail products from checkout-scene images and converts the detection output into an itemised receipt. The system is based on the Retail Product Checkout (RPC) dataset and focuses on a 200-SKU subset represented as an object-detection problem. We first transformed RPC checkout-scene annotations from COCO format into YOLO format and constructed a balanced 80/10/10 train-validation-test split stratified by difficulty level. Three lightweight detector variants, YOLOv5nu, YOLOv8n, and YOLOv8s, were trained and compared under a common experimental configuration. The final deployed model was YOLOv8n, which achieved the highest weighted score while remaining efficient for interactive web inference. On top of the detector, we implemented a Django-based smart checkout web application with desktop and mobile interfaces, manual review support, receipt generation, and session history. The final system demonstrates that accurate SKU-level detection can be integrated into a practical human-in-the-loop checkout workflow, while also revealing limitations related to image quality, closed-set recognition, and the remaining need for manual verification in difficult scenes.

---

## 1. Introduction and Background

Retail checkout is a high-frequency operational task in supermarkets, convenience stores, and unattended kiosks. Traditional barcode-based self-checkout is effective when each item can be scanned individually, but it becomes less convenient when multiple products are placed together, partially overlap, or are photographed instead of scanned. In such cases, computer vision offers a more natural interaction mode: the user captures one checkout-scene image and the system predicts the products present, their quantities, and the corresponding bill.

This project investigates whether a compact object detector can support a practical smart checkout workflow for a fixed set of retail products. Instead of treating the task as a general-purpose image recognition problem, we frame it as a 200-class closed-set object detection problem. The system therefore does not attempt to recognise arbitrary unseen products. Rather, it focuses on reliably identifying products from a predefined SKU catalogue and converting the detections into an itemised receipt.

The project has two equally important parts. The first is the experimental pipeline: dataset preparation, model training, evaluation, and model selection. The second is the application layer: a desktop-and-mobile web interface that lets users upload or capture an image, review uncertain predictions, adjust item quantities, and complete a checkout session. This combined approach makes the project both technically grounded and deployment-oriented.

### 1.1 The Problem We Tried to Solve

The problem addressed in this project is the automated recognition of multiple retail products in a single checkout-scene image and the conversion of these detections into a usable checkout summary. In practice, this requires solving several sub-problems simultaneously:

1. Detecting many small or partially overlapping products in one image.
2. Distinguishing visually similar SKUs at fine-grained product level.
3. Estimating quantities accurately enough for billing.
4. Turning raw detections into an operator-facing checkout workflow rather than a model-only demo.

The practical challenge is that checkout images are not as clean as isolated product photographs. Products may appear at different scales, rotations, and lighting conditions, and difficult scenes can reduce the confidence of the detector. The system therefore needs not only a strong detector, but also a review mechanism that allows uncertain outputs to be checked before final checkout.

### 1.2 Motivation

The motivation for this project comes from the growing demand for semi-automated checkout systems in retail environments. A camera-based system can reduce repetitive manual scanning and make checkout more natural, especially in small-scale smart retail settings. However, a purely automatic solution is risky when the model is uncertain, because a missed item or a wrong SKU directly affects billing correctness.

For this reason, the project was designed as an AI-assisted checkout system rather than a fully autonomous replacement for human judgement. The detector provides a fast first-pass interpretation of the scene, and the interface supports human review when needed. This design choice reflects a pragmatic deployment mindset: in a real checkout environment, reliability and operator control matter at least as much as raw benchmark accuracy.

### 1.3 Application

The main application of the project outcome is a smart checkout assistant for desktop and mobile use. In the implemented workflow, a checkout session can be started from a desktop browser, and the input image can be provided either by direct upload on the desktop or by scanning a QR code and capturing the image from a mobile device. The detector then predicts the products in the scene, the system aggregates them into SKU-level rows, and the interface displays the corresponding quantity, price, subtotal, GST, and final total.

This application is relevant to self-checkout stations, cashier-assistance tools, and smart retail demonstration systems. Even though the current implementation is a prototype, it already supports core operational features such as manual item correction, session history, retake, low-confidence warnings, and receipt printing.

### 1.4 Dataset

This project uses the **Retail Product Checkout (RPC)** dataset [2], which is designed for SKU-level retail recognition. RPC contains both isolated product images and more realistic checkout-scene images. For this project, only the **`val2019` checkout-scene subset** was used as the source for model training and evaluation, because the original `train2019` images are not representative of the intended application scenario. They are largely product-centric and cleaner than actual checkout scenes, whereas `val2019` contains the multi-product layouts required for this task.

The final prepared dataset is a **200-SKU closed-set detection benchmark** with:

- **200 SKU classes**
- **17 product categories**
- **6000 checkout-scene images**
- **73,602 annotated bounding boxes** in total

The dataset was split into train, validation, and test sets using a stratified strategy based on the RPC difficulty labels:

- **Train:** 4800 images, 58,906 boxes
- **Validation:** 600 images, 7,345 boxes
- **Test:** 600 images, 7,351 boxes

Each split preserves a balanced distribution of:

- **Easy:** 1600 / 200 / 200
- **Medium:** 1600 / 200 / 200
- **Hard:** 1600 / 200 / 200

In addition to the detection annotations, the project also maintains a structured SKU catalogue in `products.json`, which maps YOLO class IDs to product names, barcodes, and category labels. Price information is stored separately in `prices.json` and used by the checkout application after detection.

**Suggested figure insertions for this section**

- `[Insert Figure: Dataset difficulty distribution — use figures/fig_level_distribution.png]`
- `[Insert Figure: Sample checkout-scene images — use figures/fig_sample_scenes.png]`
- `[Insert Figure: Top-30 SKU frequency — use figures/fig_top30_sku.png]`

---

## 2. Overview of the Architecture/System

The proposed system is composed of four main layers:

1. **Dataset preparation layer**  
   Converts the RPC checkout-scene annotations from COCO to YOLO format, creates the stratified data split, and stores dataset metadata for training and analysis.

2. **Detection model layer**  
   Trains and evaluates multiple YOLO variants (YOLOv5nu, YOLOv8n, YOLOv8s) under a common configuration and selects the final detector for deployment.

3. **Checkout aggregation layer**  
   Maps class IDs to SKU metadata, groups detections by SKU, computes quantities, average confidence, and checkout subtotals, and prepares structured item rows for display.

4. **Web application layer**  
   Provides the user-facing desktop and mobile interfaces for image input, result review, manual correction, receipt generation, and history management.

The resulting system is not just a model inference demo. It is a full workflow prototype that starts from image capture and ends with a verified checkout receipt.

### 2.1 Flow Diagram / Workflow

The end-to-end workflow can be summarised as follows:

1. The user starts a checkout session from the desktop interface.
2. An image is supplied either by desktop upload, desktop camera capture, demo selection, or QR-linked mobile submission.
3. The selected image is passed to the YOLO detector.
4. The model predicts bounding boxes, class IDs, and confidence scores.
5. Predictions are mapped to SKU metadata and aggregated into checkout rows.
6. The review interface presents detected items, prices, subtotals, and confidence warnings.
7. The operator may adjust quantities, delete incorrect items, add missing items, or retake the image.
8. Once confirmed, the system generates a receipt and stores the session in history.

This workflow reflects a **human-in-the-loop checkout design**. The detector accelerates the initial interpretation of the image, but final confirmation still remains under operator control.

**Suggested figure insertion**

- `[Insert Figure: System workflow / architecture diagram — create or add manually if required]`

### 2.2 CNN Architecture Design

The project evaluates three lightweight YOLO-family object detectors:

| Model | Base weights | Approx. parameters | Role in study |
|---|---:|---:|---|
| YOLOv5nu | `yolov5nu.pt` | ~2.5M | Lightweight baseline |
| YOLOv8n | `yolov8n.pt` | ~3.2M | Final deployment model |
| YOLOv8s | `yolov8s.pt` | ~11.2M | Larger comparison model |

All three models were trained using the same dataset split and the same overall training configuration so that the comparison remained controlled. The training process was executed through a terminal script instead of inside a Jupyter notebook, because long YOLO runs caused repeated Jupyter kernel crashes on the available SageMaker instance due to RAM pressure from validation logging.

The final deployed detector is **YOLOv8n**. It was selected because it achieved the highest weighted score under our evaluation scheme while remaining compact enough for responsive web-based inference. Importantly, the 300-epoch comparison showed that all three models converged to an extremely similar performance range, indicating diminishing returns from larger model size on this particular 200-SKU checkout task.

The architecture choice therefore reflects a practical trade-off:

- **High detection accuracy**
- **Smaller model size**
- **Lower inference overhead**
- **More suitable deployment behaviour for an interactive application**

### 2.3 GUI Design

The graphical user interface was implemented as a Django web application with both desktop and mobile interaction modes. The desktop interface is the main checkout console, while the mobile interface acts as an auxiliary image-capture device connected through a QR-based session.

The desktop interface includes:

- local image upload and drag-and-drop
- demo image selection
- QR-based mobile capture
- real-time session handling
- a review page with editable quantities
- low-confidence warnings
- manual item addition and item removal
- receipt generation
- session history

The mobile interface provides a simpler workflow:

- scan the QR code from the desktop session
- take a new photo or choose one from the phone library
- preview the selected image
- submit the image back to the active checkout session

This split between desktop and mobile is deliberate. The desktop remains the main operational interface for review and checkout, while the mobile device functions as a convenient camera input channel.

**Suggested figure insertions for this section**

- `[Insert Figure: Main desktop interface]`
- `[Insert Figure: Confirm/review interface]`
- `[Insert Figure: Receipt page]`
- `[Insert Figure: History page]`
- `[Insert Figure: Mobile capture workflow screenshots]`

---

## 3. Results and Evaluation

### 3.1 Experimental Settings

The three YOLO models were trained under a common configuration:

| Parameter | Value |
|---|---:|
| Epochs | 300 (upper bound) |
| Early stopping patience | 50 |
| Input size | 640 × 640 |
| Batch size | 8 |
| Workers | 4 |
| Device | CUDA (Tesla T4) |
| Training mode | Terminal script (`scripts/train_all.py`) |

The batch size was reduced from 16 to 8 because the original setting caused consistent memory instability on the SageMaker environment. With batch size 8, long terminal-based training completed reliably while maintaining very strong final performance.

Evaluation was based on four metrics:

- **Precision**
- **Recall**
- **mAP@0.5**
- **mAP@0.5:0.95**

To support final model selection, a weighted score was also computed:

\[
\text{Weighted Score} = 0.50 \cdot \text{mAP@0.5:0.95} + 0.25 \cdot \text{mAP@0.5} + 0.15 \cdot \text{Recall} + 0.10 \cdot \text{Precision}
\]

This weighting places the strongest emphasis on **mAP@0.5:0.95**, which is the strictest overall detection metric and best reflects both detection quality and localisation quality. Recall is weighted slightly higher than precision because in a checkout scenario, missing an item is generally more serious than over-detecting one.

### 3.2 Pre-Processing

Several preprocessing and preparation steps were required before training:

1. **Dataset selection**  
   Only RPC `val2019` checkout-scene images were used as the source subset.

2. **Stratified splitting by difficulty**  
   The scene-level `level` field in RPC was used to create a balanced 80/10/10 train-validation-test split.

3. **COCO-to-YOLO conversion**  
   Original bounding boxes in COCO format (`x, y, width, height`) were converted into YOLO format (`class_id, x_center, y_center, width, height`) with normalised coordinates.

4. **SKU metadata alignment**  
   A 200-class mapping was maintained between YOLO IDs and product metadata, including SKU name, display name, barcode, and category label.

5. **Price integration**  
   Static price metadata was associated with each SKU to support final bill generation inside the web application.

These preprocessing steps are important because they connect the raw dataset to the actual application workflow. Without SKU metadata and pricing information, the detector would only produce class labels rather than a usable checkout result.

### 3.3 Experimental Results

The final comparison of the three trained models is shown below.

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 | Weighted Score |
|---|---:|---:|---:|---:|---:|
| YOLOv8n | 0.9918 | 0.9948 | 0.9939 | 0.8707 | 0.9322 |
| YOLOv8s | 0.9943 | 0.9966 | 0.9942 | 0.8682 | 0.9316 |
| YOLOv5nu | 0.9948 | 0.9955 | 0.9942 | 0.8682 | 0.9315 |

Several observations follow from these results.

First, all three models performed at a very high level. Precision, recall, and mAP@0.5 were all close to 0.99, while mAP@0.5:0.95 remained close to 0.87 for all variants. This indicates that the task is learnable under the prepared dataset split and that the training pipeline is stable across all three model variants.

Second, the performance gap between the three models is very small. The weighted score spread across all three models is less than 0.001, which means that no model dominates the others by a large margin. This is an important finding in itself: for this 200-SKU checkout task, larger model capacity does not translate into a dramatic performance advantage.

Third, **YOLOv8n** achieved the highest weighted score and was therefore selected as the final deployment model for the web application. This choice is consistent with both quantitative performance and practical deployment needs. Because YOLOv8n is smaller than YOLOv8s, it is more suitable for responsive inference in an interactive checkout interface, while still delivering top-ranked validation performance.

**Suggested figure insertions for this section**

- `[Insert Figure: Training curves — use figures/fig_training_curves.png]`
- `[Insert Figure: Convergence plot — use figures/fig_convergence.png]`
- `[Insert Figure: Metrics comparison — use figures/fig_metrics_bar.png]`
- `[Insert Figure: Precision/Recall or F1 curves — use figures/fig_pr_curves.png and/or figures/fig_f1_curves.png]`
- `[Insert Figure: Sample predictions — use figures/fig_sample_predictions.png]`

### 3.4 Limitations

Although the system performs strongly overall, several limitations remain.

**1. Closed-set recognition**  
The detector only recognises the 200 predefined SKUs included in the project catalogue. Unknown products outside this set cannot be classified correctly and are therefore outside the system’s operating scope.

**2. Sensitivity to image quality and angle**  
Low-quality captures, unfavourable angles, motion blur, and strong overlap can reduce confidence and produce incomplete detections. For this reason, the system includes low-confidence warnings and retake support.

**3. Single-image checkout assumption**  
The current system assumes that a single image is sufficient to represent the order. In more complex scenes, multiple captures from different viewpoints might be necessary for stronger robustness.

**4. Static pricing and simplified tax logic**  
The prototype uses a static SKU-price table and a simple GST calculation. It does not connect to an external inventory, promotions engine, or live pricing source.

**5. Human review is still required**  
The system is intentionally designed as an AI-assisted workflow rather than a fully autonomous one. This is appropriate for a prototype, but it also means that operator intervention remains necessary for difficult or low-confidence cases.

---

## 4. Discussion and Conclusions

This project demonstrates that a compact deep-learning-based detector can be integrated into a realistic smart checkout workflow rather than being limited to offline benchmark evaluation. Starting from RPC checkout-scene images, we prepared a balanced 200-SKU detection dataset, trained three YOLO-family models, compared their results under a common setup, and deployed the final chosen detector in a functional web application with desktop and mobile interaction.

The technical results are strong. All three models converged to a very similar performance range, indicating that the dataset and task are well aligned with lightweight detection architectures. Among the three, YOLOv8n provided the best overall balance of strict detection performance and deployment suitability, which justified its use as the final demonstration model.

More importantly, the project outcome is not only a detector but also a usable system. The web application supports image input from both desktop and mobile devices, QR-linked sessions, annotated result review, quantity adjustment, manual item correction, receipt generation, and history management. These features make the system closer to a real operational prototype than to a purely academic model benchmark.

At the same time, the project confirms that fully automatic checkout remains difficult in challenging scenes. Low-confidence detections, difficult camera angles, and the closed-set nature of the catalogue mean that human review is still necessary. This is not a failure of the system design; instead, it reflects a realistic engineering choice. A human-in-the-loop smart checkout pipeline is often more trustworthy and deployable than a brittle end-to-end automatic system that cannot surface its uncertainty.

Future improvements could focus on several directions:

- extending beyond the current closed 200-SKU catalogue
- adding multi-image or video-assisted checkout
- integrating OCR or barcode reading as a secondary verification channel
- improving robustness under heavy overlap and difficult lighting
- connecting the billing logic to real inventory and pricing systems

Overall, the final prototype successfully achieves the project objective: it shows how deep learning, structured SKU metadata, and a practical GUI can be combined into a usable smart checkout system for retail product recognition.

---

## 5. References

[1] Ultralytics, “Ultralytics YOLO Documentation,” Available: https://docs.ultralytics.com/

[2] DIYer22, “Retail Product Checkout Dataset,” Kaggle, Available: https://www.kaggle.com/datasets/diyer22/retail-product-checkout-dataset

[3] Django Software Foundation, “Django Documentation,” Available: https://docs.djangoproject.com/

[4] [Add the original RPC dataset publication here if required by the teaching team; verify authors, year, and title before final submission.]

[5] [If required, add the preferred YOLO-family paper or Ultralytics repository citation in the final submission format.]

---

## Appendices

### Appendix A. Individual Contribution

**[Team Member 1 Name]**  
[Write up to half a page about this member’s contribution.]

**[Team Member 2 Name]**  
[Write up to half a page about this member’s contribution.]

**[Team Member 3 Name]**  
[Write up to half a page about this member’s contribution.]

### Appendix B. Individual Contribution Split

| Team Member Name | Percentage |
|---|---:|
| [Full Name] | [%] |
| [Full Name] | [%] |
| [Full Name] | [%] |

All team members have discussed and agreed on the above individual contribution split.
