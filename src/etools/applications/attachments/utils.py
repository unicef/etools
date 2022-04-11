from django.db import connection


def get_filepath_prefix():
    return connection.schema_name


def get_file_type(obj):
    """If dealing with intervention attachment then use
    partner file type instead of attachment file type
    """
    from etools.applications.partners.models import InterventionAttachment
    from etools.applications.t2f.models import TravelAttachment

    if isinstance(obj.content_object, InterventionAttachment):
        return obj.content_object.type.name
    elif isinstance(obj.content_object, TravelAttachment):
        return obj.content_object.type
    elif obj.file_type:
        return obj.file_type.label
    return ""


def get_partner_obj(obj):
    """Try and get partner value"""
    from etools.applications.audit.models import Engagement
    from etools.applications.partners.models import (
        Agreement,
        AgreementAmendment,
        Assessment,
        CoreValuesAssessment,
        Intervention,
        InterventionAmendment,
        InterventionAttachment,
        PartnerOrganization,
    )
    from etools.applications.tpm.models import TPMActivity

    if isinstance(obj.content_object, PartnerOrganization):
        return obj.content_object
    elif isinstance(obj.content_object, (AgreementAmendment, Intervention)):
        return obj.content_object.agreement.partner
    elif isinstance(obj.content_object, (InterventionAmendment, InterventionAttachment)):
        return obj.content_object.intervention.agreement.partner
    elif isinstance(obj.content_object, (Agreement, Assessment, Engagement, TPMActivity, CoreValuesAssessment)):
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


def get_pd_ssfa(obj):
    """Only certain models will have this value available
    Intervention
    InterventionAttachment
    InterventionAmendment
    """
    from etools.applications.partners.models import Intervention, InterventionAmendment, InterventionAttachment
    from etools.applications.tpm.models import TPMActivity

    if isinstance(obj.content_object, Intervention):
        return obj.content_object
    elif isinstance(obj.content_object, (
            TPMActivity,
            InterventionAmendment,
            InterventionAttachment,
    )):
        if obj.content_object.intervention:
            return obj.content_object.intervention
    return ""


def get_content_obj(obj):
    """Not able to get specific agreement for partners, engagements,
    and assessments
    """
    from etools.applications.audit.models import Engagement
    from etools.applications.partners.models import (
        Agreement,
        AgreementAmendment,
        Intervention,
        InterventionAmendment,
        InterventionAttachment,
    )
    from etools.applications.psea.models import Assessment
    from etools.applications.tpm.models import TPMActivity

    if isinstance(obj.content_object, (Agreement, Engagement, Assessment)):
        return obj.content_object
    elif isinstance(obj.content_object, (AgreementAmendment, Intervention)):
        return obj.content_object.agreement
    elif isinstance(obj.content_object, (
            InterventionAmendment,
            InterventionAttachment,
            TPMActivity
    )):
        if obj.content_object.intervention:
            return obj.content_object.intervention.agreement
    return ""


def get_reference_number(obj):
    content_obj = get_content_obj(obj)
    if content_obj:
        return content_obj.reference_number
    return ""


def get_object_url(obj):
    try:
        return obj.content_object.get_object_url()
    except AttributeError:
        return ""


def get_source(obj):
    if obj.content_type:
        app_label = obj.content_type.app_label
        if app_label == "partners":
            return "Partnership Management Portal"
        elif app_label == "audit":
            return "Financial Assurance (FAM)"
        elif app_label == "tpm":
            return "Third Party Monitoring"
        elif app_label == "t2f":
            return "Trips"
        elif app_label == "psea":
            return "PSEA"
    return ""


def denormalize_attachment(attachment):
    from etools.applications.attachments.models import AttachmentFlat

    partner = get_partner(attachment)
    partner_type = get_partner_type(attachment)
    vendor_number = get_vendor_number(attachment)
    pd_ssfa = get_pd_ssfa(attachment)
    agreement_reference_number = get_reference_number(attachment)
    file_type = get_file_type(attachment)
    object_link = get_object_url(attachment)
    source = get_source(attachment)
    uploaded_by = attachment.uploaded_by.get_full_name() if attachment.uploaded_by else ""

    flat, created = AttachmentFlat.objects.update_or_create(
        attachment=attachment,
        defaults={
            "partner": partner,
            "partner_type": partner_type,
            "vendor_number": vendor_number,
            "pd_ssfa": pd_ssfa.pk if pd_ssfa else None,
            "pd_ssfa_number": pd_ssfa.number if pd_ssfa else "",
            "agreement_reference_number": agreement_reference_number,
            "object_link": object_link,
            "file_type": file_type,
            "file_link": attachment.file_link,
            "filename": attachment.filename,
            "uploaded_by": uploaded_by,
            "ip_address": attachment.ip_address,
            "source": source,
            "created": attachment.created,
        }
    )

    return flat
