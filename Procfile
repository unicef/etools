web: newrelic-admin run-program gunicorn EquiTrack.wsgi -b "0.0.0.0:$PORT" -w 4 --timeout=3200 --log-level debug
worker: newrelic-admin run-program python manage.py celery worker --loglevel=info
beater: newrelic-admin run-program python manage.py celery beat --loglevel=info