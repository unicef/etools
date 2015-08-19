#!/usr/bin/env bash

pip install tutum
tutum service redeploy --sync web
tutum container exec web-1 python ./EquiTrack/manage.py syncdb --migrate