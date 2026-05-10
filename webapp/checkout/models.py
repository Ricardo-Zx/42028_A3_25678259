import uuid

from django.db import models
from django.utils import timezone


class CheckoutSession(models.Model):
    class Status(models.TextChoices):
        WAITING_FOR_IMAGE = "waiting_for_image", "Waiting for image"
        PROCESSING = "processing", "Processing"
        READY_FOR_REVIEW = "ready_for_review", "Ready for review"
        EDITED_MANUALLY = "edited_manually", "Edited manually"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class SourceType(models.TextChoices):
        DESKTOP_UPLOAD = "desktop_upload", "Desktop upload"
        MOBILE_UPLOAD = "mobile_upload", "Mobile upload"
        DEMO_IMAGE = "demo_image", "Demo image"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.WAITING_FOR_IMAGE,
    )
    source_type = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        blank=True,
    )
    uploaded_image_url = models.CharField(max_length=512, blank=True)
    annotated_image_url = models.CharField(max_length=512, blank=True)
    model_name = models.CharField(max_length=128, blank=True)
    num_detected = models.PositiveIntegerField(default=0)
    num_unique = models.PositiveIntegerField(default=0)
    avg_conf = models.FloatField(default=0.0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def mark_completed(self) -> None:
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()

    @property
    def subtotal_ex_gst(self):
        return self.subtotal

    def __str__(self) -> str:
        return f"{self.id} ({self.get_status_display()})"


class SessionItem(models.Model):
    class Source(models.TextChoices):
        DETECTED = "detected", "Detected"
        MANUAL = "manual", "Manual"

    session = models.ForeignKey(
        CheckoutSession,
        on_delete=models.CASCADE,
        related_name="items",
    )
    sku_name = models.CharField(max_length=128)
    display_name = models.CharField(max_length=255)
    display_name_cn = models.CharField(max_length=255, blank=True)
    sku_class = models.CharField(max_length=128, blank=True)
    category_name = models.CharField(max_length=128, blank=True)
    barcode = models.CharField(max_length=64, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    avg_conf = models.FloatField(default=0.0)
    source = models.CharField(
        max_length=16,
        choices=Source.choices,
        default=Source.DETECTED,
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-quantity", "sku_name"]

    def __str__(self) -> str:
        return f"{self.session_id}: {self.sku_name} x{self.quantity}"
