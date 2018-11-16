FROM python:3.7.1

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
    software-properties-common \
    python-setuptools
RUN apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    python-psycopg2
RUN apt-get install -y --no-install-recommends \
    python-gdal \
    gdal-bin \
    libgdal-dev \
    g++ \
    libxml2-dev \
    libxslt-dev \
    xmlsec1

RUN gdal-config --version
RUN pip install --upgrade \
    setuptools \
    pip \
    wheel

# http://gis.stackexchange.com/a/74060
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal
ENV REQUIREMENTS_FILE base.txt

ADD src/requirements/*.txt /pip/
ADD src/requirements/$REQUIREMENTS_FILE /pip/app_requirements.txt
RUN pip install -f /pip -r /pip/app_requirements.txt

ENV PYTHONUNBUFFERED 1
ADD src /code/
ADD manage.py /code/manage.py 
ENV PYTHONPATH /code

WORKDIR /code/

ENV DJANGO_SETTINGS_MODULE etools.config.settings.production
RUN SECRET_KEY=not-so-secret-key-just-for-collectstatic DISABLE_JWT_LOGIN=1 python manage.py collectstatic --noinput
