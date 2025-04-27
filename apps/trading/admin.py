from django.contrib import admin
from django.utils.html import format_html

from apps.trading import models


@admin.register(models.TradingSettings)
class TradingSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "symbol",
        "investment_percentage",
        "leverage",
        "take_profit",
        "stop_loss",
        "created",
    )
    search_fields = ("user__username", "symbol")
    list_filter = ("symbol", "leverage")
    readonly_fields = ("created", "modified")
    fieldsets = (
        ("Usuario", {"fields": ("user",)}),
        (
            "Credenciales API",
            {
                "fields": ("api_key", "api_secret"),
                "classes": ("collapse",),
            },
        ),
        (
            "Configuración Telegram",
            {
                "fields": (
                    "telegram_bot_token",
                    "telegram_chat_id",
                    "webhook_url",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Configuración Trading",
            {
                "fields": (
                    "symbol",
                    "investment_percentage",
                    "leverage",
                    "take_profit",
                    "stop_loss",
                ),
            },
        ),
        (
            "Información Temporal",
            {
                "fields": ("created", "modified"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(models.Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = (
        "ticker",
        "signal_type",
        "timeframe",
        "strategy",
        "price_close",
        "created",
        "processed",
    )
    list_filter = (
        "signal_type",
        "timeframe",
        "strategy",
        "processed",
        "created",
    )
    search_fields = ("ticker", "strategy")
    date_hierarchy = "created"
    readonly_fields = ("created",)
    list_per_page = 50


@admin.register(models.Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "symbol",
        "direction",
        "status",
        "entry_price",
        "exit_price",
        "leverage",
        "investment",
        "profit_loss_display",
        "opened_at",
        "closed_at",
    )
    list_filter = ("status", "direction", "symbol", "opened_at")
    search_fields = ("user__username", "symbol")
    date_hierarchy = "opened_at"
    readonly_fields = ("opened_at", "closed_at")
    fieldsets = (
        (
            "Usuario y Activo",
            {"fields": ("user", "symbol", "direction", "status")},
        ),
        (
            "Detalles de Entrada",
            {
                "fields": (
                    "entry_price",
                    "quantity",
                    "leverage",
                    "investment",
                    "opened_at",
                ),
            },
        ),
        (
            "Configuración de Riesgo",
            {
                "fields": ("take_profit", "stop_loss"),
            },
        ),
        (
            "Detalles de Salida",
            {
                "fields": (
                    "exit_price",
                    "profit_loss",
                    "profit_loss_percentage",
                    "closed_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def profit_loss_display(self, obj):
        if obj.profit_loss is None:
            return "-"

        value = float(obj.profit_loss_percentage)
        color = "green" if value >= 0 else "red"
        return format_html(
            '<span style="color: {}">{}%</span>', color, format(value, ".2f")
        )

    profit_loss_display.short_description = "P&L %"


@admin.register(models.SignalGroup)
class SignalGroupAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "direction",
        "operation_status",
        "signal_count",
        "created",
    )
    list_filter = ("direction", "created")
    filter_horizontal = ("signals",)
    readonly_fields = ("created",)
    search_fields = ("operation__symbol",)
    date_hierarchy = "created"

    def operation_status(self, obj):
        if not obj.operation:
            return format_html(
                '<span class="badge badge-secondary">Sin operación</span>'
            )

        status = obj.operation.status
        if status == "open":
            return format_html('<span style="color: blue;">Abierta</span>')
        else:
            return format_html('<span style="color: purple;">Cerrada</span>')

    operation_status.short_description = "Estado de Operación"

    def signal_count(self, obj):
        return obj.signals.count()

    signal_count.short_description = "Número de Señales"


@admin.register(models.Bot)
class BotStatusAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status_display",
        "confirming_count",
        "current_operation_info",
        "last_updated",
    )
    list_filter = ("status", "last_updated")
    search_fields = ("user__username",)
    readonly_fields = ("last_updated",)

    def status_display(self, obj):
        status_colors = {
            "idle": "secondary",
            "listening": "primary",
            "confirming": "warning",
            "operating": "success",
        }
        color = status_colors.get(obj.status, "info")
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "Estado"

    def current_operation_info(self, obj):
        if not obj.current_operation:
            return "Sin operación"
        return format_html(
            "{} {} ({})",
            obj.current_operation.symbol,
            obj.current_operation.direction,
            obj.current_operation.get_status_display(),
        )

    current_operation_info.short_description = "Operación Actual"
