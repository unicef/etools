import logging

from django.db import connection

from django_tenants.utils import get_tenant_model
from django.conf import settings
from unicef_vision.synchronizers import VisionDataSynchronizer

from etools.applications.vision.models import VisionSyncLog

logger = logging.getLogger(__name__)


class VisionDataTenantSynchronizer(VisionDataSynchronizer):
    LOGGER_CLASS = VisionSyncLog

    def __init__(self, business_area_code=None, *args, **kwargs):
        super().__init__(business_area_code, *args, **kwargs)
        self.country = get_tenant_model().objects.get(business_area_code=self.business_area_code)
        connection.set_tenant(self.country)

    def _get_kwargs(self):
        kwargs = super()._get_kwargs()
        kwargs.update({
            'url': settings.INSIGHT_URL,
            'headers': (('Ocp-Apim-Subscription-Key', settings.INSIGHT_SUB_KEY), )
        })
        return kwargs

    def logger_parameters(self):
        return {
            'handler_name': self.__class__.__name__,
            'business_area_code': self.business_area_code,
            'country': self.country
        }
