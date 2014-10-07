__author__ = 'jcranwellward'

import tablib

from django.utils.datastructures import SortedDict

from import_export import resources

from .models import TPMVisit


class TPMResource(resources.ModelResource):

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

    def fill_tpm_row(self, row, tpm):

        self.insert_column(row, 'PCA', tpm.pca.__unicode__())
        self.insert_column(row, 'Status', tpm.status)
        self.insert_column(row, 'Cycle Number', tpm.cycle_number if tpm.cycle_number else 0)
        self.insert_column(row, 'Location', tpm.pca_location.__unicode__())
        self.insert_column(row, 'Sections', tpm.pca.sectors)
        self.insert_column(row, 'Assigned by', tpm.assigned_by.get_full_name())
        self.insert_column(row, 'Tentative Date', tpm.tentative_date.strftime("%d-%m-%Y") if tpm.tentative_date else '')
        self.insert_column(row, 'Completed Date', tpm.completed_date.strftime("%d-%m-%Y") if tpm.completed_date else '')
        self.insert_column(row, 'Comments', tpm.comments)

        return row

    def fill_row(self, tpm, row):

        self.fill_tpm_row(row, tpm)

    def export(self, queryset=None):
        """
        Exports a resource.
        """
        rows = []

        if queryset is None:
            queryset = self.get_queryset()

        fields = SortedDict()

        for tpm in queryset.iterator():

            self.fill_row(tpm, fields)

        self.headers = fields

        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.
        for tpm in queryset.iterator():
            # second pass creates rows from the known table shape
            row = fields.copy()

            self.fill_row(tpm, row)

            rows.append(row)

        data = tablib.Dataset(headers=fields.keys())
        for row in rows:
            data.append(row.values())
        return data

    class Meta:
        model = TPMVisit

