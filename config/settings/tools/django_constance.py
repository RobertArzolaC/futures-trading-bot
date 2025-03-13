from django.utils.translation import gettext_lazy as _

# Django Constance
# https://django-constance.readthedocs.io/en/latest/

CONSTANCE_FILE_ROOT = "constance"

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"

CONSTANCE_ADDITIONAL_FIELDS = {
    "image_field": ["django.forms.ImageField", {}],
    "json_field": ["django.forms.JSONField", {}],
}

CONSTANCE_CONFIG = {
    "LOGO_IMAGE": ("default.png", _("Company logo"), "image_field"),
    "JSON_FIELD_TEST": ({"name": "Robert"}, _("Test json field"), "json_field"),
    "ENABLE_SEND_EMAIL": (True, _("Enable sending emails.")),
    "ENABLE_VERIFICATION_EMAIL": (True, _("Enable email verification.")),
    "WEBSITE_DOMAIN": ("https://knowinglabs.com/", _("Website domain.")),
}

CONSTANCE_CONFIG_FIELDSETS = {
    "1. General Options": {
        "fields": (
            "LOGO_IMAGE",
            "JSON_FIELD_TEST",
            "WEBSITE_DOMAIN",
            "ENABLE_SEND_EMAIL",
            "ENABLE_VERIFICATION_EMAIL",
        ),
        "collapse": False,
    },
}
