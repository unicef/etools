from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Field Monitoring Planning'
    label = 'field_monitoring_planning'

    def ready(self):
        from etools.applications.field_monitoring.planning import signals  # noqa
