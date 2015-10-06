FROM python:2.7
RUN apt-get update && apt-get -y install python-gdal gdal-bin libgdal-dev libgdal1h libgdal1-dev libxml2-dev libxslt-dev python-dev
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD EquiTrack /code/
RUN pip install -r requirements/production.txt
ENV DJANGO_SETTINGS_MODULE EquiTrack.settings.production
RUN python manage.py collectstatic --noinput
# Start everything
ENV PORT 8080
EXPOSE $PORT
ENV C_FORCE_ROOT true
CMD honcho start
