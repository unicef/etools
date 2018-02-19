import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.http.response import HttpResponseRedirect
from django.template.response import SimpleTemplateResponse
from tenant_schemas.middleware import TenantMiddleware
from tenant_schemas.utils import get_public_schema_name

from EquiTrack.utils import set_country

logger = logging.getLogger(__name__)


class EToolsTenantMiddleware(TenantMiddleware):
    """
    Routes user to their correct schema based on country
    """
    def process_request(self, request):
        # Connection needs first to be at the public schema, as this is where
        # the tenant metadata is stored.
        connection.set_schema_to_public()

        if not request.user:
            return

        if any(x in request.path for x in [
                u'workspace_inactive']):
            return None

        if request.user.is_anonymous():
            # check if user is trying to reach an authentication endpoint
            if any(x in request.path for x in [
                u'api',
                u'login',
                u'saml',
                u'accounts',
                u'monitoring',
            ]):
                return None  # let them pass
            else:
                return HttpResponseRedirect(settings.LOGIN_URL)

        if request.user.is_superuser and not request.user.profile.country:
            return None

        if not request.user.is_superuser and \
                (not request.user.profile.country or
                 request.user.profile.country.business_area_code in settings.INACTIVE_BUSINESS_AREAS):
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
