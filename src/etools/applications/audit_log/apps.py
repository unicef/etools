from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = 'etools.applications.audit_log'
    verbose_name = 'Audit Log'
