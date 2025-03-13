from django.db.models import Q


def get_filtered_queryset(queryset, user, account_field="account"):
    if user.is_staff or user.is_superuser:
        return queryset

    if user.is_account:
        if user.account.is_organization:
            return queryset.filter(
                Q(**{f"{account_field}__parent_account": user.account})  # noqa
                | Q(**{account_field: user.account})  # noqa
            )
        return queryset.filter(**{account_field: user.account})
    return queryset.none()
