FROM python:3.7.5-alpine

RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories

RUN apk update
RUN apk add --upgrade apk-tools

RUN apk add \
    --update alpine-sdk

RUN apk add openssl \
    ca-certificates \
    libressl2.7-libcrypto
RUN apk add \
    libxml2-dev \
    libxslt-dev \
    xmlsec-dev
RUN apk add postgresql-dev \
    libffi-dev\
    jpeg-dev \
    python-dev \
    libmagic

RUN apk add --update-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/community/ \
    gdal \
    gdal-dev \
    geos \
    geos-dev

RUN apk add --update-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing/ \
    gcc \
    g++

RUN apk add bash

RUN pip install --upgrade \
    setuptools \
    pip \
    wheel \
    pipenv \
    tox

