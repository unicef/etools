#!/usr/bin/env sh
set -ex

export PATH=/etools/__pypackages__/3.12/bin/:$PATH

# If set, use DJANGO_SETTINGS_MODULE from environment, except that we never want to use production settings
# for tests. In that case, fall back to local settings.
if [[ $DJANGO_SETTINGS_MODULE = '' || $DJANGO_SETTINGS_MODULE = etools.config.settings.production ]] ; then
    # Not set, or production; override and use local settings for tests
    export DJANGO_SETTINGS_MODULE=etools.config.settings.local
fi

# Ensure there are no errors.
python -W ignore manage.py check
python -W ignore manage.py makemigrations --dry-run --check

# Ensure translations are up-to-date.
cwd=$(pwd)
app_dirs="${cwd}/src/etools/applications/field_monitoring/data_collection/
          ${cwd}/src/etools/applications/field_monitoring/fm_settings/
          ${cwd}/src/etools/applications/field_monitoring/planning/
          ${cwd}/src/etools/applications/comments/
          ${cwd}/src/etools/applications/organizations/
          ${cwd}/src/etools/applications/partners/"
for app_dir in ${app_dirs};
do
    echo ${app_dir}
    cd ${app_dir}
    python ${cwd}/manage.py make-messages -a --no-location
    git diff --ignore-matching-lines=POT-Creation-Date --exit-code
done
cd ${cwd}

# Check code style unless running under tox, in which case tox runs flake8 separately
if [[ "$(echo "$RUNNING_UNDER_TOX")" != 1 ]] ; then
    time flake8 src/
    time isort src/ --check-only
fi

# Run unittests and coverage report
coverage erase
time coverage run manage.py test --noinput --keepdb "$@"
coverage report -m
coverage html
