__author__ = 'jcranwellward'

import tablib

from collections import OrderedDict
from django.utils.datastructures import SortedDict

from import_export import resources

from partners.models import PCA


class PCAResource(resources.ModelResource):

    headers = []

    def insert_column(self, row, field_name, value):

        row[field_name] = value if self.headers else ''

    def insert_columns_inplace(self, row, fields, after_column):

        keys = row.keys()
        before_column = None
        if after_column in row:
            index = keys.index(after_column)
            offset = index + 1
            if offset < len(row):
                before_column = keys[offset]

        for key, value in fields.items():
            if before_column:
                row.insert(offset, key, value)
                offset += 1
            else:
                row[key] = value

    def fill_pca_grants(self, row, pca):

        for num, grant in enumerate(pca.pcagrant_set.all()):
            num += 1
            values = SortedDict()

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
            values = SortedDict()

            self.insert_column(values, '{} RRP output {}'.format(sector_name, num), output.output.name)

            last_field = '{} RRP output {}'.format(sector_name, num-1)
            insert_after = last_field if last_field in row else 'NULL'

            self.insert_columns_inplace(row, values, insert_after)

        return row

    def fill_sector_goals(self, row, sector):
        sector_name = sector.sector.name
        for num, goal in enumerate(sector.pcasectorgoal_set.all()):
            num += 1
            values = SortedDict()

            self.insert_column(values, '{} CCC {}'.format(sector_name, num), goal.goal.name)

            last_field = '{} CCC {}'.format(sector_name, num-1)
            insert_after = last_field if last_field in row else 'NULL'

            self.insert_columns_inplace(row, values, insert_after)

        return row

    def fill_sector_indicators(self, row, sector):
        sector_name = sector.sector.name
        for num, indicator in enumerate(sector.indicatorprogress_set.all()):
            num += 1
            values = SortedDict()

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
            values = SortedDict()

            self.insert_column(values, '{} WBS/Activity {}'.format(sector_name, num), wbs)

            last_field = '{} WBS/Activity {}'.format(sector_name, num-1)
            insert_after = last_field if last_field in row else 'NULL'

            self.insert_columns_inplace(row, values, insert_after)

        return row

    def fill_sector_activities(self, row, sector):
        sector_name = sector.sector.name
        for num, activity in enumerate(sector.pcasectoractivity_set.all()):
            num += 1
            values = SortedDict()

            self.insert_column(values, '{} Activity {}'.format(sector_name, num), activity.activity.name)

            last_field = '{} Activity {}'.format(sector_name, num-1)
            insert_after = last_field if last_field in row else 'NULL'

            self.insert_columns_inplace(row, values, insert_after)

        return row

    def fill_pca_locations(self, row, pca):

        for num, location in enumerate(pca.locations.all()):
            num += 1

            self.insert_column(row, 'Locality {}'.format(num), location.locality.name)
            self.insert_column(row, 'Gateway Type {}'.format(num), location.gateway.name)

        return row

    def fill_pca_row(self, row, pca):

        self.insert_column(row, 'Sectors', pca.sectors)
        self.insert_column(row, 'Number', pca.number)
        self.insert_column(row, 'Amendment', 'Yes' if pca.amendment else 'No')
        self.insert_column(row, 'Amendment date', pca.amended_at.strftime("%d-%m-%Y") if pca.amended_at else '')
        self.insert_column(row, 'Title', pca.title)
        self.insert_column(row, 'Partner Organisation', pca.partner.name)
        self.insert_column(row, 'Initiation Date', pca.initiation_date.strftime("%d-%m-%Y") if pca.initiation_date else '')
        self.insert_column(row, 'Status', pca.status)
        self.insert_column(row, 'Start Date', pca.start_date.strftime("%d-%m-%Y") if pca.start_date else '')
        self.insert_column(row, 'End Date', pca.end_date.strftime("%d-%m-%Y") if pca.end_date else '')
        self.insert_column(row, 'Signed by unicef date', pca.signed_by_unicef_date.strftime("%d-%m-%Y") if pca.signed_by_unicef_date else '')
        self.insert_column(row, 'Signed by partner date', pca.signed_by_partner_date.strftime("%d-%m-%Y") if pca.signed_by_partner_date else '')
        self.insert_column(row, 'Unicef mng first name', pca.unicef_mng_first_name)
        self.insert_column(row, 'Unicef mng last name', pca.unicef_mng_last_name)
        self.insert_column(row, 'Unicef mng email', pca.unicef_mng_email)
        self.insert_column(row, 'Partner mng first name', pca.partner_mng_first_name)
        self.insert_column(row, 'Partner mng last name', pca.partner_mng_last_name)
        self.insert_column(row, 'Partner mng email', pca.partner_mng_email)
        self.insert_column(row, 'Partner contribution budget', pca.partner_contribution_budget)
        self.insert_column(row, 'Unicef cash budget', pca.unicef_cash_budget)
        self.insert_column(row, 'In kind amount budget', pca.in_kind_amount_budget)
        self.insert_column(row, 'Total budget', pca.total_cash)

        return row

    def fill_row(self, pca, row):

        self.fill_pca_row(row, pca)
        self.fill_pca_grants(row, pca)

        for sector in sorted(pca.pcasector_set.all()):

            self.fill_sector_outputs(row, sector)
            self.fill_sector_goals(row, sector)
            self.fill_sector_indicators(row, sector)
            self.fill_sector_wbs(row, sector)
            self.fill_sector_activities(row, sector)

    def export(self, queryset=None):
        """
        Exports a resource.
        """
        rows = []

        if queryset is None:
            queryset = self.get_queryset()

        fields = SortedDict()

        for pca in queryset.iterator():

            self.fill_row(pca, fields)

        for pca in queryset.iterator():

            self.fill_pca_locations(fields, pca)

        self.headers = fields

        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.
        for pca in queryset.iterator():
            # second pass creates rows from the known table shape
            row = fields.copy()

            self.fill_row(pca, row)
            self.fill_pca_locations(row, pca)

            rows.append(row)

        data = tablib.Dataset(headers=fields.keys())
        for row in rows:
            data.append(row.values())
        return data

    class Meta:
        model = PCA
