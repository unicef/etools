from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'TPM'

    def ready(self):
        from etools.applications.tpm import signals  # noqa
        from etools.applications.permissions import signals as permissions_signals

        permissions_signals.prepare_permission_choices(self.get_models())
