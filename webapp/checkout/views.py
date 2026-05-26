from __future__ import annotations

import json
import random
import shutil
import sys
import uuid
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

PROJECT_ROOT = Path(settings.PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.checkout import ProductCatalog, build_checkout_summary
from services.inference import YoloCheckoutDetector

from .models import CheckoutSession, SessionItem

_DETECTOR: YoloCheckoutDetector | None = None
_CATALOG: ProductCatalog | None = None
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DEMO_DIR = Path(settings.BASE_DIR) / "static" / "demo"
DEMO_CANDIDATE_DIR = Path(settings.BASE_DIR) / "static" / "demo_candidates"
STATIC_ROOT = Path(settings.BASE_DIR) / "static"
GST_RATE = Decimal("0.10")
DEMO_POOLS = {
    "easy": [
        "20180824-16-18-28-498.jpg",
        "20180828-13-25-57-1122.jpg",
        "20180829-11-42-12-1699.jpg",
        "20180830-10-19-09-1490.jpg",
        "20180830-13-10-52-1525.jpg",
        "20180830-14-57-13-2203.jpg",
        "20180831-10-03-31-2314.jpg",
        "20180903-09-23-55-2929.jpg",
        "20180903-16-58-08-2712.jpg",
        "20180904-11-32-12-2799.jpg",
    ],
    "medium": [
        "20180904-17-13-59-82.jpg",
        "20180905-14-45-16-170.jpg",
        "20180907-15-06-49-824.jpg",
        "20181012-09-37-54-1293.jpg",
        "20181016-09-24-44-1588.jpg",
        "20181016-11-28-40-1779.jpg",
        "20181018-09-26-06-2284.jpg",
        "20181019-15-09-49-2467.jpg",
        "20181022-09-24-40-2527.jpg",
        "20181022-15-49-11-3258.jpg",
    ],
    "hard": [
        "20180914-11-27-18-684.jpg",
        "20180914-15-07-08-822.jpg",
        "20180920-15-05-04-1418.jpg",
        "20180925-09-24-28-1362.jpg",
        "20180925-10-48-27-1385.jpg",
        "20180925-14-11-39-1592.jpg",
        "20180927-16-57-26-2035.jpg",
        "20181011-16-42-09-3265.jpg",
        "20181018-14-44-18-2902.jpg",
        "20181022-11-36-58-2590.jpg",
    ],
}


def get_detector() -> YoloCheckoutDetector:
    global _DETECTOR
    if _DETECTOR is None:
        products = json.loads(Path(settings.PRODUCTS_PATH).read_text())
        _DETECTOR = YoloCheckoutDetector(settings.MODEL_PATH, products)
    return _DETECTOR


def get_catalog() -> ProductCatalog:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = ProductCatalog.from_files(settings.PRODUCTS_PATH, settings.PRICES_PATH)
    return _CATALOG


def _session_media_subdir(session: CheckoutSession, kind: str) -> Path:
    return Path(settings.MEDIA_ROOT) / kind / str(session.id)


def _clear_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _delete_session_media(session: CheckoutSession) -> None:
    _clear_dir(_session_media_subdir(session, "uploads"))
    _clear_dir(_session_media_subdir(session, "results"))


def _build_demo_choices() -> list[dict]:
    choices: list[dict] = []
    for level, filenames in DEMO_POOLS.items():
        existing = [name for name in filenames if (DEMO_CANDIDATE_DIR / name).exists()]
        if existing:
            picked = random.choice(existing)
            choices.append({
                "file": f"demo_candidates/{picked}",
                "url": settings.STATIC_URL + f"demo_candidates/{picked}",
                "label": level.title(),
                "name": f"{level.title()} scene",
                "chip_class": level,
            })

    if choices:
        return choices

    fallback = [
        ("demo1.jpg", "Easy", "easy"),
        ("demo2.jpg", "Medium", "medium"),
        ("demo3.jpg", "Hard", "hard"),
    ]
    return [
        {
            "file": f"demo/{name}",
            "url": settings.STATIC_URL + f"demo/{name}",
            "label": label,
            "name": f"{label} scene",
            "chip_class": chip,
        }
        for name, label, chip in fallback
        if (DEMO_DIR / name).exists()
    ]


def _build_detection_context(source_path: Path, display_url: str, result_dir: Path, result_url: str) -> dict:
    detection_result = get_detector().predict(source_path, result_dir)
    summary = build_checkout_summary(detection_result.detections, get_catalog())

    avg_conf = (
        sum(d["confidence"] for d in detection_result.detections) /
        len(detection_result.detections) * 100
        if detection_result.detections else 0.0
    )

    return {
        "uploaded_image_url": display_url,
        "annotated_image_url": result_url,
        "rows": summary["rows"],
        "total": summary["total"],
        "num_detected_items": summary["num_detected_items"],
        "num_unique_items": summary["num_unique_items"],
        "avg_conf": round(avg_conf, 1),
        "model_name": Path(settings.MODEL_PATH).stem,
    }


def _get_or_create_session(session_id: str | None = None) -> CheckoutSession:
    if session_id:
        session = CheckoutSession.objects.filter(id=session_id).first()
        if session:
            return session

    return CheckoutSession.objects.create()


def _upsert_session_items(session: CheckoutSession, rows: list[dict], source: str) -> None:
    SessionItem.objects.filter(session=session).delete()
    items = []
    for index, row in enumerate(rows):
        barcode = row.get("barcode")
        items.append(
            SessionItem(
                session=session,
                sku_name=row["sku_name"],
                display_name=row["display_name"],
                display_name_cn=row.get("display_name_cn", ""),
                sku_class=row.get("sku_class", ""),
                category_name=row.get("category_name", ""),
                barcode="" if barcode is None else str(barcode),
                quantity=int(row["quantity"]),
                unit_price=Decimal(str(row["unit_price"])),
                subtotal=Decimal(str(row["subtotal"])),
                avg_conf=float(row.get("avg_conf", 0.0)),
                source=source,
                sort_order=index,
            )
        )
    SessionItem.objects.bulk_create(items)


def _refresh_session_totals(session: CheckoutSession, *, status: str | None = None) -> None:
    # Query directly to bypass any stale prefetch cache (e.g. after a delete)
    items = list(SessionItem.objects.filter(session=session))
    subtotal = Decimal("0.00")
    num_detected = 0
    avg_conf_total = 0.0
    to_update = []

    for item in items:
        correct = item.unit_price * item.quantity
        if correct != item.subtotal:
            item.subtotal = correct
            to_update.append(item)
        subtotal += item.subtotal
        num_detected += item.quantity
        avg_conf_total += item.avg_conf

    if to_update:
        SessionItem.objects.bulk_update(to_update, ["subtotal"])

    session.subtotal = subtotal.quantize(Decimal("0.01"))
    session.gst = (session.subtotal * GST_RATE).quantize(Decimal("0.01"))
    session.total = (session.subtotal + session.gst).quantize(Decimal("0.01"))
    session.num_detected = num_detected
    session.num_unique = len(items)
    session.avg_conf = round(avg_conf_total / len(items), 1) if items else 0.0
    if status:
        session.status = status
    session.save(
        update_fields=[
            "subtotal",
            "gst",
            "total",
            "num_detected",
            "num_unique",
            "avg_conf",
            "status",
            "updated_at",
        ]
    )


def _reset_session_for_retake(session: CheckoutSession, *, message: str = "") -> None:
    _delete_session_media(session)
    SessionItem.objects.filter(session=session).delete()
    session.uploaded_image_url = ""
    session.annotated_image_url = ""
    session.num_detected = 0
    session.num_unique = 0
    session.avg_conf = 0.0
    session.subtotal = Decimal("0.00")
    session.gst = Decimal("0.00")
    session.total = Decimal("0.00")
    session.status = CheckoutSession.Status.WAITING_FOR_IMAGE
    session.completed_at = None
    session.last_error = message
    session.save(
        update_fields=[
            "uploaded_image_url",
            "annotated_image_url",
            "num_detected",
            "num_unique",
            "avg_conf",
            "subtotal",
            "gst",
            "total",
            "status",
            "completed_at",
            "last_error",
            "updated_at",
        ]
    )


def _save_detection_to_session(
    session: CheckoutSession,
    *,
    source_type: str,
    source_path: Path,
    display_url: str,
    result_dir: Path,
    result_url: str,
) -> None:
    session.status = CheckoutSession.Status.PROCESSING
    session.source_type = source_type
    session.last_error = ""
    session.save(update_fields=["status", "source_type", "last_error", "updated_at"])

    ctx = _build_detection_context(source_path, display_url, result_dir, result_url)
    with transaction.atomic():
        session.uploaded_image_url = ctx["uploaded_image_url"]
        session.annotated_image_url = ctx["annotated_image_url"]
        session.model_name = ctx["model_name"]
        session.num_detected = ctx["num_detected_items"]
        session.num_unique = ctx["num_unique_items"]
        session.avg_conf = ctx["avg_conf"]
        session.subtotal = Decimal(str(ctx["total"])).quantize(Decimal("0.01"))
        session.gst = (session.subtotal * GST_RATE).quantize(Decimal("0.01"))
        session.total = (session.subtotal + session.gst).quantize(Decimal("0.01"))
        session.status = CheckoutSession.Status.READY_FOR_REVIEW
        session.completed_at = None
        session.save(
            update_fields=[
                "uploaded_image_url",
                "annotated_image_url",
                "model_name",
                "num_detected",
                "num_unique",
                "avg_conf",
                "subtotal",
                "gst",
                "total",
                "status",
                "completed_at",
                "updated_at",
            ]
        )
        _upsert_session_items(session, ctx["rows"], SessionItem.Source.DETECTED)


def _session_rows(session: CheckoutSession) -> list[dict]:
    rows = []
    for item in session.items.all():
        rows.append(
            {
                "id": item.id,
                "sku_name": item.sku_name,
                "display_name": item.display_name,
                "display_name_cn": item.display_name_cn,
                "sku_class": item.sku_class,
                "category_name": item.category_name or "Unknown",
                "barcode": item.barcode,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.subtotal),
                "avg_conf": round(item.avg_conf, 1),
                "source": item.source,
            }
        )
    return rows


def _build_result_context(
    session: CheckoutSession,
    *,
    message: str = "",
    phone_mode: bool = False,
    receipt_mode: bool = False,
) -> dict:
    rows = _session_rows(session)
    low_conf_count = sum(1 for row in rows if row["avg_conf"] < 60)
    critical_conf_count = sum(1 for row in rows if row["avg_conf"] < 40)
    cat_totals: dict[str, float] = defaultdict(float)
    for row in rows:
        cat_totals[row["category_name"]] += row["subtotal"]
    cat_totals = dict(sorted(cat_totals.items(), key=lambda x: -x[1]))

    sku_options = [
        {
            "sku_name": sku_name,
            "display_name": meta.get("display_name", sku_name),
        }
        for sku_name, meta in sorted(get_catalog().products.items())
    ]

    return {
        "session_id": str(session.id),
        "session": session,
        "total": float(session.total),
        "total_display": f"{session.total:.2f}",
        "num_detected_items": session.num_detected,
        "num_unique_items": session.num_unique,
        "avg_conf": round(session.avg_conf, 1),
        "model_name": session.model_name or Path(settings.MODEL_PATH).stem,
        "cat_labels": json.dumps(list(cat_totals.keys())),
        "cat_values": json.dumps([round(v, 2) for v in cat_totals.values()]),
        "is_completed": session.status == CheckoutSession.Status.COMPLETED,
        "can_edit": session.status != CheckoutSession.Status.COMPLETED,
        "message": message,
        "has_low_conf_warning": low_conf_count > 0,
        "low_conf_count": low_conf_count,
        "critical_conf_count": critical_conf_count,
        "is_empty_detection": session.num_detected == 0,
        "phone_mode": phone_mode,
        "receipt_mode": receipt_mode,
        "sku_options": sku_options,
    }


def _build_phone_state_context(session: CheckoutSession) -> dict:
    if session.status in {
        CheckoutSession.Status.READY_FOR_REVIEW,
        CheckoutSession.Status.EDITED_MANUALLY,
    }:
        return {
            "phone_mode": True,
            "phone_locked": True,
            "session_id": str(session.id),
            "phone_lock_can_retry": True,
            "phone_lock_message": "Checkout is currently under review on the desktop screen. Please finish checkout before uploading another photo.",
        }
    if session.status == CheckoutSession.Status.COMPLETED:
        return {
            "phone_mode": True,
            "phone_locked": True,
            "session_id": str(session.id),
            "phone_lock_can_retry": False,
            "phone_lock_message": "This checkout session has already been completed. Start a new session on the desktop screen to upload another photo.",
        }
    return {
        "phone_mode": True,
        "session_id": str(session.id),
    }


def delete_session(request, session_id: str):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    session = get_object_or_404(CheckoutSession, id=session_id)
    _delete_session_media(session)
    session.delete()
    return JsonResponse({"ok": True})


def poll_session(request, session_id: str):
    session = CheckoutSession.objects.filter(id=session_id).first()
    if not session:
        return JsonResponse({"status": "missing"}, status=404)
    if session.status == CheckoutSession.Status.WAITING_FOR_IMAGE and session.last_error:
        return JsonResponse({"status": "empty", "message": session.last_error})
    if session.status in {
        CheckoutSession.Status.READY_FOR_REVIEW,
        CheckoutSession.Status.EDITED_MANUALLY,
        CheckoutSession.Status.COMPLETED,
    }:
        return JsonResponse({"status": "ready", "url": f"/confirm/{session_id}/"})
    if session.status == CheckoutSession.Status.PROCESSING:
        return JsonResponse({"status": "processing"})
    return JsonResponse({"status": "waiting"})


def history(request):
    sessions = CheckoutSession.objects.exclude(
        status=CheckoutSession.Status.WAITING_FOR_IMAGE
    ).prefetch_related("items").order_by("-completed_at", "-updated_at")
    return render(request, "checkout/history.html", {"sessions": sessions})


def receipt(request, session_id: str):
    session = get_object_or_404(CheckoutSession, id=session_id)
    return render(
        request,
        "checkout/receipt.html",
        _build_result_context(session, receipt_mode=True),
    )


def _build_phone_url(request, session_id: str) -> str:
    base_url = getattr(settings, "PHONE_BASE_URL", "").strip().rstrip("/")
    # Only use server-provided base if it's a real LAN address.
    # If empty or localhost, return "" so the JS template falls back to
    # window.location.origin (which reflects whatever URL the browser used).
    if not base_url or "127.0.0.1" in base_url or "localhost" in base_url:
        return ""
    return f"{base_url}{reverse('home')}?session={session_id}"


def _build_desktop_wait_context(request, session: CheckoutSession, *, message: str = "") -> dict:
    waiting_title = "Waiting for phone scan..."
    waiting_sub = "Scan the QR code with your phone to capture"
    info_title = "Scan & shoot"
    info_text = "Opens Smart Checkout on your phone.<br>Result appears here automatically."

    session_id = str(session.id)
    if session.source_type == CheckoutSession.SourceType.MOBILE_UPLOAD:
        waiting_title = "Waiting for another phone photo..."
        waiting_sub = "Ask the customer or operator to capture another image"
        info_title = "Mobile recapture ready"
        info_text = "The previous image was cleared.<br>Scan the same session and upload another photo."
    elif session.source_type in {
        CheckoutSession.SourceType.DESKTOP_UPLOAD,
        CheckoutSession.SourceType.DEMO_IMAGE,
    }:
        waiting_title = "Ready for another image"
        waiting_sub = "Upload a new image on the left or use phone capture again"
        info_title = "New capture session"
        info_text = "The previous image was cleared.<br>You can upload locally or scan with a phone."

    return {
        "desktop_session": session_id,
        "desktop_phone_url": _build_phone_url(request, session_id),
        "desktop_message": message,
        "desktop_waiting_title": waiting_title,
        "desktop_waiting_sub": waiting_sub,
        "desktop_info_title": info_title,
        "desktop_info_text": info_text,
        "demo_choices": _build_demo_choices(),
    }


def confirm_checkout(request, session_id: str):
    session = get_object_or_404(CheckoutSession.objects.prefetch_related("items"), id=session_id)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "update_items":
            for item in session.items.all():
                raw_qty = request.POST.get(f"qty_{item.id}", str(item.quantity)).strip()
                try:
                    quantity = max(0, int(raw_qty))
                except ValueError:
                    quantity = item.quantity
                if quantity == 0:
                    item.delete()
                elif quantity != item.quantity:
                    item.quantity = quantity
                    item.save(update_fields=["quantity"])
            _refresh_session_totals(session, status=CheckoutSession.Status.EDITED_MANUALLY)
            return render(
                request,
                "checkout/confirm.html",
                _build_result_context(session, message="Quantities updated."),
            )

        if action == "remove_item":
            item_id = request.POST.get("item_id", "").strip()
            session.items.filter(id=item_id).delete()
            _refresh_session_totals(session, status=CheckoutSession.Status.EDITED_MANUALLY)
            return render(
                request,
                "checkout/confirm.html",
                _build_result_context(session, message="Item removed."),
            )

        if action == "add_item":
            sku_name = request.POST.get("manual_sku", "").strip()
            qty_raw = request.POST.get("manual_qty", "1").strip()
            if sku_name not in get_catalog().products:
                return render(
                    request,
                    "checkout/confirm.html",
                    _build_result_context(session, message="Unknown SKU. Choose a valid product."),
                )
            try:
                quantity = max(1, int(qty_raw))
            except ValueError:
                quantity = 1

            product = get_catalog().lookup_product(sku_name)
            unit_price = Decimal(str(get_catalog().lookup_price(sku_name)))
            SessionItem.objects.create(
                session=session,
                sku_name=sku_name,
                display_name=product.get("display_name", sku_name),
                display_name_cn=product.get("display_name", sku_name),
                sku_class=product.get("sku_class", ""),
                category_name=product.get("category_name", "Unknown"),
                barcode="" if product.get("barcode") is None else str(product.get("barcode")),
                quantity=quantity,
                unit_price=unit_price,
                subtotal=unit_price * quantity,
                avg_conf=0.0,
                source=SessionItem.Source.MANUAL,
                sort_order=session.items.count() + 1,
            )
            _refresh_session_totals(session, status=CheckoutSession.Status.EDITED_MANUALLY)
            return render(
                request,
                "checkout/confirm.html",
                _build_result_context(session, message="Manual item added."),
            )

        if action == "confirm_checkout":
            session.mark_completed()
            session.save(update_fields=["status", "completed_at", "updated_at"])
            return render(
                request,
                "checkout/receipt.html",
                _build_result_context(session, message="Checkout completed.", receipt_mode=True),
            )

        if action == "retake_photo":
            _reset_session_for_retake(session)
            return redirect(f"{reverse('home')}?session={session_id}&mode=desktop")

    template = "checkout/receipt.html" if session.status == CheckoutSession.Status.COMPLETED else "checkout/confirm.html"
    return render(request, template, _build_result_context(session, receipt_mode=session.status == CheckoutSession.Status.COMPLETED))


def home(request):
    session_id = request.GET.get("session") or request.POST.get("session_id", "")

    if request.method == "POST":
        is_phone = bool(request.POST.get("phone_upload"))
        session = _get_or_create_session(session_id or None)

        if is_phone and session.status in {
            CheckoutSession.Status.READY_FOR_REVIEW,
            CheckoutSession.Status.EDITED_MANUALLY,
            CheckoutSession.Status.COMPLETED,
        }:
            return render(request, "checkout/home.html", _build_phone_state_context(session))

        demo_name = request.POST.get("demo_image", "").strip()

        if demo_name:
            if ".." in demo_name:
                return render(request, "checkout/home.html", {"error": "Invalid demo image path."})
            src = STATIC_ROOT / demo_name
            if not src.exists() or src.suffix.lower() not in ALLOWED_EXTENSIONS:
                return render(request, "checkout/home.html", {"error": "Demo image not found."})
            display_url = settings.STATIC_URL + demo_name
            source_type = CheckoutSession.SourceType.DEMO_IMAGE
        elif request.FILES.get("image"):
            upload = request.FILES["image"]
            if Path(upload.name).suffix.lower() not in ALLOWED_EXTENSIONS:
                return render(
                    request,
                    "checkout/home.html",
                    {"error": "Please upload a JPG, JPEG, PNG, or WEBP image."},
                )
            upload_dir = _session_media_subdir(session, "uploads")
            _clear_dir(upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)
            suffix = Path(upload.name).suffix.lower() or ".jpg"
            src = upload_dir / f"source{suffix}"
            with src.open("wb+") as dst:
                for chunk in upload.chunks():
                    dst.write(chunk)
            display_url = settings.MEDIA_URL + f"uploads/{session.id}/{src.name}"
            source_type = (
                CheckoutSession.SourceType.MOBILE_UPLOAD
                if is_phone
                else CheckoutSession.SourceType.DESKTOP_UPLOAD
            )
        else:
            return render(request, "checkout/home.html")

        try:
            result_dir = _session_media_subdir(session, "results")
            _clear_dir(result_dir)
            result_dir.mkdir(parents=True, exist_ok=True)
            result_url = settings.MEDIA_URL + f"results/{session.id}/{src.name}"
            _save_detection_to_session(
                session,
                source_type=source_type,
                source_path=src,
                display_url=display_url,
                result_dir=result_dir,
                result_url=result_url,
            )
        except Exception as exc:
            session.last_error = str(exc)
            session.status = CheckoutSession.Status.WAITING_FOR_IMAGE
            session.save(update_fields=["last_error", "status", "updated_at"])
            return render(
                request,
                "checkout/home.html",
                {"error": f"Detection failed: {exc}", "demo_choices": _build_demo_choices()},
            )

        if session.num_detected == 0:
            message = (
                "No products were detected from the latest image. "
                "Please capture a clearer photo or upload another image to continue."
            )
            _reset_session_for_retake(session, message=message)
            if is_phone:
                return render(request, "checkout/home.html", {
                    "phone_mode": True,
                    "phone_done": True,
                    "session_id": str(session.id),
                })
            return render(
                request,
                "checkout/home.html",
                _build_desktop_wait_context(request, session, message=message),
            )

        if is_phone:
            return render(request, "checkout/home.html", {
                "phone_mode": True,
                "phone_done": True,
                "session_id": str(session.id),
            })
        return redirect(reverse("confirm_checkout", args=[str(session.id)]))

    if session_id:
        session = _get_or_create_session(session_id)
        if request.GET.get("mode") == "desktop":
            return render(request, "checkout/home.html", _build_desktop_wait_context(request, session))
        return render(request, "checkout/home.html", _build_phone_state_context(session))

    session = _get_or_create_session()
    session_id = str(session.id)
    return render(request, "checkout/home.html", {
        "desktop_session": session_id,
        "desktop_phone_url": _build_phone_url(request, session_id),
        "demo_choices": _build_demo_choices(),
    })
