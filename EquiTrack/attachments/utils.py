from partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    PartnerOrganization,
)


def get_file_type(obj):
    """If dealing with intervention attachment then use
    partner file type instead of attachement file type
    """
    if isinstance(obj.content_object, InterventionAttachment):
        return obj.content_object.type.name
    return obj.file_type.label


def get_partner_obj(obj):
    """Try and get partner value"""
    if isinstance(obj.content_object, PartnerOrganization):
        return obj.content_object
    elif isinstance(obj.content_object, (AgreementAmendment, Intervention)):
        return obj.content_object.agreement.partner
    elif isinstance(obj.content_object, (InterventionAmendment, InterventionAttachment)):
        return obj.content_object.intervention.agreement.partner
    elif isinstance(obj.content_object, (Agreement, Assessment)):
        return obj.content_object.partner
    return ""


def get_partner(obj):
    partner = get_partner_obj(obj)
    if partner:
        return partner.name
    return ""


def get_vendor_number(obj):
    """Try and get partner value, from there get vendor number"""
    partner = get_partner_obj(obj)
    if partner:
        return "" if partner.vendor_number is None else partner.vendor_number
    return ""


def get_partner_type(obj):
    partner = get_partner_obj(obj)
    if partner:
        return "" if partner.partner_type is None else partner.partner_type
    return ""


def get_pd_ssfa_number(obj):
    """Only certain models will have this value available
    Intervention
    InterventionAttachment
    InterventionAmendment
    """
    if isinstance(obj.content_object, Intervention):
        return obj.content_object.number
    elif isinstance(obj.content_object, (InterventionAmendment, InterventionAttachment)):
        return obj.content_object.intervention.number
    return ""


def denormalize_attachment(attachment):
    from attachments.models import AttachmentFlat

    partner = get_partner(attachment)
    partner_type = get_partner_type(attachment)
    vendor_number = get_vendor_number(attachment)
    pd_ssfa_number = get_pd_ssfa_number(attachment)
    file_type = get_file_type(attachment)
    uploaded_by = attachment.uploaded_by if attachment.uploaded_by else ""

    flat, created = AttachmentFlat.objects.update_or_create(
        attachment=attachment,
        defaults={
            "partner": partner,
            "partner_type": partner_type,
            "vendor_number": vendor_number,
            "pd_ssfa_number": pd_ssfa_number,
            "file_type": file_type,
            "file_link": attachment.file_link,
            "uploaded_by": uploaded_by,
            "created": attachment.created.strftime("%d %b %Y"),
        }
    )

    return flat
