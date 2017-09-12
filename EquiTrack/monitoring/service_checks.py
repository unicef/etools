"""
A collection of functions which test the most basic operations of various services.
"""
from collections import namedtuple


from django.conf import settings
from django.contrib.auth.models import User
from django.db import connections
from django.db.utils import OperationalError
from celery import Celery


# much of this modeled from https://github.com/dimagi/commcare-hq/blob/master/corehq/apps/hqadmin/service_checks.py

ServiceStatus = namedtuple("ServiceStatus", "success message")


def check_db():
    connected = True
    status_str = ""
    for db in settings.DATABASES:
        db_conn = connections[db]
        try:
            c = db_conn.cursor()
            c_status = 'OK'
        except OperationalError:
            c_status = 'FAIL'
            connected = False
        status_str += "%s:%s " % (settings.DATABASES[db]['NAME'], c_status)

    a_user = User.objects.first()
    if a_user is None:
        status_str += "No users found in postgres"
    else:
        status_str += "Successfully got a user from postgres"

    if a_user is None or not connected:
        return ServiceStatus(False, status_str)
    return ServiceStatus(True, status_str)


def check_celery():
    celery = Celery()
    celery.config_from_object(settings)
    worker_responses = celery.control.ping(timeout=10)
    if not worker_responses:
        return ServiceStatus(False, 'No running Celery workers were found.')
    else:
        msg = 'Successfully pinged {} workers'.format(len(worker_responses))
        return ServiceStatus(True, msg)


CHECKS = {
    'db': check_db,
    'celery': check_celery,
}
