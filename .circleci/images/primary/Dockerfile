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
    python-setuptools
RUN apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    python-psycopg2 \
    python2.7-dev \
    python3.4-dev
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
    wheel

# Make sure we have what we need when it comes time to build python-gdal in our venvs

# THIS: is way overkill - debian installs everything it would need to build all of GDAL,
# over 100 packages
#COPY jessie-src.list /etc/apt/sources.list.d/jessie-src.list
#RUN apt-get updaqte -qq && apt-get build-dep python-gdal python3-gdal -y

# So, hand-curate the list of things we actually need
RUN apt-get install -qy  \
    libogdi3.2-dev \
    python-dev \
    python3-dev

# http://gis.stackexchange.com/a/74060
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal
ENV REQUIREMENTS_FILE production.txt

# Warm the pip cache
RUN python3 -m venv /tmpvenv && /tmpvenv/bin/pip install GDAL==1.10.0 && rm -rf /tmpvenv

# Prebuild wheels for requirements for testing?
#RUN pip install
#RUN mkdir /wheels && pip wheel --wheel-dir=/wheels GDAL==1.10.0
