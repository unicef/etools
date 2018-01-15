#!/usr/bin/env bash
set -ex

TEST_SETTINGS=${DJANGO_SETTINGS_MODULE:-EquiTrack.settings.local}
# Use DJANGO_SETTINGS_MODULE from environment, except that we never want to use production settings
# for tests. In that case, fall back to local settings.
if [ "TEST_SETTINGS" = "EquiTrack.settings.production" ]; then
    TEST_SETTINGS=EquiTrack.settings.local
fi

# Ensure there are no missing migrations. If there are, show what they are.
python manage.py makemigrations --dry-run --settings="$TEST_SETTINGS" >mig.out
grep 'No changes detected' mig.out || (cat mig.out; rm mig.out; echo 'There are changes which require migrations.';  exit 1)
rm mig.out

# Run unittests and coverage report
coverage erase
time coverage run manage.py test --noinput --keepdb --settings="$TEST_SETTINGS" "$@"
coverage report -m

# Check code style
time flake8 --config .flake8
