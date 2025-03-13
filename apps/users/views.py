from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, View

from apps.customers import forms as customer_forms
from apps.users import forms


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "users/profile.html"
    paginate_by = 6

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entity"] = _("Profile")
        context["back_url"] = reverse_lazy("apps.dashboard:index")

        return context


class SettingsView(SuccessMessageMixin, LoginRequiredMixin, View):
    template_name = "users/settings.html"
    success_message = _("Settings updated successfully")
    success_url = reverse_lazy("apps.users:settings")

    def get_context_data(self, **kwargs):
        user = self.request.user

        context = {
            "entity": _("Settings"),
            "back_url": reverse_lazy("apps.dashboard:index"),
            "user_form": forms.UserSettingsForm(instance=user),
        }

        if user.is_account:
            context["account_form"] = customer_forms.AccountSettingsForm(
                instance=user.account
            )

        context.update(kwargs)
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        try:
            user = request.user

            user_form = forms.UserSettingsForm(request.POST, request.FILES, instance=user)
            if user_form.is_valid():
                user_form.save()

            if user.is_account:
                customer_form = customer_forms.AccountSettingsForm(
                    request.POST, request.FILES, instance=user.account
                )

                if customer_form.is_valid():
                    customer_form.save()

            messages.success(request, self.success_message)
            return redirect(self.success_url)
        except Exception as e:
            messages.error(request, f"Error updating settings: {str(e)}")

        return render(request, self.template_name, self.get_context_data())
