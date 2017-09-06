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
#packages needed for RTL text support for PDF generation
#RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
RUN apt-get install -y --no-install-recommends \
    libfreetype6 \
    libfontconfig1 \
    libxrender1 \
    libxext6 \
    #xorg \
    #libssl-dev \
    wkhtmltopdf

RUN pip install --upgrade \
    setuptools \
    pip \
    wheel \
    pdfkit

# http://gis.stackexchange.com/a/74060
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal
ENV REQUIREMENTS_FILE production.txt

ADD ./EquiTrack/requirements/*.txt /pip/
ADD ./EquiTrack/requirements/$REQUIREMENTS_FILE /pip/app_requirements.txt
RUN pip install -f /pip -r /pip/app_requirements.txt

ENV PYTHONUNBUFFERED 1
ADD EquiTrack /code/

WORKDIR /code/

ENV DJANGO_SETTINGS_MODULE EquiTrack.settings.production
RUN SECRET_KEY=not-so-secret-key-just-for-collectstatic python manage.py collectstatic --noinput

#overwrite wkhtmltopdf binary with a patched version with QT support
#ADD docker-entrypoint.sh /
#RUN chmod a+rx /docker-entrypoint.sh
#ENTRYPOINT ["/docker-entrypoint.sh"]

ADD ./bin/wkhtmltopdf-amd64 /usr/bin/wkhtmltopdf