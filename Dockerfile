ARG  BASE_TAG=latest_prod
FROM unicef/etools-base:$BASE_TAG

#### CLEANUP

RUN apk del .build-deps

ADD src /code/
ADD manage.py /code/manage.py

WORKDIR /code/

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /code
ENV DJANGO_SETTINGS_MODULE etools.config.settings.production

RUN SECRET_KEY=not-so-secret-key-just-for-collectstatic DISABLE_JWT_LOGIN=1 python manage.py collectstatic --noinput
