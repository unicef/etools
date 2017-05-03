from __future__ import unicode_literals

from StringIO import StringIO

from EquiTrack.tests.mixins import APITenantTestCase
from publics.management.commands.update_dsa_regions import Command
from publics.models import DSARegion, DSARate
from publics.tests.factories import CountryFactory


class DSARateTest(APITenantTestCase):
    def setUp(self):
        super(DSARateTest, self).setUp()
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.command = Command(stdout=self.stdout, stderr=self.stderr)

    def test_updater(self):
        self.assertEqual(DSARegion.objects.all().count(), 0)
        self.assertEqual(DSARate.objects.all().count(), 0)

        dsa_code_country_mapping = {'AFG': CountryFactory(iso_3='AFG'),
                                    'BIH': CountryFactory(iso_3='BIH'),
                                    'CVI': CountryFactory(iso_3='CPV')}

        rows = [{'Room_Percentage': '70',
                 'Local_60': '10,800',
                 'Local_60Plus': '10,800',
                 'Unique ID': 'AFG301',
                 'USD_60': '162',
                 'Country Code': 'AFG',
                 'DSA Area Name': 'Kabul',
                 'Country Name': 'Afghanistan (Afghani)',
                 'Unique Name': 'AFGKabul',
                 'USD_60Plus': '162',
                 'Finalization_Date': '1/2/16',
                 'Area Code': '301',
                 'DSA_Eff_Date': '1/3/17'},
                {'Room_Percentage': '55',
                 'Local_60': '203',
                 'Local_60Plus': '153',
                 'Unique ID': 'BIH256',
                 'USD_60': '110',
                 'Country Code': 'BIH',
                 'DSA Area Name': 'Banja Luka',
                 'Country Name': 'Bosnia and Herzegovina (Convertible Mark)',
                 'Unique Name': 'BIHBanja Luka',
                 'USD_60Plus': '83',
                 'Finalization_Date': '1/5/16',
                 'Area Code': '256',
                 'DSA_Eff_Date': '1/3/17'}]
        self.command.update_dsa_regions(rows, dsa_code_country_mapping)

        self.assertEqual(DSARegion.objects.all().count(), 2)
        self.assertEqual(DSARegion.objects.active().count(), 2)
        self.assertEqual(DSARate.objects.all().count(), 2)

        region_afg = DSARegion.objects.get(area_code='301')
        region_bih = DSARegion.objects.get(area_code='256')

        self.assertEqual(region_afg.rates.all().count(), 1)
        self.assertEqual(region_bih.rates.all().count(), 1)

        rows = [{'Room_Percentage': '70',
                 'Local_60': '10,800',
                 'Local_60Plus': '10,800',
                 'Unique ID': 'AFG301',
                 'USD_60': '162',
                 'Country Code': 'AFG',
                 'DSA Area Name': 'Kabul',
                 'Country Name': 'Afghanistan (Afghani)',
                 'Unique Name': 'AFGKabul',
                 'USD_60Plus': '162',
                 'Finalization_Date': '1/2/16',
                 'Area Code': '301',
                 'DSA_Eff_Date': '1/3/17'},
                {'Room_Percentage': '60',
                 'Local_60': '1000',
                 'Local_60Plus': '800',
                 'Unique ID': 'BIH256',
                 'USD_60': '400',
                 'Country Code': 'BIH',
                 'DSA Area Name': 'Banja Luka',
                 'Country Name': 'Bosnia and Herzegovina (Convertible Mark)',
                 'Unique Name': 'BIHBanja Luka',
                 'USD_60Plus': '360',
                 'Finalization_Date': '15/3/17',
                 'Area Code': '256',
                 'DSA_Eff_Date': '1/4/17'},
                {'Room_Percentage': '57',
                 'Local_60': '20,900',
                 'Local_60Plus': '15,700',
                 'Unique ID': 'CVI603',
                 'USD_60': '201',
                 'Country Code': 'CVI',
                 'DSA Area Name': 'Boa Vista Island',
                 'Country Name': 'Cape Verde (CV Escudo)',
                 'Unique Name': 'CVIBoa Vista Island',
                 'USD_60Plus': '151',
                 'Finalization_Date': '1/2/16',
                 'Area Code': '603',
                 'DSA_Eff_Date': '1/3/17'}]
        self.command.update_dsa_regions(rows, dsa_code_country_mapping)

        self.assertEqual(DSARegion.objects.all().count(), 3)
        self.assertEqual(DSARegion.objects.active().count(), 3)
        self.assertEqual(DSARate.objects.all().count(), 4)

        region_cvi = DSARegion.objects.get(area_code='603')

        self.assertEqual(region_afg.rates.all().count(), 1)
        self.assertEqual(region_bih.rates.all().count(), 2)
        self.assertEqual(region_cvi.rates.all().count(), 1)

        rows = [{'Room_Percentage': '60',
                 'Local_60': '1000',
                 'Local_60Plus': '800',
                 'Unique ID': 'BIH256',
                 'USD_60': '400',
                 'Country Code': 'BIH',
                 'DSA Area Name': 'Banja Luka',
                 'Country Name': 'Bosnia and Herzegovina (Convertible Mark)',
                 'Unique Name': 'BIHBanja Luka',
                 'USD_60Plus': '360',
                 'Finalization_Date': '15/3/17',
                 'Area Code': '256',
                 'DSA_Eff_Date': '1/4/17'},
                {'Room_Percentage': '57',
                 'Local_60': '20,900',
                 'Local_60Plus': '15,700',
                 'Unique ID': 'CVI603',
                 'USD_60': '201',
                 'Country Code': 'CVI',
                 'DSA Area Name': 'Boa Vista Island',
                 'Country Name': 'Cape Verde (CV Escudo)',
                 'Unique Name': 'CVIBoa Vista Island',
                 'USD_60Plus': '151',
                 'Finalization_Date': '1/2/16',
                 'Area Code': '603',
                 'DSA_Eff_Date': '1/3/17'}]
        self.command.update_dsa_regions(rows, dsa_code_country_mapping)

        self.assertEqual(DSARegion.objects.all().count(), 3)
        self.assertEqual(DSARegion.objects.active().count(), 2)
        self.assertEqual(DSARate.objects.all().count(), 4)

        self.assertEqual(region_afg.rates.all().count(), 1)
        self.assertEqual(region_bih.rates.all().count(), 2)
        self.assertEqual(region_cvi.rates.all().count(), 1)
