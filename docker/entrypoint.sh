#!/bin/bash -e


if [[ "$*" == "worker" ]];then
    celery worker -A etools.config.celery --loglevel=DEBUG --concurrency=4 --purge --pidfile run/celery.pid
elif [[ "$*" == "beater" ]];then
    celery beat -A etools.config.celery --loglevel=DEBUG --pidfile run/celerybeat.pid
elif [[ "$*" == "web" ]];then
    if [[ -n "${DATABASE_CONN}" ]];then
        wait-for-it.sh $DATABASE_CONN -t 30
        if [[ "${RUN_MIGRATIONS}" == "1" ]];then
            django-admin migrate
        fi
    fi
    django-admin collectstatic --noinput
    newrelic-admin run-program gunicorn etools.config.wsgi -b 0.0.0.0:8080 -w 6 --max-requests 100 --timeout=3200 --log-level info
else
    exec "$@"
fi
