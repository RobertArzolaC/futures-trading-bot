from django.db import models


class OrderSide(models.TextChoices):
    BUY = "buy", "Buy"
    SELL = "sell", "Sell"
    HOLD = "hold", "Hold"


class OrderType(models.TextChoices):
    LIMIT = "limit", "Limit"
    MARKET = "market", "Market"


class OperationStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    PENDING = "pending", "Pending"
    CANCELLED = "cancelled", "Cancelled"


class OperationDirection(models.TextChoices):
    LONG = "long", "Long"
    SHORT = "short", "Short"


class BotStatus(models.TextChoices):
    IDLE = "idle", "Inactive"
    LISTENING = "listening", "Listening"
    CONFIRMING = "confirming", "Confirming"
    OPERATING = "operating", "Operating"


class BotAction(models.TextChoices):
    START = "start", "Start"
    STOP = "stop", "Stop"
    RESTART = "restart", "Restart"
