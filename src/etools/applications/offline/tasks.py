import re

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

import requests
from unicef_attachments.models import Attachment

from etools.applications.users.models import Country
from etools.config.celery import app


@app.task
def download_remote_attachment(workspace, attachment_id, url):
    # attachments are tenant-wide, so we need to switch schema before searching
    ws = Country.objects.exclude(name__in=['Global']).get(schema_name=workspace)
    connection.set_tenant(ws)

    attachment = Attachment.objects.filter(id=attachment_id).first()
    if not attachment:
        return

    response = requests.get(url)
    if not (200 <= response.status_code < 300):
        raise Exception(f'Bad attachment url: {url}')

    filename_header = response.headers.get('content-disposition')
    if filename_header:
        filename = re.findall("filename=(.+)", filename_header)[0]
    else:
        filename = url.split('/')[-1].split('?')[0]

    attachment.file = SimpleUploadedFile(filename, response.content)
    attachment.save()
