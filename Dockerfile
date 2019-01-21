FROM python:3.6.4-jessie
# python:3.6.4-jessie has python 2.7 and 3.6 installed, and packages
# available to install 3.4

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
    python3-dev \
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
    pip \
    wheel \
    pipenv

# http://gis.stackexchange.com/a/74060
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal

ADD Pipfile.lock /
RUN pipenv install --system --deploy --ignore-pipfile

ENV PYTHONUNBUFFERED 1
ADD src /code/
ADD manage.py /code/manage.py 
ENV PYTHONPATH /code

WORKDIR /code/

ENV DJANGO_SETTINGS_MODULE etools.config.settings.production
RUN SECRET_KEY=not-so-secret-key-just-for-collectstatic DISABLE_JWT_LOGIN=1 python manage.py collectstatic --noinput
