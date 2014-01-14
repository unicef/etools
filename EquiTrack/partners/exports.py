__author__ = 'jcranwellward'

import tablib
from import_export import resources

from partners.models import PCA


class PCAResource(resources.ModelResource):

    def export(self, queryset=None):
        """
        Exports a resource.
        """
        fields = {
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
        }

        if queryset is None:
            queryset = self.get_queryset()

        for obj in queryset.iterator():

            # dynamically add columns
            for num,grant in enumerate(obj.pcagrant_set().all()):
                fields['donor name {}'.format(num or '')] = ''


        headers = self.get_export_headers()
        data = tablib.Dataset(headers=headers)
        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.
        for obj in queryset.iterator():
            data.append(self.export_resource(obj))
        return data

    class Meta:
        model = PCA
        fields = (



        )