from django.urls import path

from . import views

app_name = "apps.trading"

urlpatterns = [
    # Dashboard y vistas principales
    path("", views.dashboard, name="dashboard"),
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path("operations/", views.OperationListView.as_view(), name="operations"),
    path("signals/", views.SignalListView.as_view(), name="signals"),
    # Control del Bot
    path("bot/control/", views.BotControlView.as_view(), name="bot_control"),
    # Operaciones
    path(
        "operations/<int:pk>/",
        views.OperationDetailView.as_view(),
        name="operation_detail",
    ),
    path(
        "operations/manual/",
        views.ManualOperationView.as_view(),
        name="manual_operation",
    ),
    path(
        "operations/<int:pk>/close/",
        views.CloseOperationView.as_view(),
        name="close_operation",
    ),
    # API / Webhooks
    path("api/webhook/", views.WebhookReceiverView.as_view(), name="webhook"),
]
