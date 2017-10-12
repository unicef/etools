from import_export import resources

from partners.models import (
    PartnerOrganization,
    PartnerType,
    Agreement
)


class PartnerExport(resources.ModelResource):
    risk_rating = resources.Field()
    agreement_count = resources.Field()
    intervention_count = resources.Field()
    active_staff_members = resources.Field()

    class Meta:
        model = PartnerOrganization
        # TODO add missing fields:
        #   Blocked Flag (new property)
        #   Bank Info (just the number of accounts synced from VISION)
        fields = ('vendor_number', 'vision_synced', 'deleted_flag', 'name', 'short_name', 'alternate_id',
                  'alternate_name', 'partner_type', 'cso_type', 'shared_partner', 'address', 'email', 'phone_number',
                  'risk_rating', 'type_of_assessment', 'last_assessment_date', 'total_ct_cp', 'total_ct_cy',
                  'agreement_count', 'intervention_count', 'active_staff_members')
        export_order = fields

    def dehydrate_risk_rating(self, partner_organization):
        return partner_organization.rating

    def dehydrate_agreement_count(self, partner_organization):
        return partner_organization.agreements.count()

    def dehydrate_intervention_count(self, partner_organization):
        if partner_organization.partner_type == PartnerType.GOVERNMENT:
            return partner_organization.work_plans.count()
        intervention_count = 0
        # TODO: Nik revisit this... move this into a single query
        for agr in partner_organization.agreements.all():
            intervention_count += agr.interventions.count()
        return intervention_count

    def dehydrate_active_staff_members(self, partner_organization):
        return ', '.join([sm.get_full_name() for sm in partner_organization.staff_members.all()])


class AgreementExport(resources.ModelResource):
    reference_number = resources.Field()
    signed_by_partner = resources.Field()
    signed_by_unicef = resources.Field()
    authorized_officers = resources.Field()
    start_date = resources.Field()
    end_date = resources.Field()

    class Meta:
        model = Agreement
        # TODO add missing fields:
        #   Attached Signed Agreement Link
        #   Amendments (comma separated list of amended fields)
        fields = ('reference_number', 'partner__vendor_number', 'partner__name', 'partner__short_name',
                  'start_date', 'end_date', 'signed_by_partner', 'signed_by_partner_date',
                  'signed_by_unicef', 'signed_by_unicef_date', 'authorized_officers')
        export_order = fields

    def dehydrate_reference_number(self, agreement):
        return agreement.reference_number

    def dehydrate_signed_by_partner(self, agreement):
        if agreement.partner_manager:
            return agreement.partner_manager.get_full_name()
        return None

    def dehydrate_signed_by_unicef(self, agreement):
        if agreement.signed_by:
            return agreement.signed_by.get_full_name()
        return ''

    def dehydrate_authorized_officers(self, agreement):
        names = [ao.get_full_name() for ao in agreement.authorized_officers.all()]
        return ', '.join(names)

    def dehydrate_start_date(self, agreement):
        return agreement.start

    def dehydrate_end_date(self, agreement):
        return agreement.end
