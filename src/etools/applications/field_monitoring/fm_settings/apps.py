
from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Field Monitoring Settings'
    label = 'field_monitoring_settings'
