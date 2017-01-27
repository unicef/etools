from __future__ import unicode_literals

import logging

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from EquiTrack.celery import app

log = logging.getLogger(__name__)


@app.task
def import_travel_agents(xml_path):
    log.info('Try to open %s', xml_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    a = 12
