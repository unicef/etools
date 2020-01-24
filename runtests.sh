#!/usr/bin/env sh
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
    time isort -rc src/ --check-only
fi

first_tests=(etools.applications.action_points.tests etools.applications.activities.tests etools.applications.attachments.tests etools.applications.audit.tests etools.applications.core.tests etools.applications.environment.tests etools.applications.field_monitoring.tests)
second_tests=(etools.applications.firms.tests etools.applications.funds.tests etools.applications.hact.tests etools.applications.management.tests etools.applications.partners.tests etools.applications.permissions2.tests etools.applications.psea.tests)
third_tests=(etools.applications.publics.tests etools.applications.reports.tests etools.applications.t2f.tests etools.applications.tpm.tests etools.applications.users.tests etools.applications.vision.tests)
# Run unittests and coverage report
coverage erase
if [ $1 == "first_tests" ] ; then
    echo "running for partners"
    time coverage run manage.py test $first_tests --noinput --keepdb "$@"
elif [ $1 == "second_tests" ] ; then
    echo "running for monkeys"
    time coverage run manage.py test $second_tests --noinput --keepdb "$@"
elif [ $1 == "third_tests" ] ; then
    echo "running for others"
    time coverage run manage.py test $third_tests --noinput --keepdb "$@"
else
    echo "running for all"
    time coverage run manage.py test --noinput --keepdb "$@"
fi
coverage report -m
coverage html
