import random
from decimal import Decimal

import factory
from django.utils import timezone

from apps.core import choices
from apps.customers import models
from apps.laboratory import choices as laboratory_choices
from apps.laboratory import models as laboratory_models
from apps.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "password123")


class AccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Account

    user = factory.SubFactory(UserFactory)
    parent_account = None
    is_organization = False
