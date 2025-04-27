import django_filters

from apps.trading import models


class SignalFilterSet(django_filters.FilterSet):
    """Filtro para las señales"""

    class Meta:
        model = models.Signal
        fields = {
            "ticker": ["exact"],
            "signal_type": ["exact"],
            "created": ["gte", "lte"],
        }
