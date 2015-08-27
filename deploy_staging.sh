#!/usr/bin/env bash

#pip install tutum
CONTAINER_ID = "$(tutum service redeploy --sync web)"
tutum container exec "${CONTAINER_ID}" python ./EquiTrack/manage.py syncdb --migrate