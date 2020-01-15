import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.http.response import HttpResponseRedirect
from django.template.response import SimpleTemplateResponse
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from django_tenants.middleware import TenantMainMiddleware
from django_tenants.utils import get_public_schema_name

from etools.libraries.tenant_support.utils import set_country

logger = logging.getLogger(__name__)

ANONYMOUS_ALLOWED_URL_FRAGMENTS = [
    'api',
    'social',
    'login',
    'accounts',
    'monitoring',
]

INACTIVE_WORKSPACE_URL = reverse('workspace-inactive')


class QueryCountDebugMiddleware(MiddlewareMixin):
    """ Debug db connections"""
    def process_response(self, request, response):
        if response.status_code == 200:
            total_time = 0

            for query in connection.queries:
                query_time = query.get('time')
                if query_time is None:
                    # django-debug-toolbar monkeypatches the connection
                    # cursor wrapper and adds extra information in each
                    # item in connection.queries. The query time is stored
                    # under the key "duration" rather than "time" and is
                    # in milliseconds, not seconds.
                    query_time = query.get('duration', 0) / 1000
                total_time += float(query_time)

            print('%s queries run, total %s seconds' % (len(connection.queries), total_time))
            for q in connection.queries:
                print(q['time'])
        return response
    pass

class EToolsTenantMiddleware(TenantMainMiddleware):
    """
    Sets request.tenant based on the users's country (Tenant) and sets the DB connection to use that tenant.

    Allows the following types of requests to pass without trying to set the tenant:
    * requests without a user
    * requests by anonymous users to a URL with a fragment matching ANONYMOUS_ALLOWED_URL_FRAGMENTS.
    * requests by superusers without a country

    Other requests are either redirected to login, or to the INACTIVE_WORKSPACE_URL.
    """

    def process_request(self, request):
        # Connection needs first to be at the public schema, as this is where
        # the tenant metadata is stored.
        connection.set_schema_to_public()

        if not request.user:
            return None

        if INACTIVE_WORKSPACE_URL in request.path:
            return None

        if request.user.is_anonymous:
            # check if user is trying to reach an authentication endpoint
            if any(fragment in request.path
                   for fragment in ANONYMOUS_ALLOWED_URL_FRAGMENTS):
                return None  # let them pass
            else:
                return HttpResponseRedirect(settings.LOGIN_URL)

        if request.user.is_superuser and not request.user.profile.country:
            return None

        if not request.user.is_superuser and (
                not request.user.profile.country or request.user.profile.country.business_area_code in settings.INACTIVE_BUSINESS_AREAS):
            return HttpResponseRedirect("/workspace_inactive/")

        try:
            set_country(request.user, request)
        except Exception:
            logger.info('No country found for user {}'.format(request.user))
            return SimpleTemplateResponse('no_country_found.html', {'user': request.user})

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
