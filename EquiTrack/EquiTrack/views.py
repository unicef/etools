from django.views.generic import TemplateView
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class MainView(TemplateView):
    template_name = 'choose_login.html'


class OutdatedBrowserView(TemplateView):
    template_name = 'outdated_browser.html'


class PublicTenantMixin(object):
    """
    This mixin protect returns an empty queryset for the tenant apps when in the public schema.
    It avoid problems relation does not exist.
    It is supposed to be used only for tenant models.
    """

    def get_queryset(self):
        if connection.schema_name == 'public':
            logger.warning(''.format(self.serializer_class.Meta.model))
            return self.serializer_class.Meta.model.objects.none()
        return self.serializer_class.Meta.model.objects.all()
