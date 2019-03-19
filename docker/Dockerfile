FROM python:3.6.8-alpine3.8
ARG PIPENV_ARGS

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

#RUN apk add --no-cache --virtual .etools-run-deps \
#        postgresql-libs
#
#RUN apk add --no-cache --virtual .system-run-deps \
#        bash

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE etools.config.settings.production
ENV DATABASE_URL ""
ENV DATABASE_CONN ""
ENV RUN_MIGRATIONS "0"
ENV STATIC_ROOT /var/etools/static
ENV SECRET_KEY not-so-secret-key-just-for-setup
EXPOSE 8080

ADD . /code
WORKDIR /code

RUN set -ex \
    ls -al /code \
    && pip install pip pipenv --upgrade \
    && pipenv install --verbose --system --deploy --ignore-pipfile $PIPENV_ARGS \
    && pip3 install .

#RUN apk del .fetch-deps .build-deps .build-deps-edge .etools-build-deps \
#    && rm -rf /var/cache/apk/* \
#    && rm -fr /root/.cache/ \
#    && rm -fr /code \
#    && rm -fr /usr/include/
RUN find /usr/local/lib/python3.6/ -name *.pyc | xargs rm -f

FROM python:3.6.8-alpine3.8
COPY --from=0 /usr/local/lib/python3.6/ /usr/local/lib/python3.6/
COPY --from=0 /usr/local/bin /usr/local/bin

RUN adduser -S etools \
    && mkdir -p /var/etools/run /var/etools/static \
    && chown -R etools /var/etools/


RUN apk add --no-cache --virtual .postgis-rundeps-edge \
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
        binutils \
        geos \
        gdal \
        proj4


RUN apk add --no-cache --virtual .etools-run-deps \
        postgresql-libs

RUN apk add --no-cache --virtual .system-run-deps \
        bash

RUN  rm -rf /var/cache/apk/* \
    && rm -fr /root/.cache/ \
    && rm -fr /usr/include/

ADD docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ADD docker/wait-for-it.sh /usr/local/bin/wait-for-it.sh

ENTRYPOINT ["docker-entrypoint.sh"]
WORKDIR /var/etools/

USER etools

CMD ["etools"]
