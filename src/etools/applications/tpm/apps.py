
from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'TPM'

    def ready(self):
        from etools.applications.tpm import signals  # NOQA
        from etools.applications.utils.permissions import signals as utils_signals

        utils_signals.prepare_permission_choices(self.get_models())
