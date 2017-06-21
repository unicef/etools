from __future__ import unicode_literals

from django.apps import AppConfig as BaseAppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = _('Auditor Portal')
