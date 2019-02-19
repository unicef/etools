#FROM python:3.6.4-alpine as builder
#
#RUN echo "http://dl-3.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories
#RUN apk update
#RUN apk add --upgrade apk-tools
#
#RUN apk add \
#    --update alpine-sdk
#
#RUN apk add openssl \
#    ca-certificates \
#    libressl2.7-libcrypto
#RUN apk add \
#    libxml2-dev \
#    libxslt-dev \
#    xmlsec-dev
#RUN apk add postgresql-dev \
#    libffi-dev\
#    jpeg-dev
#
#RUN apk add --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ \
#    gdal \
#    gdal-dev \
#    py-gdal \
#    geos \
#    geos-dev \
#    gcc \
#    g++
#
#RUN pip install --upgrade \
#    setuptools \
#    pip \
#    wheel \
#    pipenv
#
#WORKDIR /etools/
#ADD Pipfile .
#ADD Pipfile.lock .
#RUN pipenv install --system  --ignore-pipfile --deploy
#
#
#FROM python:3.6.4-alpine
#
#RUN echo "http://dl-3.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories
#RUN apk update
#RUN apk add --upgrade apk-tools
#RUN apk add postgresql-client
#RUN apk add openssl \
#    ca-certificates \
#    libressl2.7-libcrypto
#RUN apk add geos \
#    gdal --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
#
#ADD src /code/
#ADD manage.py /code/manage.py
#
#WORKDIR /code/
#
#COPY --from=builder /usr/local/lib/python3.6/site-packages /usr/local/lib/python3.6/site-packages
#
#ENV PYTHONUNBUFFERED 1
#ENV PYTHONPATH /code
#ENV DJANGO_SETTINGS_MODULE etools.config.settings.production
#RUN SECRET_KEY=not-so-secret-key-just-for-collectstatic DISABLE_JWT_LOGIN=1 python manage.py collectstatic --noinput

FROM python:3.6.8-alpine3.8

ARG BUILD_DATE
ARG PIPENV_ARGS
ARG VERSION
ARG DEVELOP

ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal

RUN apk add --no-cache --virtual .fetch-deps \
        curl \
        ca-certificates \
        openssl \
        tar

RUN apk add --no-cache --virtual .build-deps \
        autoconf \
        automake \
        pkgconf \
        gcc \
        g++ \
        json-c-dev \
        libtool \
        libxml2-dev \
        make \
        perl

RUN apk add --no-cache --virtual .build-deps-edge \
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
        proj4 \
        proj4-dev \
        protobuf-c \
        protobuf-c-dev \
        xf86bigfontproto-dev

#RUN apk add --no-cache --virtual .postgis-rundeps \
#        json-c

RUN apk add --no-cache --virtual .postgis-rundeps-edge \
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
        binutils \
        gdal-dev \
        geos-dev \
        geos \
        gdal \
        proj4

RUN apk add --no-cache --virtual .etools-build-deps \
        fontconfig-dev \
        freetype-dev \
        jpeg-dev \
        json-c \
        json-c-dev \
        lcms2 \
        lcms2-dev \
        libffi-dev \
        libjpeg-turbo-dev \
        libressl-dev \
        libx11 \
        libx11-dev \
        libxau-dev \
        libxcb \
        libxcb-dev \
        libxdmcp-dev \
        libxft \
        libxft-dev \
        libxrender-dev \
        linux-headers \
        musl-dev \
        nghttp2-libs \
        openjpeg-dev \
        postgresql-dev \
        python3-dev \
        sqlite-libs \
        tcl \
        tcl-dev \
        tiff-dev \
        tk-dev \
        zlib-dev

RUN apk add --no-cache --virtual .etools-run-deps \
        postgresql-libs

RUN apk add --no-cache --virtual .system-run-deps \
        bash

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE etools.config.settings.production

RUN mkdir -p /code
ADD . /code

WORKDIR /code
RUN pip install pip==18.0 pipenv --upgrade

RUN set -ex \
    ls -al /code \
    && pipenv install --verbose --system --deploy --ignore-pipfile $PIPENV_ARGS \
    && pip3 install .


EXPOSE 8080
RUN apk del .fetch-deps .build-deps .build-deps-edge .etools-build-deps
RUN rm -rf /var/cache/apk/* \
    rm -fr /root/.cache/ \
    rm -fr /code \
    rm -fr /usr/include/


RUN SECRET_KEY=not-so-secret-key-just-for-collectstatic \
    DISABLE_JWT_LOGIN=1 \
    django-admin collectstatic --noinput

RUN find /usr/local/lib/python3.6/ -name *.pyc | xargs rm -f
#    && rm -fr /usr/local/lib/python3.6/site-packages/tablib/packages/dbfpy/ \
#    && python -O -m compileall -fqb /usr/local/lib/python3.6/ \
#    && find /usr/local/lib/python3.6/ -name *.py | xargs rm -f


CMD ["newrelic-admin", "run-program", \
     "gunicorn", "etools.config.wsgi", \
     "-b", "0.0.0.0:8080", \
     "-w", "6", \
     "--max-requests", "100", \
     "--timeout", "3200", \
     "--log-level", "info"]
#newrelic-admin run-program gunicorn etools.config.wsgi -b 0.0.0.0:8080 -w 6 --max-requests 100 --timeout=3200 --log-level info

#ADD docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh
#
#RUN adduser -S datamart \
#    && mkdir -p /var/datamart \
#    && chown datamart /var/datamart/
#
#WORKDIR /var/datamart
#USER datamart
#
#ENTRYPOINT ["docker-entrypoint.sh"]
#
#CMD ["datamart"]
