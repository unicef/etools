# -*- coding: utf-8 -*-
import os

from django.core.checks import Error, register


def assert_isdir(path):
    if not os.path.isdir(path):
        raise OSError(f"SAML configuration issue.'{path}' does not exists")


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

    configdir = settings.SAML_CONFIG['attribute_map_dir']
    if not os.path.isdir(configdir):
        errors.append(
            Error(
                "SAML configuration directory not found. ('attribute_map_dir')",
                hint='check your settings.SAML_CONFIG',
                obj=None,
                id='etools.E003',
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


@register('etools', deploy=True)
def check_config_deploy(app_configs, **kwargs):
    from django.conf import settings
    errors = []
    cfg = settings.SAML_CONFIG

    for i, filename in enumerate(cfg['metadata']['local']):
        if not os.path.exists(filename):
            errors.append(
                Error(
                    f"SAML configuration error.'{filename}' does not exists",
                    hint='check your settings.SAML_CONFIG',
                    obj=None,
                    id=f'etools.E001{i}',
                )
            )

    for i, filename in enumerate([cfg['key_file'], cfg['cert_file']]):
        if not os.path.exists(filename):
            errors.append(
                Error(
                    f"SAML configuration error.'{filename}' does not exists",
                    hint='check your settings.SAML_CONFIG',
                    obj=None,
                    id=f'etools.E002{i}',
                )
            )

    for i, entry in enumerate(cfg['encryption_keypairs']):
        for k, v in entry.items():
            if not os.path.exists(v):
                errors.append(
                    Error(
                        f"Error in SAML configuration in entry [encryption_keypairs][{k}]. '{v}' does not exists  ",
                        hint='check your settings.SAML_CONFIG',
                        obj=None,
                        id=f'etools.E003{i}',
                    )
                )
    return errors
