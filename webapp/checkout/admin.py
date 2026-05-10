from django.contrib import admin

from .models import CheckoutSession, SessionItem


class SessionItemInline(admin.TabularInline):
    model = SessionItem
    extra = 0


@admin.register(CheckoutSession)
class CheckoutSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "source_type",
        "num_detected",
        "num_unique",
        "total",
        "updated_at",
    )
    list_filter = ("status", "source_type", "model_name")
    search_fields = ("id",)
    inlines = [SessionItemInline]
