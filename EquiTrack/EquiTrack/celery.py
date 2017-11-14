from __future__ import absolute_import

import json
import os

from django.conf import settings

import requests
from tenant_schemas_celery.app import CeleryApp

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EquiTrack.settings.production')

app = CeleryApp('EquiTrack')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task
def send_to_slack(message):
    if settings.SLACK_URL:
        requests.post(
            settings.SLACK_URL,
            data=json.dumps({'text': message})
        )
