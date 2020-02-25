import json
from typing import List

from django.conf import settings
from django.db import connection
from django.urls import reverse

from etools_offline import OfflineCollect
from simplejson import JSONDecodeError

from etools.applications.field_monitoring.data_collection.offline.blueprint import (
    get_blueprint_code,
    get_blueprint_for_activity_and_method,
)
from etools.applications.field_monitoring.planning.models import MonitoringActivity


class MonitoringActivityOfflineSynchronizer:
    # todo: move external api calls into celery tasks for better stability & speed improvement

    def __init__(self, activity: MonitoringActivity):
        self.activity = activity
        self.enabled = settings.ETOOLS_OFFLINE_ENABLED

    def _get_data_collectors(self) -> List[str]:
        data_collectors = [self.activity.person_responsible.email]
        data_collectors += list(self.activity.team_members.values_list('email', flat=True))
        return data_collectors

    def initialize_blueprints(self) -> None:
        if not self.enabled:
            return

        for method in self.activity.methods:
            blueprint = get_blueprint_for_activity_and_method(self.activity, method)
            OfflineCollect().add(data={
                "is_active": True,
                "code": blueprint.code,
                "form_title": blueprint.title,
                "form_instructions": json.dumps(blueprint.to_dict(), indent=2),
                "accessible_by": self._get_data_collectors(),
                "api_response_url": '{}{}?workspace={}'.format(
                    settings.HOST,
                    reverse('field_monitoring_data_collection:activities-offline', args=[self.activity.id, method.id]),
                    connection.tenant.schema_name or ''
                )
            })

    def update_data_collectors_list(self) -> None:
        if not self.enabled:
            return

        for method in self.activity.methods:
            OfflineCollect().update(
                get_blueprint_code(self.activity, method),
                accessible_by=self._get_data_collectors()
            )

    def close_blueprints(self) -> None:
        if not self.enabled:
            return

        for method in self.activity.methods:
            code = get_blueprint_code(self.activity, method)

            # todo: at this moment we got jsondecodeerror event for .get, so we can't check safely blueprint existence
            try:
                OfflineCollect().delete(code)
            except JSONDecodeError:
                pass
