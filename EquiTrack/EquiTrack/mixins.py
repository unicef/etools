"""
Project wide mixins for models and classes
"""
__author__ = 'jcranwellward'

from django.conf import settings
from django.db import connection
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http.response import HttpResponseRedirect
from rest_framework.exceptions import PermissionDenied

from tenant_schemas.middleware import TenantMiddleware
from tenant_schemas.utils import get_public_schema_name
from rest_framework_jwt.authentication import JSONWebTokenAuthentication


class AdminURLMixin(object):
    """
    Provides a method to get the admin link for the mixed in model
    """
    admin_url_name = 'admin:{app_label}_{model_name}_{action}'

    def get_admin_url(self):
        content_type = ContentType.objects.get_for_model(self.__class__)
        return reverse(self.admin_url_name.format(
            app_label=content_type.app_label,
            model_name=content_type.model,
            action='change'
        ), args=(self.id,))


class EToolsTenantMiddleware(TenantMiddleware):
    """
    Routes user to their correct schema based on country
    """
    def process_request(self, request):
        # Connection needs first to be at the public schema, as this is where
        # the tenant metadata is stored.
        connection.set_schema_to_public()

        if any(x in request.path for x in [
            u'api',
            u'login',
            u'saml',
        ]):
            return None
        elif request.user.is_anonymous():
            return HttpResponseRedirect(settings.LOGIN_URL)
        elif request.user.is_superuser and not request.user.profile.country:
            return None

        try:
            request.tenant = request.user.profile.country
            connection.set_tenant(request.tenant)
        except Exception as exp:
            raise self.TENANT_NOT_FOUND_EXCEPTION(
                'No country found for user {}'.format(request.user))

        # Content type can no longer be cached as public and tenant schemas
        # have different models. If someone wants to change this, the cache
        # needs to be separated between public and shared schemas. If this
        # cache isn't cleared, this can cause permission problems. For example,
        # on public, a particular model has id 14, but on the tenants it has
        # the id 15. if 14 is cached instead of 15, the permissions for the
        # wrong model will be fetched.
        ContentType.objects.clear_cache()

        # Do we have a public-specific urlconf?
        if hasattr(settings, 'PUBLIC_SCHEMA_URLCONF') and request.tenant.schema_name == get_public_schema_name():
            request.urlconf = settings.PUBLIC_SCHEMA_URLCONF


class EToolsTenantJWTAuthentication(JSONWebTokenAuthentication):
    """
    Handles setting the tenant after a JWT successful authentication
    """
    def authenticate(self, request):

        try:
            user, jwt_value = super(EToolsTenantJWTAuthentication, self).authenticate(request)
        except TypeError as exp:
            raise PermissionDenied(detail='No valid authentication provided')
        if not user.profile.country:
            raise PermissionDenied(detail='No country found for user')

        connection.set_tenant(user.profile.country)
        request.tenant = user.profile.country

        return user, jwt_value
