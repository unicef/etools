#!/usr/bin/env bash
set -ex

TEST_SETTINGS="EquiTrack.settings.local"
# Use DJANGO_SETTINGS_MODULE from environment, except that we never want to use production settings
# for tests. In that case, fall back to local settings.
if [ "$DJANGO_SETTINGS_MODULE" != "EquiTrack.settings.production" ]; then
    TEST_SETTINGS=$DJANGO_SETTINGS_MODULE
fi

# Ensure there are no missing migrations
python manage.py makemigrations --dry-run  --settings="$TEST_SETTINGS" | grep 'No changes detected' || (echo 'There are changes which require migrations.' && exit 1)

# Run unittests and coverage report
coverage erase
coverage run manage.py test --noinput --keepdb --settings="$TEST_SETTINGS" "$@"
coverage report --include "$@/*.py"

# Check code style
flake8 .
