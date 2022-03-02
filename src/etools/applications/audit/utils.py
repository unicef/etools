from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile

from easy_pdf.rendering import render_to_pdf
from unicef_attachments.models import Attachment, FileType, generate_file_path


def generate_final_report(obj, code, labels, pdf, template, filename):
    labels_serializer = labels(obj)
    pdf_serializer = pdf(obj)
    context = {
        'engagement': pdf_serializer.data,
        'serializer': labels_serializer,
    }

    content_type = ContentType.objects.get_for_model(obj)
    file_type, __ = FileType.objects.get_or_create(
        code=code,
        defaults={
            "label": code.replace("_", " ").title(),
            "name": code.replace("_", " "),
        }
    )
    if not file_type.group:
        file_type.group = []
    file_type.group.append(code)
    file_type.save(update_fields=['group'])

    attachment, __ = Attachment.objects.get_or_create(
        code=code,
        content_type=content_type,
        object_id=obj.pk,
        defaults={
            "file_type": file_type,
        }
    )

    file_path = generate_file_path(attachment, filename)
    attachment.file.save(
        file_path,
        ContentFile(render_to_pdf(template, context)),
    )
