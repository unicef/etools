#!/usr/bin/env bash
set -ex

# Ensure there are no missing migrations
python manage.py makemigrations --dry-run | grep 'No changes detected' || (echo 'There are changes which require migrations.' && exit 1)

# Run unittests and coverage report
coverage erase
coverage run manage.py test --noinput --keepdb --settings=EquiTrack.settings.test "$@"
coverage report

# Check code style
flake8 .
