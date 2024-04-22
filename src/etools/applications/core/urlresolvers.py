from functools import cached_property
from importlib import import_module

from django.conf import settings
from django.db import connection
from django.urls import include, reverse, URLPattern, URLResolver

from django_tenants.utils import get_tenant_model

from etools.libraries.pythonlib.urlresolvers import update_url_with_kwargs


def build_frontend_url(*parts, user=None):

    if not user or user.is_staff:
        frontend_url = '{}{}'.format(settings.HOST, reverse('main'))
    else:
        frontend_url = '{}{}'.format(settings.HOST, reverse('social:begin', kwargs={'backend': 'azuread-b2c-oauth2'}))

    if hasattr(connection, "tenant"):
        country_id = connection.tenant.id
    else:
        # Not sure why this was done this way.. keeping it because I might have missed something
        country_id = get_tenant_model().objects.get(schema_name=connection.schema_name).id,

    change_country_view = update_url_with_kwargs(
        reverse('users:country-change'),
        country=country_id,
        next='/'.join(map(str, ('',) + parts))
    )

    frontend_url = update_url_with_kwargs(frontend_url, next=change_country_view)

    return frontend_url


class DecoratedPatterns(object):
    """
    A wrapper for an urlconf that applies a decorator to all its views.
    Taken from https://github.com/twidi/django-decorator-include
    """
    def __init__(self, urlconf_module, decorators):
        self.urlconf = urlconf_module
        try:
            iter(decorators)
        except TypeError:
            decorators = [decorators]
        self.decorators = decorators

    def decorate_pattern(self, pattern):
        if isinstance(pattern, URLResolver):
            decorated = URLResolver(
                pattern.pattern,
                DecoratedPatterns(pattern.urlconf_module, self.decorators),
                pattern.default_kwargs,
                pattern.app_name,
                pattern.namespace,
            )
        else:
            callback = pattern.callback
            for decorator in reversed(self.decorators):
                callback = decorator(callback)
            decorated = URLPattern(
                pattern.pattern,
                callback,
                pattern.default_args,
                pattern.name,
            )
        return decorated

    @cached_property
    def urlpatterns(self):
        # urlconf_module might be a valid set of patterns, so we default to it.
        patterns = getattr(self.urlconf_module, 'urlpatterns', self.urlconf_module)
        return [self.decorate_pattern(pattern) for pattern in patterns]

    @cached_property
    def urlconf_module(self):
        if isinstance(self.urlconf, str):
            return import_module(self.urlconf)
        else:
            return self.urlconf

    @cached_property
    def app_name(self):
        return getattr(self.urlconf_module, 'app_name', None)


def decorator_include(decorators, arg, namespace=None):
    """
    Works like ``django.conf.urls.include`` but takes a view decorator
    or an iterable of view decorators as the first argument and applies them,
    in reverse order, to all views in the included urlconf.
    """
    if isinstance(arg, tuple) and len(arg) == 3 and not isinstance(arg[0], str):
        # Special case where the function is used for something like `admin.site.urls`, which
        # returns a tuple with the object containing the urls, the app name, and the namespace
        # `include` does not support this pattern (you pass directly `admin.site.urls`, without
        # using `include`) but we have to
        urlconf_module, app_name, namespace = arg
    else:
        urlconf_module, app_name, namespace = include(arg, namespace=namespace)
    return DecoratedPatterns(urlconf_module, decorators), app_name, namespace
