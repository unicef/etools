__author__ = 'jcranwellward'

import tablib

from django.utils.datastructures import SortedDict

from import_export import resources

from partners.models import PCA


class PCAResource(resources.ModelResource):

    def fill_pca_row(self, row, pca, nulls=False):
        # dynamically add columns
        for num, grant in enumerate(pca.pcagrant_set.all()):
            num += 1
            row['Donor {}'.format(num)] = '' if nulls else grant.grant.donor.name
            row['Grant {}'.format(num)] = '' if nulls else grant.grant.name
            row['Amount {}'.format(num)] = '' if nulls else grant.funds

        for num, sector in enumerate(pca.pcasector_set.all()):
            num += 1
            row['Sector {}'.format(num)] = '' if nulls else sector.sector.name

            for num, output in enumerate(sector.pcasectoroutput_set.all()):
                num += 1
                row['RRP output {}'.format(num)] = '' if nulls else output.output.name

            for num, goal in enumerate(sector.pcasectorgoal_set.all()):
                num += 1
                row['CCC {}'.format(num)] = '' if nulls else goal.goal.name

            for num, indicator in enumerate(sector.indicatorprogress_set.all()):
                num += 1
                row['Indicator {}'.format(num)] = '' if nulls else indicator.indicator.name
                row['Unit {}'.format(num)] = '' if nulls else indicator.unit()
                row['Total Beneficiaries {}'.format(num)] = '' if nulls else indicator.programmed
                row['Current Beneficiaries {}'.format(num)] = '' if nulls else indicator.current
                row['Shortfall of Beneficiaries {}'.format(num)] = '' if nulls else indicator.shortfall()

            wbs_set = set()
            for ir in sector.pcasectorimmediateresult_set.all():
                for wbs in ir.wbs_activities.all():
                    wbs_set.add(wbs.name)

            for num, wbs in enumerate(wbs_set):
                num += 1
                row['WBS/Activity {}'.format(num)] = '' if nulls else wbs

            for num, activity in enumerate(sector.pcasectoractivity_set.all()):
                num += 1
                row['Activity {}'.format(num)] = '' if nulls else activity.activity.name

            for num, location in enumerate(pca.gwpcalocation_set.all()):
                num += 1
                row['Governorate {}'.format(num)] = '' if nulls else location.governorate.name
                row['Caza {}'.format(num)] = '' if nulls else location.region.name
                row['Locality {}'.format(num)] = '' if nulls else location.locality.name
                row['Gateway Type {}'.format(num)] = '' if nulls else location.gateway.name
                row['Location {}'.format(num)] = '' if nulls else location.location.name
                row['Latitude {}'.format(num)] = '' if nulls else location.location.point.y
                row['Longitude {}'.format(num)] = '' if nulls else location.location.point.x

    def export(self, queryset=None):
        """
        Exports a resource.
        """
        fields = SortedDict([
            ('Number', ''),
            ('Title', ''),
            ('Partner Organisation', ''),
            ('Initiation Date', ''),
            ('Status', ''),
            ('Start Date', ''),
            ('End Date', ''),
            ('Signed by unicef date', ''),
            ('Signed by partner date', ''),
            ('Unicef mng first name', ''),
            ('Unicef mng last name', ''),
            ('Unicef mng email', ''),
            ('Partner mng first name', ''),
            ('Partner mng last name', ''),
            ('Partner mng email', ''),
            ('Partner contribution budget', ''),
            ('Unicef cash budget', ''),
            ('In kind amount budget', ''),
            ('Total budget', ''),
        ])
        rows = []

        if queryset is None:
            queryset = self.get_queryset()

        for obj in queryset.iterator():
            # first pass gets the shape of the data
            self.fill_pca_row(fields, obj, nulls=True)

        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.
        for obj in queryset.iterator():
            # second pass creates rows from the known table shape
            row = fields.copy()
            row['Number'] = obj.number
            row['Title'] = obj.title
            row['Partner Organisation'] = obj.partner.name
            row['Initiation Date'] = obj.initiation_date.strftime("%d-%m-%Y")
            row['Status'] = obj.status
            row['Start Date'] = obj.start_date.strftime("%d-%m-%Y")
            row['End Date'] = obj.end_date.strftime("%d-%m-%Y")
            row['Signed by unicef date'] = obj.signed_by_unicef_date.strftime("%d-%m-%Y")
            row['Signed by partner date'] = obj.signed_by_partner_date.strftime("%d-%m-%Y")
            row['Unicef mng first name'] = obj.unicef_mng_first_name
            row['Unicef mng last name'] = obj.unicef_mng_last_name
            row['Unicef mng email'] = obj.unicef_mng_email
            row['Partner mng first name'] = obj.partner_mng_first_name
            row['Partner mng last name'] = obj.partner_mng_last_name
            row['Partner mng email'] = obj.partner_mng_email
            row['Partner contribution budget'] = obj.partner_contribution_budget
            row['Unicef cash budget'] = obj.unicef_cash_budget
            row['In kind amount budget'] = obj.in_kind_amount_budget
            row['Total budget'] = obj.total_cash
            
            self.fill_pca_row(row, obj)

            rows.append(row)

        data = tablib.Dataset(headers=fields.keys())
        for row in rows:
            data.append(row.values())
        return data

    class Meta:
        model = PCA
