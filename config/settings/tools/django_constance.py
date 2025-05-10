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
    "LOGO_IMAGE": ("default.png", _("Company default logo"), "image_field"),
    "DARK_LOGO_IMAGE": ("dark_logo.png", _("Company dark logo"), "image_field"),
    "JSON_FIELD_TEST": ({"name": "Robert"}, _("Test json field"), "json_field"),
    "WEBSITE_DOMAIN": ("https://knowinglabs.com/", _("Website domain.")),
    "ENABLE_TEST_MODE": (True, _("Enable test mode.")),
    "DUMMY_BALANCE_AMOUNT": (50000.00, _("Dummy balance amount.")),
}

CONSTANCE_CONFIG_FIELDSETS = {
    "1. General Options": {
        "fields": (
            "LOGO_IMAGE",
            "DARK_LOGO_IMAGE",
            "JSON_FIELD_TEST",
            "WEBSITE_DOMAIN",
        ),
        "collapse": False,
    },
    "2. Test Options": {
        "fields": (
            "ENABLE_TEST_MODE",
            "DUMMY_BALANCE_AMOUNT",
        ),
        "collapse": True,
    },
}
