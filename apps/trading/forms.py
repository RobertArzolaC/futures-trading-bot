from django import forms

from .models import TradingSettings


class TradingSettingsForm(forms.ModelForm):
    """Formulario para configuración de trading"""

    api_key = forms.CharField(
        widget=forms.PasswordInput(render_value=True), required=False
    )
    api_secret = forms.CharField(
        widget=forms.PasswordInput(render_value=True), required=False
    )

    class Meta:
        model = TradingSettings
        fields = [
            "api_key",
            "api_secret",
            "webhook_url",
            "investment_percentage",
            "leverage",
            "take_profit",
            "stop_loss",
            "symbol",
        ]
        widgets = {
            "investment_percentage": forms.NumberInput(
                attrs={"min": 1, "max": 100}
            ),
            "leverage": forms.NumberInput(attrs={"min": 1, "max": 125}),
            "take_profit": forms.NumberInput(attrs={"min": 1, "max": 1000}),
            "stop_loss": forms.NumberInput(attrs={"min": 1, "max": 100}),
        }


class ManualOperationForm(forms.Form):
    """Formulario para crear operaciones manuales"""

    DIRECTION_CHOICES = [
        ("long", "Long (Buy)"),
        ("short", "Short (Sell)"),
    ]

    symbol = forms.CharField(max_length=20)
    direction = forms.ChoiceField(choices=DIRECTION_CHOICES)
    investment_percentage = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=100,
        help_text="Percentage of available balance to invest",
    )
    leverage = forms.IntegerField(
        min_value=1, max_value=125, initial=25, help_text="Leverage multiplier"
    )
    take_profit = forms.IntegerField(
        min_value=1,
        max_value=1000,
        initial=25,
        help_text="Take profit percentage",
    )
    stop_loss = forms.IntegerField(
        min_value=1, max_value=100, initial=25, help_text="Stop loss percentage"
    )


class BotControlForm(forms.Form):
    """Formulario para control del bot"""

    ACTIONS = [
        ("start", "Start Bot"),
        ("stop", "Stop Bot"),
        ("restart", "Restart Bot"),
    ]

    action = forms.ChoiceField(choices=ACTIONS)
