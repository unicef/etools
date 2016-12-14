#!/usr/bin/env bash

coverage run EquiTrack/manage.py test EquiTrack --keepdb --settings=EquiTrack.settings.test
