import random
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from apps.core import choices as core_choices
from apps.core.models import Address, Contact
from apps.customers.models import Account, Patient

fake = Faker()


class Command(BaseCommand):
    help = "Generates fake patients associated with existing accounts"

    def add_arguments(self, parser):
        parser.add_argument(
            "patients_per_account",
            type=int,
            help="Number of patients to create per account",
        )
        parser.add_argument(
            "--accounts",
            type=int,
            help="Number of accounts to process (default: all)",
            required=False,
        )

    def handle(self, *args, **kwargs):
        patients_per_account = kwargs["patients_per_account"]
        accounts_limit = kwargs.get("accounts")

        accounts = Account.objects.all()
        if accounts_limit:
            accounts = accounts[:accounts_limit]

        if not accounts.exists():
            self.stdout.write(
                self.style.ERROR(
                    "No accounts found. Please create accounts first using create_fake_accounts command."  # noqa
                )
            )
            return

        total_patients = len(accounts) * patients_per_account
        self.stdout.write(
            f"Creating {patients_per_account} patients for each of {len(accounts)} accounts "  # noqa
            f"(total: {total_patients} patients)..."
        )

        for account in accounts:
            self.create_patients_for_account(account, patients_per_account)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {total_patients} patients.")
        )

    def create_patients_for_account(self, account, count):
        """Create a specified number of patients for an account."""
        for _ in range(count):
            self.create_patient(account)

    def create_patient(self, account):
        """Create a single patient with associated address and contact info."""
        with transaction.atomic():
            address = Address.objects.create(
                street=fake.street_address(),
                city=fake.city(),
                state=fake.state(),
                zip_code=fake.zipcode(),
            )

            contact = Contact.objects.create(
                email=fake.email(),
                phone=fake.phone_number(),
            )

            birth_date = fake.date_between(
                start_date=date(1940, 1, 1), end_date=date(2005, 12, 31)
            )

            genders = [2, 3]
            races = [choice[0] for choice in core_choices.RACE_CHOICES]
            patient = Patient.objects.create(
                account=account,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                gender=random.choice(genders),
                race=random.choice(races),
                birth_date=birth_date,
                address=address,
                contact=contact,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created patient: {patient.full_name} for account: {account}"
                )
            )

            return patient
