from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

import openpyxl
from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestionOverallFinding,
)
from etools.applications.field_monitoring.data_collection.tests.factories import ActivityQuestionFactory
from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory


@override_settings(RESTRICTED_ADMIN=False)
class TestRssAdminFieldMonitoringApi(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory()

    def test_sites_bulk_upload(self):
        # Build XLSX in-memory with required headers and a few rows
        # Ensure at least one active admin level 0 Location exists so LocationSite.save() can set parent
        LocationFactory(admin_level=0, is_active=True)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data"
        ws.append(["Site_Name", "Latitude", "Longitude"])  # headers
        ws.append(["LOC: Braachit_LBN41011", "33.175289", "35.443100"])  # valid
        ws.append(["LOC: Mjaydel_LBN62079", "33.517090", "35.440041"])  # valid
        ws.append(["", "34.298401", "35.850361"])  # invalid (name missing)
        ws.append(["LOC: BadCoords_LBN99999", "34.99e", "33.517090"])  # invalid coords

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)

        upload = SimpleUploadedFile(
            'LocationSites.xlsx',
            buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        url = reverse('rss_admin:rss-admin-sites-bulk-upload')
        resp = self.forced_auth_req('post', url, user=self.user, data={'import_file': upload}, request_format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        # Two valid created, rest skipped
        self.assertEqual(resp.data['created'] + resp.data['updated'], 2)
        self.assertGreaterEqual(resp.data['skipped'], 2)
        self.assertEqual(LocationSite.objects.count(), 2)

    def test_answer_hact_question_updates_overall_and_pv(self):
        # Create completed MonitoringActivity linked to partner
        activity = MonitoringActivityFactory(status='completed', partners=[self.partner])
        # Create partner-level HACT question
        question = QuestionFactory(is_hact=True, level='partner', is_active=True)
        # Create ActivityQuestion (enabled, HACT, linked to same partner)
        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=question,
            partner=self.partner,
            is_enabled=True,
        )
        # Sanity: no overall finding yet
        self.assertFalse(ActivityQuestionOverallFinding.objects.filter(activity_question=aq).exists())

        url = reverse('rss_admin:rss-admin-monitoring-activities-answer-hact', kwargs={'pk': activity.pk})
        payload = {
            'partner': self.partner.pk,
            'value': True,
        }
        resp = self.forced_auth_req('post', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

        # Overall finding created and set
        aq_of = ActivityQuestionOverallFinding.objects.get(activity_question=aq)
        self.assertEqual(aq_of.value, True)

        # Since activity is completed with an end_date, PV counter should increment to 1
        self.partner.refresh_from_db()
        self.assertEqual(self.partner.hact_values['programmatic_visits']['completed']['total'], 1)

    def test_set_on_track_upserts_activity_overall_finding(self):
        activity = MonitoringActivityFactory(status='review', partners=[self.partner])
        url = reverse('rss_admin:rss-admin-monitoring-activities-set-on-track', kwargs={'pk': activity.pk})
        payload = {
            'partner': self.partner.pk,
            'on_track': True,
        }
        resp = self.forced_auth_req('post', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        # ActivityOverallFinding exists and is set
        aof = ActivityOverallFinding.objects.get(monitoring_activity=activity, partner=self.partner)
        self.assertTrue(aof.on_track)
