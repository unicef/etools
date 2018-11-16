FROM python:3.7.1

# Install dependencies
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    build-essential \
    libcurl4-openssl-dev \
    libjpeg-dev \
    vim \
    ntp \
    git-core
RUN apt-get install -y --no-install-recommends \
    python-pip \
    postgresql-client \
    libpq-dev \
    python3-dev
RUN apt-get install -y --no-install-recommends \
    python-gdal \
    gdal-bin \
    libgdal-dev \
    libxml2-dev \
    libxslt-dev \
    xmlsec1

RUN pip install virtualenv

# http://gis.stackexchange.com/a/74060
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal
ENV REQUIREMENTS_FILE base.txt
