import json
from urllib.parse import urljoin

from django.conf import settings
from django.db import connection
from django.urls import reverse

from etools_offline import OfflineCollect
from simplejson import JSONDecodeError

from etools.applications.field_monitoring.data_collection.offline.blueprint import (
    get_blueprint_code,
    get_blueprint_for_activity_and_method,
)
from etools.config.celery import app


@app.task
def create_offline_blueprint(activity_id, method_id, data_collectors):
    from etools.applications.field_monitoring.fm_settings.models import Method
    from etools.applications.field_monitoring.planning.models import MonitoringActivity

    activity = MonitoringActivity.objects.get(id=activity_id)
    method = Method.objects.get(id=method_id)

    # absolute host should be provided, so we have to add protocol to domain
    host = settings.HOST
    if not host.startswith('http'):
        host = 'https://' + host

    blueprint = get_blueprint_for_activity_and_method(activity, method)
    OfflineCollect().add(data={
        "is_active": True,
        "code": blueprint.code,
        "form_title": blueprint.title,
        "form_instructions": json.dumps(blueprint.to_dict(), indent=2),
        "accessible_by": data_collectors,
        "api_response_url": urljoin(
            host,
            '{}?workspace={}'.format(
                reverse(
                    'field_monitoring_data_collection:activities-offline',
                    args=[activity_id, method_id]
                ),
                connection.tenant.schema_name or ''
            )
        )
    })


@app.task
def update_offline_data_collectors_list(activity_id, method_id, data_collectors):
    from etools.applications.field_monitoring.fm_settings.models import Method
    from etools.applications.field_monitoring.planning.models import MonitoringActivity

    activity = MonitoringActivity.objects.get(id=activity_id)
    method = Method.objects.get(id=method_id)

    OfflineCollect().update(get_blueprint_code(activity, method), accessible_by=data_collectors)


@app.task
def close_offline_blueprint(activity_id, method_id):
    from etools.applications.field_monitoring.fm_settings.models import Method
    from etools.applications.field_monitoring.planning.models import MonitoringActivity

    activity = MonitoringActivity.objects.get(id=activity_id)
    method = Method.objects.get(id=method_id)

    # todo: at this moment we got jsondecodeerror event for .get, so we can't check safely blueprint existence
    try:
        OfflineCollect().delete(get_blueprint_code(activity, method))
    except JSONDecodeError:
        pass
