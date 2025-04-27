from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel

from apps.core.models import BinanceModel
from apps.trading import choices, constants


class TradingSettings(TimeStampedModel, BinanceModel):
    """Configuración global de trading para el usuario"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trading_settings",
    )
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    webhook_url = models.URLField(blank=True)
    telegram_bot_token = models.CharField(max_length=255, blank=True)
    telegram_chat_id = models.CharField(max_length=255, blank=True)

    # Valores configurables
    investment_percentage = models.IntegerField(default=100)
    leverage = models.IntegerField(default=25)
    take_profit = models.IntegerField(default=25)
    stop_loss = models.IntegerField(default=25)
    symbol = models.CharField(max_length=20, default=constants.BTCUSDT)

    def __str__(self):
        return f"Trading Settings for {self.user.email}"

    def save(self, *args, **kwargs):
        if self.api_key:
            self.api_key = self.encrypt_data(self.api_key)
        if self.api_secret:
            self.api_secret = self.encrypt_data(self.api_secret)
        super().save(*args, **kwargs)


class Signal(TimeStampedModel):
    """Señales recibidas a través de webhooks"""

    ticker = models.CharField(max_length=20)
    signal_type = models.CharField(
        max_length=10,
        choices=choices.OrderSide.choices,
    )
    timeframe = models.CharField(max_length=10)
    strategy = models.CharField(max_length=50)
    price_close = models.DecimalField(max_digits=16, decimal_places=8)
    timestamp = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.ticker} - {self.signal_type} - {self.strategy}"

    class Meta:
        ordering = ["-created"]


class Operation(TimeStampedModel):
    """Operaciones abiertas o cerradas"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="operations",
    )
    symbol = models.CharField(max_length=20)
    direction = models.CharField(
        max_length=10, choices=choices.OperationDirection.choices
    )
    status = models.CharField(
        max_length=10,
        choices=choices.OperationStatus.choices,
        default=choices.OperationStatus.OPEN,
    )
    entry_price = models.DecimalField(max_digits=16, decimal_places=8)
    exit_price = models.DecimalField(
        max_digits=16, decimal_places=8, null=True, blank=True
    )
    quantity = models.DecimalField(max_digits=16, decimal_places=8)
    leverage = models.IntegerField()
    investment = models.DecimalField(max_digits=16, decimal_places=8)
    take_profit = models.IntegerField()
    stop_loss = models.IntegerField()

    # Resultados (solo para operaciones cerradas)
    profit_loss = models.DecimalField(
        max_digits=16, decimal_places=8, null=True, blank=True
    )
    profit_loss_percentage = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    # Timestamps
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.symbol} {self.direction} - {'Open' if self.status == 'open' else 'Closed'}"

    class Meta:
        ordering = ["-opened_at"]


class SignalGroup(TimeStampedModel):
    """Grupo de 5 señales consecutivas que llevaron a una operación"""

    operation = models.OneToOneField(
        Operation,
        on_delete=models.CASCADE,
        related_name="signal_group",
        null=True,
        blank=True,
    )
    signals = models.ManyToManyField(Signal, related_name="signal_groups")
    direction = models.CharField(
        max_length=10,
        choices=choices.OrderSide.choices,
    )

    def __str__(self):
        return f"Signal Group {self.id} - {self.direction}"

    class Meta:
        ordering = ["-created"]


class Bot(TimeStampedModel):
    """Estado actual del bot de trading"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bot_status",
    )
    status = models.CharField(
        max_length=20,
        choices=choices.BotStatus.choices,
        default=choices.BotStatus.IDLE,
    )
    confirming_count = models.IntegerField(default=0)
    current_operation = models.ForeignKey(
        Operation,
        on_delete=models.SET_NULL,
        related_name="bot_status",
        null=True,
        blank=True,
    )
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bot Status: {self.status}"
