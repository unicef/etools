#!/usr/bin/env bash
set -ex

coverage erase
coverage run manage.py test --noinput --keepdb --settings=EquiTrack.settings.test "$@"
coverage report
