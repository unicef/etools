from import_export import resources

from partners.models import PartnerOrganization, PartnerType


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
