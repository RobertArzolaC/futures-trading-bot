from allauth.account.models import EmailAddress
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from apps.users.models import User


class Command(BaseCommand):
    help = "Generates default users including superuser and staff users"

    def handle(self, *args, **kwargs):
        # Definir usuarios
        superuser_data = {
            "email": "admin@example.com",
            "first_name": "Administrator",
            "is_staff": True,
            "is_superuser": True,
        }

        staff_users_data = [
            {
                "email": "staff1@example.com",
                "first_name": "Laboratory",
                "last_name": "Manager",
                "is_staff": True,
            },
            {
                "email": "staff2@example.com",
                "first_name": "Results",
                "last_name": "Validator",
                "is_staff": True,
            },
            {
                "email": "staff3@example.com",
                "first_name": "Quality",
                "last_name": "Control",
                "is_staff": True,
            },
            {
                "email": "staff4@example.com",
                "first_name": "Test",
                "last_name": "Supervisor",
                "is_staff": True,
            },
            {
                "email": "staff5@example.com",
                "first_name": "Reports",
                "last_name": "Manager",
                "is_staff": True,
            },
        ]

        default_password = "qaz.123"
        users_created = 0
        users_existed = 0

        # Crear superusuario
        superuser = self.create_user(superuser_data, default_password)
        if superuser:
            users_created += 1
            self.stdout.write(
                self.style.SUCCESS(f"Superuser created successfully: {superuser.email}")
            )
        else:
            users_existed += 1
            self.stdout.write(
                self.style.WARNING(f"Superuser already exists: {superuser_data['email']}")
            )

        # Crear usuarios staff
        for staff_data in staff_users_data:
            staff_user = self.create_user(staff_data, default_password)
            if staff_user:
                users_created += 1
                # Asignar permisos específicos para usuarios staff
                self.assign_staff_permissions(staff_user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Staff user created successfully: {staff_user.email}"
                    )
                )
            else:
                users_existed += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Staff user already exists: {staff_data['email']}"
                    )
                )

        # Resumen final
        self.stdout.write(
            self.style.SUCCESS(
                f"\nProcess completed:\n"
                f"- Users created: {users_created}\n"
                f"- Users already existed: {users_existed}\n"
                f"- Total users processed: {users_created + users_existed}"
            )
        )

    def create_user(self, user_data, password):
        """
        Crea un usuario si no existe
        Retorna el usuario creado o None si ya existía
        """
        email = user_data.pop("email")

        # Verificar si el usuario ya existe
        user = User.objects.filter(email=email).first()
        if not user:
            # Crear nuevo usuario
            user = User.objects.create_user(email=email, password=password, **user_data)

            # Crear y verificar email
            EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                primary=True,
                verified=True,
            )
            return user

        return None

    def assign_staff_permissions(self, user):
        """
        Asigna permisos específicos a usuarios staff
        """
        # Permisos para gestionar resultados
        result_permissions = Permission.objects.filter(
            codename__in=[
                "add_orderresult",
                "change_orderresult",
                "view_orderresult",
                "add_medicaltestresult",
                "change_medicaltestresult",
                "view_medicaltestresult",
            ]
        )
        user.user_permissions.add(*result_permissions)

        # Permisos para gestionar pruebas médicas
        medical_test_permissions = Permission.objects.filter(
            codename__in=[
                "view_medicaltest",
                "view_panel",
                "view_order",
            ]
        )
        user.user_permissions.add(*medical_test_permissions)

        # Permisos para gestionar pacientes
        patient_permissions = Permission.objects.filter(
            codename__in=[
                "view_patient",
                "view_account",
            ]
        )
        user.user_permissions.add(*patient_permissions)
