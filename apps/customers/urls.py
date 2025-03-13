from django.urls import path

from apps.customers import views

app_name = "apps.customers"

urlpatterns = [
    # Accounts URLs
    path("accounts/", views.AccountListView.as_view(), name="account_list"),
    path(
        "accounts/create/",
        views.AccountCreateView.as_view(),
        name="account_create",
    ),
    path(
        "accounts/update/<int:pk>/",
        views.AccountUpdateView.as_view(),
        name="account_update",
    ),
    path(
        "accounts/<int:pk>/delete/",
        views.AccountDeleteView.as_view(),
        name="account_delete",
    ),
]
