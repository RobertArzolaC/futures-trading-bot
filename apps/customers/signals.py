from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.customers import models


@receiver(post_delete, sender=models.Account)
def remove_account_user(sender, instance, **kwargs):
    user = instance.user
    user.delete()
