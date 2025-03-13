from django.db.models import Count, Sum
from django.views.generic import TemplateView

from apps.core.mixins import CacheMixin
from apps.trading import forms as trading_forms
from apps.trading import models as trading_models


class DashboardView(CacheMixin, TemplateView):
    template_name = "dashboard/index.html"
    cache_timeout = 300

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        bot_status, _ = trading_models.BotStatus.objects.get_or_create(
            user=self.request.user
        )

        # Obtener operación actual si existe
        current_operation = None
        if bot_status.current_operation:
            current_operation = bot_status.current_operation

        # Obtener estadísticas generales
        operations = trading_models.Operation.objects.filter(
            user=self.request.user
        )
        total_operations = operations.count()
        closed_operations = operations.filter(status="closed")

        # Calcular ganancias/pérdidas
        profit_stats = closed_operations.aggregate(
            total_profit=Sum("profit_loss"), count=Count("id")
        )

        # Ultimas 5 señales
        recent_signals = trading_models.Signal.objects.all().order_by(
            "-timestamp"
        )[:5]

        context.update(
            {
                "bot_status": bot_status,
                "current_operation": current_operation,
                "total_operations": total_operations,
                "closed_count": closed_operations.count(),
                "profit_stats": profit_stats,
                "recent_signals": recent_signals,
                "bot_control_form": trading_forms.BotControlForm(),
            }
        )

        return context
