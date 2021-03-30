from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Field Monitoring Analyze'
    label = 'field_monitoring_analyze'
