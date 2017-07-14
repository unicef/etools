from __future__ import unicode_literals

from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'TPM'

    def ready(self):
        from . import signals # NOQA
        from utils.permissions import signals as utils_signals
        utils_signals.prepare_permission_choices(self.get_models())
