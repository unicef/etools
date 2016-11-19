FROM python:2.7



# Install dependencies
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    build-essential \
    libcurl4-openssl-dev \
    libjpeg-dev \
    vim \
    ntp \
    libpq-dev
RUN apt-get install -y --no-install-recommends \
    git-core
RUN apt-get install -y --no-install-recommends \
    python-dev \
    python-software-properties \
    python-setuptools
RUN apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    python-psycopg2
RUN apt-get install -y --no-install-recommends \
    python-gdal \
    gdal-bin \
    libgdal-dev \
    libgdal1h \
    libgdal1-dev \
    libxml2-dev \
    libxslt-dev \
    xmlsec1

RUN pip install --upgrade \
    setuptools \
    virtualenv \
    virtualenvwrapper \
    fabric \
    pip \
    wheel

# http://gis.stackexchange.com/a/74060
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal
ENV PYTHONUNBUFFERED 1
ENV REQUIREMENTS_FILE production.txt

ADD EquiTrack /code/
ADD ./EquiTrack/requirements/*.txt /pip/
ADD ./EquiTrack/requirements/$REQUIREMENTS_FILE /pip/app_requirements.txt
RUN pip install -f /pip -r /pip/app_requirements.txt

WORKDIR /code/
ENV DJANGO_SETTINGS_MODULE EquiTrack.settings.production
RUN python manage.py collectstatic --noinput
