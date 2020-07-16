import logging

from django.db import connection

from django_tenants.utils import get_tenant_model
from unicef_vision.synchronizers import VisionDataSynchronizer

from etools.applications.vision.models import VisionSyncLog

logger = logging.getLogger(__name__)


class VisionDataTenantSynchronizer(VisionDataSynchronizer):
    LOGGER_CLASS = VisionSyncLog

    def __init__(self, detail=None, business_area_code=None, *args, **kwargs):
        super().__init__(detail, business_area_code, *args, **kwargs)
        if business_area_code:
            self.country = get_tenant_model().objects.get(business_area_code=self.business_area_code)
            connection.set_tenant(self.country)

    def logger_parameters(self):
        kwargs = super().logger_parameters()
        kwargs['country'] = self.country
        return kwargs
