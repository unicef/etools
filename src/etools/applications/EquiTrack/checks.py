# -*- coding: utf-8 -*-

from django.core.checks import Error, register


@register()
def check_config(app_configs, **kwargs):
    errors = []
    try:
        from django.conf import settings
        __import__(".".join(settings.WSGI_APPLICATION.split(".")[:-1]))
    except ImportError as e:
        errors.append(
            Error(
                str(e),
                hint='check your settings.WSGI_APPLICATION',
                obj=None,
                id='etools.E001',
            )
        )
    try:
        from django.conf import settings
        __import__(settings.ROOT_URLCONF)
    except ImportError as e:
        errors.append(
            Error(
                str(e),
                hint='check your settings.ROOT_URLCONF',
                obj=None,
                id='etools.E001',
            )
        )
    return errors
