from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.customers import factories, models


class TestAccountViews(TestCase):
    def setUp(self):
        """Set up test data."""
        self.user = factories.UserFactory()
        self.client.login(email=self.user.email, password="password123")

        # Create test accounts
        self.organization = factories.AccountFactory(is_organization=True)
        self.account = factories.AccountFactory()

        # Add permissions
        permissions = Permission.objects.filter(
            codename__in=[
                "view_account",
                "add_account",
                "change_account",
                "delete_account",
            ]
        )
        self.user.user_permissions.add(*permissions)

    def test_account_list_view(self):
        """Test account list view."""
        url = reverse("apps.customers:account_list")

        # Test with permissions
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "customers/account/list.html")
        self.assertEqual(response.context["entity_plural"], "Accounts")

        # Test without permissions
        self.user.user_permissions.remove(Permission.objects.get(codename="view_account"))
        response = self.client.get(url)
        self.assertContains(response, "Acceso denegado", status_code=200)

    def test_account_update_view(self):
        """Test account update."""
        url = reverse("apps.customers:account_update", args=[self.account.id])

        # Test GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "customers/account/form.html")
        self.assertEqual(response.context["entity"], "Account")

        # Test POST
        data = {
            "user": self.account.user.id,
            "is_organization": True,
            "first_name": "Test",
            "last_name": "User",
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse("apps.customers:account_list"))

        # Test without permissions
        self.user.user_permissions.remove(
            Permission.objects.get(codename="change_account")
        )
        response = self.client.get(url)
        self.assertContains(
            response, "Your user does not have permission", status_code=200
        )

    def test_account_delete_view(self):
        """Test account deletion."""
        url = reverse("apps.customers:account_delete", args=[self.account.id])

        # Test POST
        response = self.client.post(url)
        self.assertRedirects(response, reverse("apps.customers:account_list"))
        self.assertFalse(models.Account.objects.filter(id=self.account.id).exists())

        # Test without permissions
        self.user.user_permissions.remove(
            Permission.objects.get(codename="delete_account")
        )
        another_account = factories.AccountFactory()
        response = self.client.post(
            reverse("apps.customers:account_delete", args=[another_account.id])
        )
        self.assertContains(response, "Acceso denegado", status_code=200)

    def test_account_list_view_organization(self):
        """Test account list view for organization user."""
        self.user.account.is_organization = True
        self.user.account.save()

        url = reverse("apps.customers:account_list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(
            response.context["accounts"],
            models.Account.objects.filter(parent_account=self.user.account),
            transform=lambda x: x,
        )

    def test_account_create_view(self):
        """Test account creation."""
        url = reverse("apps.customers:account_create")

        # Test GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "customers/account/form.html")
        self.assertEqual(response.context["entity"], "Account")

        # Test POST
        data = {
            "user": factories.UserFactory().id,
            "is_organization": False,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse("apps.customers:account_list"))

        # Test without permissions
        self.user.user_permissions.remove(Permission.objects.get(codename="add_account"))
        response = self.client.get(url)
        self.assertContains(response, "Acceso denegado", status_code=200)
