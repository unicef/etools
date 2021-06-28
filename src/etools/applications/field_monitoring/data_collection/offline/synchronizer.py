from typing import List, TYPE_CHECKING

from django.conf import settings

from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.field_monitoring.data_collection.tasks import (
    close_offline_blueprint,
    create_offline_blueprint,
    update_offline_data_collectors_list,
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
        data_collectors = [self.activity.person_responsible.email]
        data_collectors += list(self.activity.team_members.values_list('email', flat=True))
        return data_collectors

    def initialize_blueprints(self) -> None:
        if not self.enabled:
            return

        for method in self.activity.methods:
            create_offline_blueprint.delay(self.activity.id, method.id, self._get_data_collectors())

    def update_data_collectors_list(self) -> None:
        if not self.enabled:
            return

        for method in self.activity.methods:
            update_offline_data_collectors_list.delay(self.activity.id, method.id, self._get_data_collectors())

    def close_blueprints(self) -> None:
        if not self.enabled:
            return

        for method in self.activity.methods:
            close_offline_blueprint.delay(self.activity.id, method.id)
