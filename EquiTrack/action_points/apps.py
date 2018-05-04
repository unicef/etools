from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Action Points'

    def ready(self):
        from action_points import signals  # NOQA
