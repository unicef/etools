__author__ = 'jcranwellward'

import glob
import tablib
import StringIO
from lxml import etree
from zipfile import ZipFile

#from collections import OrderedDict
from django.utils.datastructures import SortedDict
from django.template import Context, loader

from import_export import resources
from import_export.formats.base_formats import Format, CSV

from pykml.factory import KML_ElementMaker as KML

from shapely.geometry import Point, mapping
from fiona import collection

from partners.models import (
    PCA,
    GwPCALocation,
    PartnerOrganization,
)


class SHPFormat(Format):

    def get_title(self):
        return 'shp'

    def create_dataset(self, in_stream):
        """
        Create dataset from given string.
        """
        raise NotImplementedError()

    def export_data(self, dataset):
        """
        Returns format representation for given dataset.
        """
        attribs = {
            'ID': 'str',
            'Title': 'str',
            'PCA_Number': 'str',
            'Unicef_mng': 'str',
            'Total_budg': 'str',
            'Amendment': 'str',
            'Signed_by': 'str',
            'Partner': 'str',
            'Partner_mn': 'str',
            'Sectors': 'str',
            'Status': 'str',
            'Locality': 'str',
            'CAS_CODE': 'str',
            'CAD_CODE': 'str',
            'Gateway': 'str',
            'Loc_Name': 'str',
            'PCode/CERD': 'str'
        }

        # find all keys related to donors,
        # this dynamically changes with each dataset
        donors = {}
        for key in dataset.headers:
            if 'Donor' in key:
                donors[key] = 'str'
        attribs.update(donors)

        schema = {'geometry': 'Point', 'properties': attribs}
        with collection("PCAs.shp", "w", "ESRI Shapefile", schema) as output:

            for pca_data in dataset.dict:
                # copy donor data once for the pca
                donor_copy = donors.copy()
                for key,value in pca_data.iteritems():
                    if 'Donor' in key:
                        donor_copy[key] = value

                locations = GwPCALocation.objects.filter(pca__id=pca_data['ID'])
                for loc in locations:

                    # ignore locations with no point data
                    if not loc.location.point:
                        continue

                    data = dict()
                    data['ID'] = loc.pca.id
                    data['Title'] = loc.pca.title
                    data['PCA_Number'] = loc.pca.number
                    data['Unicef_mng'] = '{} {}'.format(loc.pca.unicef_mng_first_name, loc.pca.unicef_mng_last_name)
                    data['Total_budg'] = loc.pca.total_cash
                    data['Amendment'] = loc.pca.amendment
                    data['Signed_by'] = loc.pca.signed_by_unicef_date.strftime("%d-%m-%Y") if loc.pca.signed_by_unicef_date else ''
                    data['Partner'] = loc.pca.partner.name
                    data['Partner_mn'] = '{} {}'.format(loc.pca.partner_mng_first_name, loc.pca.partner_mng_last_name)
                    data['Sectors'] = loc.pca.sectors
                    data['Status'] = loc.pca.status
                    data['Locality'] = loc.locality.name
                    data['CAD_CODE'] = loc.locality.cad_code
                    data['CAS_CODE'] = loc.locality.cas_code
                    data['Gateway'] = loc.gateway.name
                    data['Loc_Name'] = loc.location.name
                    data['PCode/CERD'] = loc.location.p_code

                    # add donors
                    data.update(donor_copy)

                    if len(data) != len(attribs):
                        raise Exception("Number of values does not match num properties")

                    point = Point(loc.location.point.x, loc.location.point.y)
                    output.write({'properties': data, 'geometry': mapping(point)})

        in_memory = StringIO.StringIO()
        zip = ZipFile(in_memory, "a")

        for file in glob.glob("PCAs.*"):
            zip.write(file)

        # fix for Linux zip files read in Windows
        for file in zip.filelist:
            file.create_system = 0

        zip.close()

        in_memory.seek(0)
        return in_memory.read()

    def is_binary(self):
        """
        Returns if this format is binary.
        """
        return True

    def get_read_mode(self):
        """
        Returns mode for opening files.
        """
        return 'rb'

    def get_extension(self):
        """
        Returns extension for this format files.
        """
        return "zip"

    def can_import(self):
        return False

    def can_export(self):
        return True


class KMLFormat(Format):

    def get_title(self):
        return self.get_extension()

    def create_dataset(self, in_stream):
        """
        Create dataset from given string.
        """
        raise NotImplementedError()

    def export_data(self, dataset):
        """
        Returns format representation for given dataset.
        """
        kml_doc = KML.Document(KML.name('PCA Locations'))

        for pca_data in dataset.dict:

            locations = GwPCALocation.objects.filter(pca__id=pca_data['ID'])

            for loc in locations:

                data_copy = pca_data.copy()
                data_copy['Locality'] = loc.locality.name
                data_copy['CAD_CODE'] = loc.locality.cad_code
                data_copy['CAS_CODE'] = loc.locality.cas_code
                data_copy['Gateway'] = loc.gateway.name
                data_copy['Location Name'] = loc.location.name

                data = KML.ExtendedData()
                for key, value in data_copy.items():
                    data.append(
                        KML.Data(KML.value(value), name=key)
                    )

                point = KML.Placemark(
                    KML.name(data_copy['Number']),
                    data,
                    KML.Point(
                        KML.coordinates('{long},{lat}'.format(
                            lat=loc.location.point.y,
                            long=loc.location.point.x)
                        ),
                    ),
                )

                kml_doc.append(point)

        return etree.tostring(etree.ElementTree(KML.kml(kml_doc)), pretty_print=True)

    def is_binary(self):
        """
        Returns if this format is binary.
        """
        return False

    def get_read_mode(self):
        """
        Returns mode for opening files.
        """
        return 'rb'

    def get_extension(self):
        """
        Returns extension for this format files.
        """
        return "kml"

    def can_import(self):
        return False

    def can_export(self):
        return True


class PartnerResource(resources.ModelResource):

    class Meta:
        model = PartnerOrganization


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
            self.insert_column(row, 'Location Name {}'.format(num), location.location.name)

        return row

    def fill_pca_row(self, row, pca):

        self.insert_column(row, 'ID', pca.id)
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

        self.headers = fields

        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.
        for pca in queryset.iterator():
            # second pass creates rows from the known table shape
            row = fields.copy()

            self.fill_row(pca, row)

            rows.append(row)

        data = tablib.Dataset(headers=fields.keys())
        for row in rows:
            data.append(row.values())
        return data

    class Meta:
        model = PCA
