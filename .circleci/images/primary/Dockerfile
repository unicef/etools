FROM python:2.7

# Install dependencies
RUN apt-get update -qq
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
    python-setuptools \
    python3.4 \
    python3.4-dev \
    python3.4-venv \
    python3-pip \
    libpython3.4-dev
RUN apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    python-psycopg2 \
    python3-psycopg2
RUN apt-get install -y --no-install-recommends \
    python-gdal \
    gdal-bin \
    libgdal-dev \
    libgdal1h \
    libgdal1-dev \
    libxml2-dev \
    libxslt-dev \
    xmlsec1

RUN pip --quiet install --upgrade \
    setuptools \
    pip \
    wheel

RUN pip3 --quiet install --upgrade \
    setuptools \
    pip \
    wheel

# http://gis.stackexchange.com/a/74060
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal
ENV REQUIREMENTS_FILE production.txt
