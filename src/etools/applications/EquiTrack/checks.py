import os

from django.core.checks import Error, register


def assert_isdir(path):
    if not os.path.isdir(path):
        raise OSError(1, "SAML configuration issue: path does not exists", path)


@register('etools')
def check_config(app_configs, **kwargs):
    from django.conf import settings
    errors = []
    try:
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
        __import__(settings.ROOT_URLCONF)
    except ImportError as e:
        errors.append(
            Error(
                str(e),
                hint='check your settings.ROOT_URLCONF',
                obj=None,
                id='etools.E002',
            )
        )

    # check templates
    for entry in settings.TEMPLATES:
        for path in entry['DIRS']:
            if not os.path.isdir(path):
                errors.append(
                    Error(
                        f"TEMPLATES: directory not found. ('{path}')",
                        hint='check your settings.TEMPLATES',
                        obj=None,
                        id='etools.E004',
                    )
                )
    return errors
