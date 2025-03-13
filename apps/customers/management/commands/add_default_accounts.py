from io import BytesIO

import requests
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from PIL import Image

from apps.core.utils.images import get_random_user_image
from apps.customers.models import Account
from apps.users import choices as user_choices

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    help = "Generates fake data for accounts and related users"

    def add_arguments(self, parser):
        parser.add_argument(
            "total",
            type=int,
            help="Indicates the number of accounts to be created",
        )

    def handle(self, *args, **kwargs):
        total = kwargs["total"]
        self.stdout.write(f"Creating {total} accounts...")

        for _ in range(total):
            self.create_account()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {total} accounts with related users."
            )
        )

    def create_account(self):
        with transaction.atomic():
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = fake.email()
            password = "holamundo"

            user = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                user_type=user_choices.USER_TYPE_CHOICES[5][0],
                is_active=True,
            )
            user.set_password(password)

            self.add_user_avatar(user)
            user.save()

            account = Account.objects.create(user=user)

            EmailAddress.objects.get_or_create(
                user=user, email=user.email, primary=True, verified=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created account for user: {user.email} (password: {password})"
                )
            )

            return account

    def add_user_avatar(self, user):
        """Add a random avatar to the user."""
        try:
            image_url = get_random_user_image()
            response = requests.get(image_url)

            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img_io = BytesIO()
                img.save(img_io, format="JPEG", quality=85)

                file_name = f"avatar_{fake.uuid4()}.jpg"
                user.avatar.save(file_name, File(img_io), save=True)
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Could not add avatar for user {user.email}: {str(e)}"
                )
            )
