__author__ = 'jcranwellward'

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from collections import OrderedDict

from import_export import resources

from EquiTrack.utils import BaseExportResource
from .models import (
    PCA,
    PartnerOrganization,
    PartnershipBudget,
    AmendmentLog
)

class PartnerResource(resources.ModelResource):

    class Meta:
        model = PartnerOrganization


class PCAResource(BaseExportResource):

    class Meta:
        model = PCA

    def fill_pca_grants(self, row, pca):

        for num, grant in enumerate(pca.pcagrant_set.all()):
            num += 1
            values = OrderedDict()

            self.insert_column(values, 'Donor {}'.format(num), grant.grant.donor.name)
            self.insert_column(values, 'Grant {}'.format(num), grant.grant.name)
            self.insert_column(values, 'Amount {}'.format(num), grant.funds)

            insert_after = 'Amount {}'.format(num-1)
            insert_after = insert_after if insert_after in row else 'Total budget'

            self.insert_columns_inplace(row, values, insert_after)
        return row

    def fill_sector_outputs(self, row, sector):
        sector_name = sector.sector.name
        for num, output in enumerate(sector.pcasectoroutput_set.all()):
            num += 1
            values = OrderedDict()

            self.insert_column(values, '{} RRP output {}'.format(sector_name, num), output.output.name)

            last_field = '{} RRP output {}'.format(sector_name, num-1)
            insert_after = last_field if last_field in row else 'NULL'

            self.insert_columns_inplace(row, values, insert_after)

        return row

    def fill_sector_goals(self, row, sector):
        sector_name = sector.sector.name
        for num, goal in enumerate(sector.pcasectorgoal_set.all()):
            num += 1
            values = OrderedDict()

            self.insert_column(values, '{} CCC {}'.format(sector_name, num), goal.goal.name)

            last_field = '{} CCC {}'.format(sector_name, num-1)
            insert_after = last_field if last_field in row else 'NULL'

            self.insert_columns_inplace(row, values, insert_after)

        return row

    def fill_sector_indicators(self, row, sector):
        sector_name = sector.sector.name
        for num, indicator in enumerate(sector.indicatorprogress_set.all()):
            num += 1
            values = OrderedDict()

            self.insert_column(values, '{} Indicator {}'.format(sector_name, num), indicator.indicator.name)
            self.insert_column(values, '{} Unit {}'.format(sector_name, num), indicator.unit())
            self.insert_column(values, '{} Total Beneficiaries {}'.format(sector_name, num), indicator.programmed)
            self.insert_column(values, '{} Current Beneficiaries {}'.format(sector_name, num), indicator.current)
            self.insert_column(values, '{} Shortfall of Beneficiaries {}'.format(sector_name, num), indicator.shortfall())

            last_field = '{} Shortfall of Beneficiaries {}'.format(sector_name, num-1)
            insert_after = last_field if last_field in row else 'NULL'

            self.insert_columns_inplace(row, values, insert_after)

        return row

    def fill_sector_wbs(self, row, sector):
        sector_name = sector.sector.name
        wbs_set = set()
        for ir in sector.pcasectorimmediateresult_set.all():
            for wbs in ir.wbs_activities.all():
                wbs_set.add(wbs.name)

        for num, wbs in enumerate(wbs_set):
            num += 1
            values = OrderedDict()

            self.insert_column(values, '{} WBS/Activity {}'.format(sector_name, num), wbs)

            last_field = '{} WBS/Activity {}'.format(sector_name, num-1)
            insert_after = last_field if last_field in row else 'NULL'

            self.insert_columns_inplace(row, values, insert_after)

        return row

    def fill_sector_activities(self, row, sector):
        sector_name = sector.sector.name
        for num, activity in enumerate(sector.pcasectoractivity_set.all()):
            num += 1
            values = OrderedDict()

            self.insert_column(values, '{} Activity {}'.format(sector_name, num), activity.activity.name)

            last_field = '{} Activity {}'.format(sector_name, num-1)
            insert_after = last_field if last_field in row else 'NULL'

            self.insert_columns_inplace(row, values, insert_after)

        return row

    def fill_pca_locations(self, row, pca):

        for num, location in enumerate(pca.locations.all()):
            num += 1

            self.insert_column(row, 'Locality {}'.format(num), location.locality.name)
            self.insert_column(row, 'Location Type {}'.format(num), location.gateway.name)
            self.insert_column(row, 'Location Name {}'.format(num), location.location.name)

        return row

    def fill_budget(self, row, pca):

        unicef_cash = 0
        in_kind = 0
        partner_contribution = 0
        total = 0

        try:
            budget = pca.budget_log.latest('created')
            unicef_cash = budget.unicef_cash
            in_kind = budget.in_kind_amount
            partner_contribution = budget.partner_contribution
            total = budget.total
        except PartnershipBudget.DoesNotExist:
            pass

        self.insert_column(row, 'Partner contribution budget', partner_contribution)
        self.insert_column(row, 'Unicef cash budget', unicef_cash)
        self.insert_column(row, 'In kind amount budget', in_kind)
        self.insert_column(row, 'Total budget', total)

        return row

    def fill_pca_row(self, row, pca):

        try:
            amendment = pca.amendments_log.latest('created')
        except AmendmentLog.DoesNotExist:
            amendment = None

        self.insert_column(row, 'ID', pca.id)
        self.insert_column(row, 'Number', pca.reference_number)
        self.insert_column(row, 'Partner Organisation', pca.partner.name)
        self.insert_column(row, 'Title', pca.title)
        self.insert_column(row, 'Sectors', pca.sector_names)
        self.insert_column(row, 'Status', pca.status)
        self.insert_column(row, 'Created date', pca.created_at)
        self.insert_column(row, 'Initiation Date', pca.initiation_date.strftime("%d-%m-%Y") if pca.initiation_date else '')
        self.insert_column(row, 'Submission Date to PRC', pca.submission_date)
        self.insert_column(row, 'Review date by PRC', pca.review_date)
        self.insert_column(row, 'Signed by unicef date', pca.signed_by_unicef_date.strftime("%d-%m-%Y") if pca.signed_by_unicef_date else '')
        self.insert_column(row, 'Signed by partner date', pca.signed_by_partner_date.strftime("%d-%m-%Y") if pca.signed_by_partner_date else '')
        self.insert_column(row, 'Start Date', pca.start_date.strftime("%d-%m-%Y") if pca.start_date else '')
        self.insert_column(row, 'End Date', pca.end_date.strftime("%d-%m-%Y") if pca.end_date else '')
        self.insert_column(row, 'Amendment number', amendment.amendment_number if amendment else 0)
        self.insert_column(row, 'Amendment status', amendment.status if amendment else '')
        self.insert_column(row, 'Amended at', amendment.amended_at if amendment else '')
        self.insert_column(row, 'Unicef mng first name', pca.unicef_manager.first_name if pca.unicef_manager else '')
        self.insert_column(row, 'Unicef mng last name', pca.unicef_manager.last_name if pca.unicef_manager else '')
        self.insert_column(row, 'Unicef mng email', pca.unicef_manager.email if pca.unicef_manager else '')
        self.insert_column(row, 'Partner mng first name', pca.partner_manager.first_name if pca.partner_manager else '')
        self.insert_column(row, 'Partner mng last name', pca.partner_manager.last_name if pca.partner_manager else '')
        self.insert_column(row, 'Partner mng email', pca.partner_manager.email if pca.partner_manager else '')

        return row

    def fill_row(self, pca, row):
        """
        Controls the order in which fields are exported
        """

        self.fill_pca_row(row, pca)
        self.fill_budget(row,pca)
        # self.fill_pca_grants(row, pca)

        # for sector in sorted(pca.pcasector_set.all()):
        #
        #     self.fill_sector_outputs(row, sector)
        #     self.fill_sector_goals(row, sector)
        #     self.fill_sector_indicators(row, sector)
        #     self.fill_sector_wbs(row, sector)
        #     self.fill_sector_activities(row, sector)


class PartnerExport(resources.ModelResource):
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

    def dehydrate_active_staff_members(self, partner_organization):
        return ', '.join([sm.get_full_name() for sm in partner_organization.staff_members])

    def dehydrate_agreement_count(self, partner_organization):
        return partner_organization.agreements.count()

    def dehydrate_intervention_count(self, partner_organization):
        return partner_organization.work_plans.count()
