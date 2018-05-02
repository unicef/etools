#!/usr/bin/env bash
set -ex

# If set, use DJANGO_SETTINGS_MODULE from environment, except that we never want to use production settings
# for tests. In that case, fall back to local settings.
if [[ $DJANGO_SETTINGS_MODULE = '' || $DJANGO_SETTINGS_MODULE = etools.config.settings.production ]] ; then
    # Not set, or production; override and use local settings for tests
    export DJANGO_SETTINGS_MODULE=etools.config.settings.local
fi

# Ensure there are no errors.
python -W ignore manage.py check
python -W ignore manage.py makemigrations --dry-run --check

# Check code style unless running under tox, in which case tox runs flake8 separately
if [[ $RUNNING_UNDER_TOX != 1 ]] ; then
    time flake8 src/
fi

# Run unittests and coverage report
coverage erase
time coverage run manage.py test --noinput --keepdb "$@"
coverage report -m

