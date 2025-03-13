from allauth.account.models import EmailAddress
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from sesame.utils import get_query_string

from apps.users.forms import CustomUserChangeForm, CustomUserCreationForm
from apps.users.models import User


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_superuser",
        "is_staff",
        "is_active",
        "is_verified",
        "get_login_link",
    )
    list_filter = (
        "is_active",
        "is_staff",
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "avatar")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_superuser",
                    "is_staff",
                    "is_active",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)

    def is_verified(self, obj):
        email = EmailAddress.objects.filter(user=obj, primary=True).first()
        return email.verified if email else False

    is_verified.short_description = "Verified"
    is_verified.boolean = True

    def get_login_link(self, obj):
        if self.request.user.is_superuser:
            query_string = get_query_string(obj)
            base_domain = f"{self.request.scheme}://{self.request.get_host()}"
            url = f"{base_domain}{obj.get_absolute_url()}{query_string}"
            return format_html(
                '<button type="button" class="copy-link-btn" data-url="{}" '
                'onclick="copyToClipboard(this)" style="background-color: #79aec8; '
                'color: white; border: none; border-radius: 4px; padding: 5px 10px; cursor: pointer;">'  # noqa
                "Copy</button>",
                url,
            )
        return "Not available"

    get_login_link.short_description = "Magic Link"

    def get_queryset(self, request):
        self.request = request
        return super().get_queryset(request)


admin.site.register(User, CustomUserAdmin)
