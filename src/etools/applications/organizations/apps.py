from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Organizations'
    default_auto_field = 'django.db.models.BigAutoField'
