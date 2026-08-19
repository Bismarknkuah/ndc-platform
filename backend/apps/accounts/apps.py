from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "NDC Accounts & Roles"

    def ready(self):
        from apps.accounts import schema  # noqa: F401
