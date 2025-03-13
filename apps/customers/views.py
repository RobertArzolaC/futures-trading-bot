from constance import config
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, UpdateView
from django_filters.views import FilterView

from apps.core import mixins as core_mixins
from apps.customers import filtersets, forms, models


class AccountListView(
    PermissionRequiredMixin, FilterView, LoginRequiredMixin, SuccessMessageMixin
):
    model = models.Account
    permission_required = "customers.view_account"
    filterset_class = filtersets.AccountFilter
    template_name = "customers/account/list.html"
    context_object_name = "accounts"
    paginate_by = 5

    def get_queryset(self):
        if self.request.user.is_organization:
            return models.Account.objects.filter(parent_account=self.request.user.account)
        return models.Account.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["config"] = config
        context["entity"] = _("Account")
        context["entity_plural"] = _("Accounts")
        context["back_url"] = reverse_lazy("apps.dashboard:index")
        context["add_entity_url"] = reverse_lazy("apps.customers:account_create")

        return context


class AccountCreateView(
    PermissionRequiredMixin, FormView, LoginRequiredMixin, SuccessMessageMixin
):
    form_class = forms.AccountCreationForm
    permission_required = "customers.add_account"
    template_name = "customers/account/form.html"
    success_message = _("Account created successfully")
    success_url = reverse_lazy("apps.customers:account_list")

    def form_valid(self, form):
        form.save(self.request)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entity"] = _("Account")
        context["back_url"] = reverse_lazy("apps.customers:account_list")
        return context


class AccountUpdateView(
    PermissionRequiredMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = models.Account
    context_object_name = "account"
    form_class = forms.AccountUpdateForm
    template_name = "customers/account/form.html"
    permission_required = "customers.change_account"
    success_message = _("Account updated successfully")
    success_url = reverse_lazy("apps.customers:account_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entity"] = _("Account")
        context["back_url"] = reverse_lazy("apps.customers:account_list")
        return context


class AccountDeleteView(core_mixins.AjaxDeleteViewMixin):
    model = models.Account
