from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.customers import models


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name",)
    search_fields = ("user__first_name", "user__last_name",)
    autocomplete_fields = ["user"]
    exclude = ("is_removed",)
