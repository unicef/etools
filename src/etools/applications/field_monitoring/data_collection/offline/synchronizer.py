import json
from typing import List, TYPE_CHECKING
from urllib.parse import urljoin

from django.conf import settings
from django.db import connection
from django.urls import reverse

from etools_offline import OfflineCollect
from sentry_sdk import capture_exception
from simplejson import JSONDecodeError

from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.field_monitoring.data_collection.offline.blueprint import (
    get_blueprint_code,
    get_blueprint_for_activity_and_method,
)

if TYPE_CHECKING:
    from etools.applications.field_monitoring.planning.models import MonitoringActivity


class MonitoringActivityOfflineSynchronizer:
    """
    Interface to synchronize MonitoringActivity blueprints with etools offline collect backend.
    """

    # todo: move external api calls into celery tasks for better stability & speed improvement

    def __init__(self, activity: 'MonitoringActivity'):
        self.activity = activity
        self.enabled = not tenant_switch_is_active('fm_offline_sync_disabled') and settings.ETOOLS_OFFLINE_API

    def _get_data_collectors(self) -> List[str]:
        data_collectors = [self.activity.visit_lead.email]
        data_collectors += list(self.activity.team_members.values_list('email', flat=True))
        return data_collectors

    def initialize_blueprints(self) -> None:
        if not self.enabled:
            return

        # absolute host should be provided, so we have to add protocol to domain
        host = settings.HOST
        if not host.startswith('http'):
            host = 'https://' + host

        for method in self.activity.methods:
            blueprint = get_blueprint_for_activity_and_method(self.activity, method)
            try:
                OfflineCollect().add(data={
                    "is_active": True,
                    "code": blueprint.code,
                    "form_title": blueprint.title,
                    "form_instructions": json.dumps(blueprint.to_dict(), indent=2),
                    "accessible_by": self._get_data_collectors(),
                    "api_response_url": urljoin(
                        host,
                        '{}?workspace={}'.format(
                            reverse(
                                'field_monitoring_data_collection:activities-offline',
                                args=[self.activity.id, method.id]
                            ),
                            connection.tenant.schema_name or ''
                        )
                    )
                })
            except JSONDecodeError:
                capture_exception()

    def update_data_collectors_list(self) -> None:
        if not self.enabled:
            return

        for method in self.activity.methods:
            try:
                OfflineCollect().update(
                    get_blueprint_code(self.activity, method),
                    accessible_by=self._get_data_collectors()
                )
            except JSONDecodeError:
                capture_exception()

    def close_blueprints(self) -> None:
        if not self.enabled:
            return

        for method in self.activity.methods:
            code = get_blueprint_code(self.activity, method)

            # todo: at this moment we got jsondecodeerror event for .get, so we can't check safely blueprint existence
            try:
                OfflineCollect().delete(code)
            except JSONDecodeError:
                capture_exception()
