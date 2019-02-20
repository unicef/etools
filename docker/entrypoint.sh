#!/bin/bash -e


if [[ "$*" == "workers" ]];then
    celery worker -A etools.config.celery --loglevel=DEBUG --concurrency=4 --purge --pidfile run/celery.pid
elif [[ "$*" == "beat" ]];then
    celery beat -A etools.config.celery --loglevel=DEBUG --pidfile run/celerybeat.pid
elif [[ "$*" == "etools" ]];then
    django-admin collectstatic --noinput
    newrelic-admin run-program gunicorn etools.config.wsgi -b 0.0.0.0:8080 -w 6 --max-requests 100 --timeout=3200 --log-level info
else
    exec "$@"
fi
