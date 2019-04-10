"""
A collection of functions which test the most basic operations of various services.
"""
from collections import namedtuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import cache
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
            db_conn.cursor()
            c_status = 'OK'
        except OperationalError:
            c_status = 'FAIL'
            connected = False
        status_str += "%s:%s " % (settings.DATABASES[db]['NAME'], c_status)

    a_user = get_user_model().objects.first()
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
    conn = celery.connection()
    if conn.connected:
        return ServiceStatus(True, 'Celery connected')
    else:
        return ServiceStatus(False, 'Celery unable to connect')


def check_redis():
    if 'redis' in settings.CACHES:
        import redis
        rc = cache.caches['redis']
        redis_api = redis.StrictRedis.from_url('%s' % rc._server)
        memory = redis_api.info()['used_memory_human']
        result = rc.set('serverup_check_key', 'test', timeout=5)
        return ServiceStatus(result, "Redis is up and using {} memory".format(memory))
    else:
        return ServiceStatus(False, "Redis is not configured on this system!")


CHECKS = {
    'db': check_db,
    'celery': check_celery,
    # 'redis': check_redis,
}
