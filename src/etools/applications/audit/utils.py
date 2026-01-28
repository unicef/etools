from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _

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


def get_partner_contacted_display_progress_order():
    """
    Return the ordered progression of computed display statuses while Engagement.status == partner_contacted.

    This is derived from the existing Engagement.DISPLAY_STATUSES_DATES ordering (no new model constants).
    """
    # Import locally to avoid circular imports: models.py imports this module.
    from etools.applications.audit.models import Engagement

    order = []
    for st in Engagement.DISPLAY_STATUSES_DATES.keys():  # dict order is meaningful
        order.append(st)
        if st == Engagement.DISPLAY_STATUSES.comments_received_by_unicef:
            break
    return tuple(order)


def rollback_engagement_display_status(engagement, target_display_status: str) -> list[str]:
    """
    Roll back *computed* display status by clearing later milestone dates (Option A).

    Rules:
    - Only supported while FSM/db status is partner_contacted.
    - Forward moves are rejected (would require inventing dates).
    - If the required milestone date for the target stage is missing, reject (no guessing).
    - Returns list of model fields that were changed (for update_fields).
    """
    # Import locally to avoid circular imports: models.py imports this module.
    from etools.applications.audit.models import Engagement

    if engagement.status != Engagement.STATUSES.partner_contacted:
        raise ValidationError({
            'status': [_('Display status changes are only supported while status is "IP Contacted".')]
        })

    progress_order = get_partner_contacted_display_progress_order()
    if target_display_status not in progress_order:
        raise ValidationError({
            'status': [_('Unsupported display status: %(status)s') % {'status': target_display_status}]
        })

    current_display_status = getattr(engagement, 'displayed_status', Engagement.DISPLAY_STATUSES.partner_contacted)
    if current_display_status not in progress_order:
        current_display_status = Engagement.DISPLAY_STATUSES.partner_contacted

    current_idx = progress_order.index(current_display_status)
    target_idx = progress_order.index(target_display_status)

    if target_idx > current_idx:
        raise ValidationError({
            'status': [
                _('Cannot move status forward.')
            ]
        })

    # Derive "required date field" for target stage from the existing mapping.
    required_field = Engagement.DISPLAY_STATUSES_DATES.get(target_display_status)
    # For partner_contacted, we don't require partner_contacted_at to exist here (we only wipe other milestones).
    if target_display_status != Engagement.DISPLAY_STATUSES.partner_contacted and required_field:
        if getattr(engagement, required_field) is None:
            # Use model field verbose_name if available (more user friendly than raw field name).
            try:
                verbose = str(engagement._meta.get_field(required_field).verbose_name)
            except Exception:
                verbose = required_field
            raise ValidationError({
                'status': [
                    _('Cannot set status to %(status)s because the required date "%(field)s" is missing.') % {
                        'status': target_display_status,
                        'field': verbose,
                    }
                ]
            })

    changed_fields: list[str] = []
    # Clear later milestones (based on mapping order).
    for later_status in progress_order[target_idx + 1:]:
        field_name = Engagement.DISPLAY_STATUSES_DATES.get(later_status)
        # Do not clear partner_contacted_at when rolling back.
        if field_name and field_name != 'partner_contacted_at' and getattr(engagement, field_name) is not None:
            setattr(engagement, field_name, None)
            changed_fields.append(field_name)

    return changed_fields
