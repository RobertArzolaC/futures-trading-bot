from allauth.account.models import EmailAddress
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from model_utils.models import SoftDeletableModel, TimeStampedModel

from apps.users.models import User


class Account(SoftDeletableModel, TimeStampedModel):
    user = models.OneToOneField(
        User,
        verbose_name=_("User"),
        on_delete=models.CASCADE,
        related_name="account",
    )

    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ("user__last_name", "user__first_name")

    def __str__(self):
        return self.user.get_full_name()

    @cached_property
    def full_name(self):
        return self.user.get_full_name()

    @cached_property
    def is_verified(self):
        return EmailAddress.objects.filter(user=self.user, verified=True).exists()
