import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView
from django_filters.views import FilterView

from apps.trading import choices, filtersets, forms, models, tasks


class SettingsView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Vista para configuración del trading"""

    model = models.TradingSettings
    form_class = forms.TradingSettingsForm
    template_name = "trading/settings.html"
    success_url = reverse_lazy("apps.trading:settings")
    success_message = "Trading settings updated successfully."

    def get_queryset(self):
        """Obtener la configuración existente del usuario"""
        try:
            return models.TradingSettings.objects.get(user=self.request.user)
        except models.TradingSettings.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        """Agregar la configuración existente al contexto"""
        context = super().get_context_data(**kwargs)
        settings = self.get_queryset()
        if settings:
            context["form"].initial = {
                "symbol": settings.symbol,
                "investment_percentage": settings.investment_percentage,
                "leverage": settings.leverage,
                "take_profit": settings.take_profit,
                "stop_loss": settings.stop_loss,
                "api_key": settings.api_key,
                "api_secret": settings.api_secret,
            }
        return context

    def form_valid(self, form):
        """Guardar la configuración y encriptar las claves API"""
        settings = self.get_queryset()
        if settings:
            form.instance = settings
        form.instance.user = self.request.user
        return super().form_valid(form)


class OperationListView(LoginRequiredMixin, View):
    """Lista de operaciones"""

    def get(self, request):
        operations = models.Operation.objects.filter(
            user=request.user
        ).order_by("-opened_at")
        return render(
            request, "trading/operations.html", {"operations": operations}
        )


class OperationDetailView(LoginRequiredMixin, View):
    """Detalles de una operación específica"""

    def get(self, request, pk):
        operation = get_object_or_404(
            models.Operation, pk=pk, user=request.user
        )

        try:
            signal_group = operation.signal_group
            signals = signal_group.signals.all()
        except Exception:
            signals = []

        context = {
            "operation": operation,
            "signals": signals,
        }

        return render(request, "trading/operation_detail.html", context)


class SignalListView(LoginRequiredMixin, FilterView):
    """Lista de señales recibidas"""

    model = models.Signal
    filterset_class = filtersets.SignalFilterSet
    template_name = "trading/signals.html"
    context_object_name = "signals"
    paginate_by = 10


class ManualOperationView(LoginRequiredMixin, View):
    """Crear una operación manual"""

    def get(self, request):
        # Prellenar con las configuraciones del usuario
        initial_data = {}
        try:
            settings = models.TradingSettings.objects.get(user=request.user)
            initial_data = {
                "symbol": settings.symbol,
                "investment_percentage": settings.investment_percentage,
                "leverage": settings.leverage,
                "take_profit": settings.take_profit,
                "stop_loss": settings.stop_loss,
            }
        except models.TradingSettings.DoesNotExist:
            pass

        form = forms.ManualOperationForm(initial=initial_data)
        return render(request, "trading/manual_operation.html", {"form": form})

    def post(self, request):
        form = forms.ManualOperationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # Crear tarea para abrir posición
            tasks.open_position.delay(
                user_id=request.user.id,
                symbol=data["symbol"],
                direction=data["direction"],
                investment_percentage=data["investment_percentage"],
                leverage=data["leverage"],
                take_profit=data["take_profit"],
                stop_loss=data["stop_loss"],
            )

            messages.info(
                request,
                "Manual operation request sent. It will be processed shortly.",
            )
            return redirect("apps.trading:operations")


class CloseOperationView(LoginRequiredMixin, View):
    """Cerrar una operación existente"""

    def get(self, request, pk):
        operation = get_object_or_404(
            models.Operation,
            pk=pk,
            user=request.user,
            status=choices.OperationStatus.OPEN,
        )
        return render(
            request,
            "trading/close_operation_confirm.html",
            {"operation": operation},
        )

    def post(self, request, pk):
        operation = get_object_or_404(
            models.Operation,
            pk=pk,
            user=request.user,
            status=choices.OperationStatus.OPEN,
        )
        tasks.close_position.delay(operation_id=operation.id)

        messages.info(
            request,
            "Operation closing request sent. It will be processed shortly.",
        )
        return redirect("apps.trading:operations")


class BotControlView(LoginRequiredMixin, View):
    """Controlar el estado del bot"""

    def post(self, request):
        form = forms.BotControlForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]

            if action == choices.BotAction.START:
                tasks.start_bot.delay(user_id=request.user.id)
                messages.success(request, "Bot started successfully.")
            elif action == choices.BotAction.STOP:
                tasks.stop_bot.delay(user_id=request.user.id)
                messages.success(request, "Bot stopped successfully.")
            elif action == choices.BotAction.RESTART:
                tasks.restart_bot.delay(user_id=request.user.id)
                messages.success(request, "Bot restarted successfully.")

        return redirect("apps.dashboard:index")


@method_decorator(csrf_exempt, name="dispatch")
class WebhookReceiverView(View):
    """Endpoint para recibir señales de webhook"""

    def post(self, request):
        try:
            # Obtener datos del webhook
            data = json.loads(request.body)
            if not data:
                return JsonResponse(
                    {"status": "error", "message": "Empty payload"}
                )

            # Validar formato de señal esperado
            required_fields = [
                "ticker",
                "signal",
                "timeframe",
                "strategy",
                "price_close",
            ]
            if not all(field in data for field in required_fields):
                return JsonResponse(
                    {"status": "error", "message": "Invalid signal format"}
                )

            # Crear señal en la base de datos
            signal = models.Signal.objects.create(
                ticker=data["ticker"],
                signal_type=data["signal"],
                timeframe=data["timeframe"],
                strategy=data["strategy"],
                price_close=data["price_close"],
            )

            # Crear tarea para procesar la señal
            tasks.process_signal.delay(signal_id=signal.id)

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Signal received and processing",
                }
            )

        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Error processing webhook: {str(e)}",
                }
            )
