from __future__ import absolute_import

from EquiTrack.celery import app


@app.task
def process_trips():
    #TODO: Actually process trips:
    # 1. Upcoming trips (for supervisor and traveller)
    # 2. Overdue reports
    return "Processing"