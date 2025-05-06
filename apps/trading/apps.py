from django.apps import AppConfig


class TradingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.trading"

    def ready(self):
        from apps.trading import signals  # noqa: F401
