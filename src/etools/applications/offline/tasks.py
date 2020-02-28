import re

from django.core.files.uploadedfile import SimpleUploadedFile

import requests
from unicef_attachments.models import Attachment

from etools.config.celery import app


@app.task
def download_remote_attachment(attachment_id, url):
    attachment = Attachment.objects.get(id=attachment_id)

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
