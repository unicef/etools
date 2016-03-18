FROM unicef/etools:base

ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal
ENV PYTHONUNBUFFERED 1
RUN mkdir /code

ADD EquiTrack /code/
RUN pip install -r /code/requirements/production.txt

COPY frontend /code/frontend/
WORKDIR /code/frontend/
RUN sh /code/frontend/build.sh

WORKDIR /code/
ENV DJANGO_SETTINGS_MODULE EquiTrack.settings.production
RUN python manage.py collectstatic --noinput

# Start everything
ENV PORT 8080
ENV C_FORCE_ROOT true
CMD newrelic-admin run-program gunicorn EquiTrack.wsgi -b "0.0.0.0:$PORT" -w 4 --timeout=3200 --log-level debug
EXPOSE $PORT

