from io import BytesIO

from django.contrib.admin import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import Client
from django.urls import reverse

import openpyxl
from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.admin import LocationSiteAdmin
from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.test_admin import MockRequest


class TestLocationSiteAdmin(BaseTenantTestCase):
    client_class = Client

    @classmethod
    def setUpTestData(cls):
        site = AdminSite()
        cls.admin = LocationSiteAdmin(LocationSite, site)
        cls.request = MockRequest()

        cls.superuser = UserFactory(is_superuser=True, is_staff=True)
        cls.user = UserFactory()
        cls.client = Client()

    def test_has_import_permission(self):
        self.request.user = self.superuser
        self.assertTrue(self.admin.has_import_permission(self.request))

        self.request.user = self.user
        self.assertFalse(self.admin.has_import_permission(self.request))

    @staticmethod
    def create_test_xlsx():
        """Helper method to create a test XLSX file in memory"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data"

        ws.append(['Site_Name', 'Latitude', 'Longitude'])

        ws.append(['LOC: Braachit_LBN41011', '33.175289', '35.443100'])
        ws.append(['LOC: Mjaydel_LBN62079', '33.517090', '35.440041'])
        ws.append(['LOC: Majdel el Koura_LBN54029',	'34.252449', '35.792671'])
        ws.append(['LOC: Kousba_LBN54044', '34.298401',	'35.850361'])
        ws.append(['LOC: Meftah es Sellom_LBN34165', '34.99e', '33.517090'])  # invalid Coordinates, will be skipped

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    def test_import_file(self):
        self.sites_file = SimpleUploadedFile(
            'LocationSites.xlsx',
            self.create_test_xlsx().read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        self.assertEqual(LocationSite.objects.count(), 0)

        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse('admin:field_monitoring_settings_locationsite_import')
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        LocationFactory(admin_level=0, is_active=True)
        response = self.client.post(
            reverse('admin:field_monitoring_settings_locationsite_import'),
            data={
                "import_file": self.sites_file,
                '_save_records': ['Submit']
            },
            follow=True
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(LocationSite.objects.count(), 4, '4 Valid, 1 Invalid')
