from etools.applications.audit.models import Engagement
from etools.applications.partners.models import (Agreement, AgreementAmendment, Assessment, Intervention,
                                                 InterventionAmendment, InterventionAttachment, PartnerOrganization,)
from etools.applications.tpm.models import TPMActivity


def get_file_type(obj):
    """If dealing with intervention attachment then use
    partner file type instead of attachment file type
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
    elif isinstance(obj.content_object, (Agreement, Assessment, Engagement, TPMActivity)):
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
    if partner and hasattr(partner, "partner_type"):
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
    elif isinstance(obj.content_object, (
            TPMActivity,
            InterventionAmendment,
            InterventionAttachment,
    )):
        return obj.content_object.intervention.number if obj.content_object.intervention else ""
    return ""


def get_agreement_obj(obj):
    """Not able to get specific agreement for partners, engagements,
    and assessments
    """
    if isinstance(obj.content_object, (Agreement)):
        return obj.content_object
    elif isinstance(obj.content_object, (AgreementAmendment, Intervention)):
        return obj.content_object.agreement
    elif isinstance(obj.content_object, (
            InterventionAmendment,
            InterventionAttachment,
            TPMActivity
    )):
        return obj.content_object.intervention.agreement if obj.content_object.intervention else None
    return ""


def get_agreement_reference_number(obj):
    agreement = get_agreement_obj(obj)
    if agreement:
        return agreement.reference_number
    return ""


def denormalize_attachment(attachment):
    from etools.applications.attachments.models import AttachmentFlat

    partner = get_partner(attachment)
    partner_type = get_partner_type(attachment)
    vendor_number = get_vendor_number(attachment)
    pd_ssfa_number = get_pd_ssfa_number(attachment)
    agreement_reference_number = get_agreement_reference_number(attachment)
    file_type = get_file_type(attachment)
    uploaded_by = attachment.uploaded_by.get_full_name() if attachment.uploaded_by else ""

    flat, created = AttachmentFlat.objects.update_or_create(
        attachment=attachment,
        defaults={
            "partner": partner,
            "partner_type": partner_type,
            "vendor_number": vendor_number,
            "pd_ssfa_number": pd_ssfa_number,
            "agreement_reference_number": agreement_reference_number,
            "file_type": file_type,
            "file_link": attachment.file_link,
            "filename": attachment.filename,
            "uploaded_by": uploaded_by,
            "created": attachment.created.strftime("%d %b %Y"),
        }
    )

    return flat
