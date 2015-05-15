#!/usr/bin/env bash

pip install -r EquiTrack/requirements/test.txt

coverage run EquiTrack/manage.py test EquiTrack --settings=EquiTrack.settings.test