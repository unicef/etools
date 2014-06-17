from __future__ import absolute_import

from EquiTrack.celery import app
from post_office import mail


def send_mail(sender, template, variables, *recipients):
    mail.send(
        [recp for recp in recipients],
        sender,
        template=template,
        context=variables,
    )