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
    libgdal1h \
    libgdal1-dev \
    libxml2-dev \
    libxslt-dev \
    xmlsec1

RUN pip install virtualenv

# http://gis.stackexchange.com/a/74060
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal
ENV REQUIREMENTS_FILE production.txt
