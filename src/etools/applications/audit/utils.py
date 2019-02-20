from django.contrib.contenttypes.models import ContentType

from easy_pdf.rendering import render_to_pdf
from unicef_attachments.models import Attachment

from etools.applications.attachments.models import generate_file_path


def generate_final_report(obj, code, labels, pdf, template, filename):
    labels_serializer = labels(obj)
    pdf_serializer = pdf(obj)
    context = {
        'engagement': pdf_serializer.data,
        'serializer': labels_serializer,
    }

    content_type = ContentType.objects.get_for_model(obj)
    attachment, __ = Attachment.objects.get_or_create(
        code=code,
        content_type=content_type,
        object_id=obj.pk,
    )

    with open(generate_file_path(attachment, filename), "wb") as fp:
        fp.write(render_to_pdf(template, context))
    attachment.file = fp.name
    attachment.save()
