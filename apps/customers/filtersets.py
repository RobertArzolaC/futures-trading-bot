import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.customers import models


class AccountFilter(django_filters.FilterSet):
    name_search = django_filters.CharFilter(method="filter_by_name", label=_("Search"))
    is_active = django_filters.ChoiceFilter(
        field_name="user__is_active",
        empty_label=_("Active"),
        label=_("Status"),
        choices=(
            (True, _("Active")),
            (False, _("Inactive")),
        ),
    )
    is_organization = django_filters.ChoiceFilter(
        field_name="is_organization",
        empty_label=_("Organization"),
        label=_("Organization"),
        choices=(
            (True, _("Yes")),
            (False, _("No")),
        ),
    )

    class Meta:
        model = models.Account
        fields = ["name_search", "is_active", "is_organization"]

    def filter_by_name(self, queryset, name, value):
        return queryset.filter(
            Q(user__first_name__icontains=value)  # noqa
            | Q(user__last_name__icontains=value)  # noqa
            | Q(user__email__icontains=value)  # noqa
        )
