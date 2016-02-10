__author__ = 'jcranwellward'

import tablib
import tempfile
import zipfile
import datetime
from pytz import timezone
# from lxml import etree

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.utils.datastructures import SortedDict

from import_export import resources
from import_export.formats.base_formats import Format

import fiona
from shapely.geometry import Point, mapping
# from pykml.factory import KML_ElementMaker as KML

from EquiTrack.utils import BaseExportResource
from locations.models import Location
from .models import (
    PCA,
    GwPCALocation,
    PartnerOrganization,
    PartnershipBudget,
    AmendmentLog
)


class SHPFormat(Format):

    def get_title(self):
        return 'shp'

    def prepare_shapefile(self, dataset):

        tmp = tempfile.NamedTemporaryFile(suffix='.shp', mode='w')
        # we must close the file for GDAL to be able to open and write to it
        tmp.close()

        attributes = {}
        for key in dataset.headers:
            attributes[key] = 'str'

        schema = {'geometry': 'Point', 'properties': attributes}
        with fiona.open(tmp.name, 'w', 'ESRI Shapefile', schema) as output:

            for data in dataset.dict:

                point = Point(data['x'], data['y'])
                output.write({'properties': data, 'geometry': mapping(point)})

        return tmp.name

    def zip_response(self, shapefile_path, file_name, readme=None):

        buffer = StringIO()
        zip = zipfile.ZipFile(buffer, 'a', zipfile.ZIP_DEFLATED)
        files = ['shp', 'shx', 'dbf']
        for item in files:
            filename = '{}.{}'.format(shapefile_path.replace('.shp', ''), item)
            zip.write(filename, arcname='{}.{}'.format(file_name.replace('.shp', ''), item))
        if readme:
            zip.writestr('README.txt', readme)
        zip.close()

        buffer.seek(0)
        return buffer.read()

    def get_extension(self):
        """
        Returns extension for this format files.
        """
        return "zip"

    def can_export(self):
        return True


class DonorsFormat(SHPFormat):

    def get_title(self):
        return 'by donors'

    def export_data(self, dataset):

        locs = []

        if dataset.csv != '':
            pcas = PCA.objects.filter(
                id__in=dataset['ID']
            )
            for pca in pcas:
                donors = set(pca.pcagrant_set.all().values_list('grant__donor__name', flat=True))
                for loc in pca.locations.filter(location__point__isnull=False):
                    locs.append(
                        {
                            'Donors': ', '.join([d for d in donors]),
                            'Gateway Type': loc.location.gateway.name,
                            'PCode': loc.location.p_code,
                            'Locality': loc.locality.name,
                            'Cad Code': loc.locality.cad_code,
                            'x': loc.location.point.x,
                            'y': loc.location.point.y
                        }
                    )

        data = tablib.Dataset(headers=locs[0].keys()) if locs \
            else tablib.Dataset(headers=['Donors', 'Gateway Type', 'Locality', 'PCode', 'y', 'x', 'Cad Code'])

        for loc in {v['PCode']: v for v in locs}.values():
            data.append(loc.values())

        shpfile = self.prepare_shapefile(data)
        return self.zip_response(shpfile, 'Donors')


class PartnerResource(resources.ModelResource):

    class Meta:
        model = PartnerOrganization


class PCAResource(BaseExportResource):

    class Meta:
        model = PCA

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
        self.insert_column(row, 'Number', pca.number)
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
        self.fill_pca_grants(row, pca)

        # for sector in sorted(pca.pcasector_set.all()):
        #
        #     self.fill_sector_outputs(row, sector)
        #     self.fill_sector_goals(row, sector)
        #     self.fill_sector_indicators(row, sector)
        #     self.fill_sector_wbs(row, sector)
        #     self.fill_sector_activities(row, sector)

