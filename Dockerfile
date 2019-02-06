FROM python:3.6.4-alpine as builder
# python:3.6.4-jessie has python 2.7 and 3.6 installed, and packages
# available to install 3.4

# Install dependencies
RUN echo "http://dl-3.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories
RUN apk update
RUN apk add --upgrade apk-tools

RUN apk add \
    --update alpine-sdk
RUN apk add \
    libxml2-dev \
    libxslt-dev \
    xmlsec-dev

RUN apk add postgresql-dev
RUN apk add libffi-dev
RUN apk add jpeg-dev

RUN pip install --upgrade \
    setuptools \
    pip \
    wheel \
    pipenv

RUN apk add openssl
RUN apk add ca-certificates
RUN apk add libressl2.7-libcrypto
RUN apk add gdal --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
RUN apk add gdal-dev --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
RUN apk add py-gdal --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
RUN apk add geos --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
RUN apk add geos-dev --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
RUN apk add gcc --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
RUN apk add g++ --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/

# http://gis.stackexchange.com/a/74060
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal

WORKDIR /etools/
ADD Pipfile .
ADD Pipfile.lock .
#ADD requirements.txt .

RUN pipenv install --system  --ignore-pipfile --deploy

RUN python -c "import os; print(os.__file__)"
#RUN python -m site
#RUN pip wheel --wheel-dir=/tmp/etwheels -r requirements.txt
#
FROM python:3.6.4-alpine

RUN echo "http://dl-3.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories
RUN apk update
RUN apk add --upgrade apk-tools
RUN apk add postgresql-client
RUN apk add openssl
RUN apk add ca-certificates
RUN apk add libressl2.7-libcrypto
RUN apk add gdal --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/

ADD src /code/
ADD manage.py /code/manage.py
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code
WORKDIR /code/

COPY --from=builder /usr/local/lib/python3.6/site-packages /usr/local/lib/python3.6/site-packages
#COPY --from=builder /tmp/etwheels /tmp/etwheels
#COPY --from=builder /etools/requirements.txt /code/requirements.txt
#RUN pip install --no-index --find-links=/tmp/etwheels -r /code/requirements.txt

#RUN rm -rf /tmp/etwheels

ENV DJANGO_SETTINGS_MODULE etools.config.settings.production
RUN SECRET_KEY=not-so-secret-key-just-for-collectstatic DISABLE_JWT_LOGIN=1 python manage.py collectstatic --noinput
