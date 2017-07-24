from EquiTrack.utils import BaseExportResource
from tpm.models import TPMVisit


class TPMResource(BaseExportResource):

    class Meta:
        model = TPMVisit

    def fill_tpm_row(self, row, tpm):

        self.insert_column(row, 'PCA', tpm.pca.__unicode__())
        self.insert_column(row, 'Status', tpm.status)
        self.insert_column(row, 'Cycle Number', tpm.cycle_number if tpm.cycle_number else 0)
        self.insert_column(row, 'Location', tpm.pca_location.__unicode__())
        self.insert_column(row, 'Sections', tpm.pca.sector_names)
        self.insert_column(row, 'Assigned by', tpm.assigned_by.get_full_name())
        self.insert_column(row, 'Tentative Date', tpm.tentative_date.strftime("%d-%m-%Y") if tpm.tentative_date else '')
        self.insert_column(row, 'Completed Date', tpm.completed_date.strftime("%d-%m-%Y") if tpm.completed_date else '')
        self.insert_column(row, 'Comments', tpm.comments)

        return row

    def fill_row(self, tpm, row):

        self.fill_tpm_row(row, tpm)
