__author__ = 'jcranwellward'

import tablib

from django.utils.datastructures import SortedDict

from import_export import resources

from partners.models import PCA


class PCAResource(resources.ModelResource):

    def export(self, queryset=None):
        """
        Exports a resource.
        """
        fields = SortedDict({
            'number': '',
            'title': '',
            'partner organisation': '',
            'initiation date': '',
            'status': '',
            'start date': '',
            'end date': '',
            'signed by unicef date': '',
            'signed by partner date': '',
            'unicef mng first name': '',
            'unicef mng last name': '',
            'unicef mng email': '',
            'partner mng first name': '',
            'partner mng last name': '',
            'partner mng email': '',
            'partner contribution budget': '',
            'unicef cash budget': '',
            'in kind amount budget': '',
            'total budget': '',
        })
        rows = []

        if queryset is None:
            queryset = self.get_queryset()

        for obj in queryset.iterator():
            # dynamically add columns
            for num, grant in enumerate(obj.pcagrant_set.all()):
                fields['donor name {}'.format(num or '')] = ''
                fields['grant name {}'.format(num or '')] = ''
                fields['donor amount {}'.format(num or '')] = ''

            for num, sector in enumerate(obj.pcasector_set.all()):
                fields['sector {}'.format(num or '')] = ''

                for num, output in enumerate(sector.pcasectoroutput_set.all()):
                    fields['RRP output {}'.format(num or '')] = ''

                for num, goal in enumerate(sector.pcasectorgoal_set.all()):
                    fields['CCC name {}'.format(num or '')] = ''

        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.
        for obj in queryset.iterator():
            
            row = fields.copy()
            row['number'] = obj.number
            row['title'] = obj.title
            row['partner organisation'] = obj.partner.name
            row['initiation date'] = obj.initiation_date
            row['status'] = obj.status
            row['start date'] = obj.start_date
            row['end date'] = obj.end_date
            row['signed by unicef date'] = obj.signed_by_unicef_date
            row['signed by partner date'] = obj.signed_by_partner_date
            row['unicef mng first name'] = obj.unicef_mng_first_name
            row['unicef mng last name'] = obj.unicef_mng_last_name
            row['unicef mng email'] = obj.unicef_mng_email
            row['partner mng first name'] = obj.partner_mng_first_name
            row['partner mng last name'] = obj.partner_mng_last_name
            row['partner mng email'] = obj.partner_mng_email
            row['partner contribution budget'] = obj.partner_contribution_budget
            row['unicef cash budget'] = obj.unicef_cash_budget
            row['in kind amount budget'] = obj.in_kind_amount_budget
            row['total budget'] = obj.total_cash
            
            for num, grant in enumerate(obj.pcagrant_set.all()):
                row['donor name {}'.format(num or '')] = grant.grant.donor.name
                row['grant name {}'.format(num or '')] = grant.grant.name
                fields['donor amount {}'.format(num or '')] = grant.funds

            for num, sector in enumerate(obj.pcasector_set.all()):
                fields['sector {}'.format(num or '')] = sector.sector.name

                for num, output in enumerate(sector.pcasectoroutput_set.all()):
                    fields['RRP output {}'.format(num or '')] = output.output.name

                for num, goal in enumerate(sector.pcasectorgoal_set.all()):
                    fields['CCC name {}'.format(num or '')] = goal.goal.name

            rows.append(row)

        data = tablib.Dataset(headers=fields.keys())
        for row in rows:
            data.append(row.values())
        return data

    class Meta:
        model = PCA
