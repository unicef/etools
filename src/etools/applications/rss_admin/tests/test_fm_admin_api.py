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
from etools.applications.field_monitoring.fm_settings.tests.factories import OptionFactory, QuestionFactory
from etools.applications.field_monitoring.planning.models import MonitoringActivity
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

    def test_monitoring_activities_list_does_not_error(self):
        # Ensure at least one activity exists to trigger serializer list representation
        MonitoringActivityFactory()
        url = reverse('rss_admin:rss-admin-monitoring-activities-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, getattr(resp, 'data', None))
        data = resp.data
        first = None
        if isinstance(data, dict):
            results = data.get('results') or data.get('data') or []
            first = results[0] if results else None
        elif isinstance(data, list):
            first = data[0] if data else None
        if first is not None:
            # List view uses MonitoringActivityLightSerializer (no permissions field)
            # Permissions are only in detail view
            self.assertIn('id', first)
            self.assertIn('reference_number', first)
            self.assertIn('status', first)

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

    def test_monitoring_activities_list_pagination(self):
        """Test that pagination works correctly"""
        # Create 30 activities
        for i in range(30):
            MonitoringActivityFactory()

        url = reverse('rss_admin:rss-admin-monitoring-activities-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'page': 1, 'page_size': 10})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Check pagination structure
        self.assertIn('results', resp.data)
        self.assertIn('count', resp.data)
        self.assertIn('next', resp.data)
        self.assertIn('previous', resp.data)

        # Check page size
        self.assertEqual(len(resp.data['results']), 10)
        self.assertEqual(resp.data['count'], 30)

        # Test second page
        resp = self.forced_auth_req('get', url, user=self.user, data={'page': 2, 'page_size': 10})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 10)

    def test_monitoring_activities_list_filter_by_status(self):
        """Test filtering by status"""
        activity_draft = MonitoringActivityFactory(status=MonitoringActivity.STATUS_DRAFT)
        activity_completed = MonitoringActivityFactory(status=MonitoringActivity.STATUS_COMPLETED)

        url = reverse('rss_admin:rss-admin-monitoring-activities-list')

        # Filter by draft status
        resp = self.forced_auth_req('get', url, user=self.user, data={'status': MonitoringActivity.STATUS_DRAFT})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        result_ids = [r['id'] for r in results]
        self.assertIn(activity_draft.id, result_ids)
        self.assertNotIn(activity_completed.id, result_ids)

        # Filter by completed status
        resp = self.forced_auth_req('get', url, user=self.user, data={'status': MonitoringActivity.STATUS_COMPLETED})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        result_ids = [r['id'] for r in results]
        self.assertNotIn(activity_draft.id, result_ids)
        self.assertIn(activity_completed.id, result_ids)

    def test_monitoring_activities_list_filter_by_monitor_type(self):
        """Test filtering by monitor_type"""
        activity_staff = MonitoringActivityFactory(monitor_type=MonitoringActivity.MONITOR_TYPE_CHOICES.staff)
        activity_tpm = MonitoringActivityFactory(monitor_type=MonitoringActivity.MONITOR_TYPE_CHOICES.tpm)

        url = reverse('rss_admin:rss-admin-monitoring-activities-list')

        # Filter by staff monitor type
        resp = self.forced_auth_req('get', url, user=self.user,
                                    data={'monitor_type': MonitoringActivity.MONITOR_TYPE_CHOICES.staff})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        result_ids = [r['id'] for r in results]
        self.assertIn(activity_staff.id, result_ids)
        self.assertNotIn(activity_tpm.id, result_ids)

    def test_monitoring_activities_list_filter_by_location(self):
        """Test filtering by location"""
        location1 = LocationFactory()
        location2 = LocationFactory()
        activity1 = MonitoringActivityFactory(location=location1)
        activity2 = MonitoringActivityFactory(location=location2)

        url = reverse('rss_admin:rss-admin-monitoring-activities-list')

        # Filter by location1
        resp = self.forced_auth_req('get', url, user=self.user, data={'location': location1.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        result_ids = [r['id'] for r in results]
        self.assertIn(activity1.id, result_ids)
        self.assertNotIn(activity2.id, result_ids)

    def test_monitoring_activities_list_filter_by_date_range(self):
        """Test filtering by date range"""
        from datetime import date, timedelta

        today = date.today()
        past_date = today - timedelta(days=30)
        future_date = today + timedelta(days=30)

        activity_past = MonitoringActivityFactory(start_date=past_date, end_date=past_date)
        activity_current = MonitoringActivityFactory(start_date=today, end_date=today)
        activity_future = MonitoringActivityFactory(start_date=future_date, end_date=future_date)

        url = reverse('rss_admin:rss-admin-monitoring-activities-list')

        # Filter by start_date >= today
        resp = self.forced_auth_req('get', url, user=self.user, data={'start_date__gte': str(today)})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        result_ids = [r['id'] for r in results]
        self.assertNotIn(activity_past.id, result_ids)
        self.assertIn(activity_current.id, result_ids)
        self.assertIn(activity_future.id, result_ids)

        # Filter by end_date <= today
        resp = self.forced_auth_req('get', url, user=self.user, data={'end_date__lte': str(today)})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        result_ids = [r['id'] for r in results]
        self.assertIn(activity_past.id, result_ids)
        self.assertIn(activity_current.id, result_ids)
        self.assertNotIn(activity_future.id, result_ids)

    def test_monitoring_activities_list_ordering(self):
        """Test ordering functionality"""
        from datetime import date, timedelta

        today = date.today()
        activity1 = MonitoringActivityFactory(start_date=today - timedelta(days=2))
        activity2 = MonitoringActivityFactory(start_date=today - timedelta(days=1))
        activity3 = MonitoringActivityFactory(start_date=today)

        url = reverse('rss_admin:rss-admin-monitoring-activities-list')

        # Order by start_date ascending
        resp = self.forced_auth_req('get', url, user=self.user, data={'ordering': 'start_date'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        self.assertEqual(results[0]['id'], activity1.id)
        self.assertEqual(results[1]['id'], activity2.id)
        self.assertEqual(results[2]['id'], activity3.id)

        # Order by start_date descending
        resp = self.forced_auth_req('get', url, user=self.user, data={'ordering': '-start_date'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        self.assertEqual(results[0]['id'], activity3.id)
        self.assertEqual(results[1]['id'], activity2.id)
        self.assertEqual(results[2]['id'], activity1.id)

    def test_monitoring_activities_list_search(self):
        """Test search functionality"""
        activity1 = MonitoringActivityFactory()
        MonitoringActivityFactory()

        url = reverse('rss_admin:rss-admin-monitoring-activities-list')

        # Search by number (partial match)
        search_term = activity1.number[:6]
        resp = self.forced_auth_req('get', url, user=self.user, data={'search': search_term})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        result_ids = [r['id'] for r in results]
        self.assertIn(activity1.id, result_ids)

    def test_monitoring_activities_list_structure(self):
        """Test that list response has the correct structure matching field-monitoring endpoint"""
        MonitoringActivityFactory(
            partners=[self.partner],
            status=MonitoringActivity.STATUS_DRAFT
        )

        url = reverse('rss_admin:rss-admin-monitoring-activities-list')
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        results = resp.data.get('results', resp.data)
        self.assertTrue(len(results) > 0)

        # Check structure of first result (should use MonitoringActivityLightSerializer)
        first = results[0]
        expected_fields = [
            'id', 'reference_number', 'monitor_type', 'remote_monitoring',
            'tpm_partner', 'visit_lead', 'team_members', 'location', 'location_site',
            'partners', 'interventions', 'cp_outputs', 'start_date', 'end_date',
            'checklists_count', 'reject_reason', 'report_reject_reason', 'cancel_reason',
            'status', 'sections', 'overlapping_entities', 'visit_goals', 'objective', 'facility_types'
        ]
        for field in expected_fields:
            self.assertIn(field, first, f"Field '{field}' missing from response")

    def test_monitoring_activities_detail_structure(self):
        """Test that detail response has the correct structure with permissions"""
        activity = MonitoringActivityFactory(
            partners=[self.partner],
            status=MonitoringActivity.STATUS_DRAFT
        )

        url = reverse('rss_admin:rss-admin-monitoring-activities-detail', kwargs={'pk': activity.pk})
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Check structure (should use MonitoringActivitySerializer)
        expected_fields = [
            'id', 'reference_number', 'permissions', 'transitions',
            'offices', 'report_reviewers', 'reviewed_by'
        ]
        for field in expected_fields:
            self.assertIn(field, resp.data, f"Field '{field}' missing from detail response")

    def test_monitoring_activities_list_permissions_non_staff(self):
        """Test that non-staff users get 403"""
        # Create a non-staff user
        non_staff_user = UserFactory(is_staff=False)

        MonitoringActivityFactory()
        url = reverse('rss_admin:rss-admin-monitoring-activities-list')

        # Non-staff user should get 403
        resp = self.forced_auth_req('get', url, user=non_staff_user)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_monitoring_activities_detail_permissions_non_staff(self):
        """Test that non-staff users get 403 on detail"""
        # Create a non-staff user
        non_staff_user = UserFactory(is_staff=False)

        activity = MonitoringActivityFactory()
        url = reverse('rss_admin:rss-admin-monitoring-activities-detail', kwargs={'pk': activity.pk})

        # Non-staff user should get 403
        resp = self.forced_auth_req('get', url, user=non_staff_user)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_monitoring_activities_list_permissions_staff(self):
        """Test that staff users can access list"""
        MonitoringActivityFactory()
        url = reverse('rss_admin:rss-admin-monitoring-activities-list')

        # Staff user should get 200
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_monitoring_activities_detail_permissions_staff(self):
        """Test that staff users can access detail"""
        activity = MonitoringActivityFactory()
        url = reverse('rss_admin:rss-admin-monitoring-activities-detail', kwargs={'pk': activity.pk})

        # Staff user should get 200
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_monitoring_activities_combined_filters(self):
        """Test combining multiple filters"""
        from datetime import date, timedelta

        today = date.today()
        location = LocationFactory()
        partner = PartnerFactory()

        # Create activities with different combinations
        activity_match = MonitoringActivityFactory(
            status=MonitoringActivity.STATUS_DRAFT,
            location=location,
            start_date=today,
            partners=[partner]
        )
        activity_no_match = MonitoringActivityFactory(
            status=MonitoringActivity.STATUS_COMPLETED,
            start_date=today - timedelta(days=10)
        )

        url = reverse('rss_admin:rss-admin-monitoring-activities-list')

        # Combine filters
        resp = self.forced_auth_req('get', url, user=self.user, data={
            'status': MonitoringActivity.STATUS_DRAFT,
            'location': location.id,
            'start_date__gte': str(today)
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        result_ids = [r['id'] for r in results]
        self.assertIn(activity_match.id, result_ids)
        self.assertNotIn(activity_no_match.id, result_ids)

    def test_activity_findings_list(self):
        """Test that activity findings endpoint returns questions with answers for specific activity (matching eTools)"""
        activity = MonitoringActivityFactory(partners=[self.partner])

        # Create HACT question with answer
        hact_question = QuestionFactory(is_hact=True, level='partner', is_active=True)
        activity_question = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=hact_question,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )
        ActivityQuestionOverallFinding.objects.create(activity_question=activity_question, value=True)

        # Create non-HACT question without overall finding (won't be returned)
        non_hact_question = QuestionFactory(is_hact=False, level='partner', is_active=True)
        ActivityQuestionFactory(
            monitoring_activity=activity,
            question=non_hact_question,
            partner=self.partner,
            is_hact=False,
            is_enabled=True,
        )

        # Create question on different activity (should be excluded)
        other_activity = MonitoringActivityFactory(partners=[self.partner])
        other_activity_question = ActivityQuestionFactory(
            monitoring_activity=other_activity,
            question=hact_question,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )
        ActivityQuestionOverallFinding.objects.create(activity_question=other_activity_question, value=False)

        url = reverse('rss_admin:rss-admin-activity-findings-list', kwargs={'monitoring_activity_pk': activity.pk})
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Should return questions for this activity only (matches eTools behavior)
        # We created 1 finding for activity and 1 for other_activity, so only 1 should be returned
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['value'], True)  # The finding we created for this activity

        # Check that question details and options are included
        self.assertIn('question', resp.data[0]['activity_question'])
        self.assertIn('partner', resp.data[0]['activity_question'])
        self.assertIn('findings', resp.data[0]['activity_question'])  # New field from field monitoring structure

    def test_activity_findings_patch(self):
        """Test updating question answer via PATCH"""
        activity = MonitoringActivityFactory(partners=[self.partner])

        # Create HACT question with initial answer
        hact_question = QuestionFactory(is_hact=True, level='partner', is_active=True)
        activity_question = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=hact_question,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )
        overall_finding = ActivityQuestionOverallFinding.objects.create(
            activity_question=activity_question,
            value=False
        )

        url = reverse('rss_admin:rss-admin-activity-findings-detail',
                      kwargs={'monitoring_activity_pk': activity.pk, 'pk': overall_finding.pk})

        # Update the answer
        payload = {'value': True}
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify the update
        overall_finding.refresh_from_db()
        self.assertEqual(overall_finding.value, True)

    def test_activity_findings_non_staff_forbidden(self):
        """Test that non-staff users cannot access activity findings"""
        non_staff_user = UserFactory(is_staff=False)
        activity = MonitoringActivityFactory()

        url = reverse('rss_admin:rss-admin-activity-findings-list', kwargs={'monitoring_activity_pk': activity.pk})
        resp = self.forced_auth_req('get', url, user=non_staff_user)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_activity_findings_with_question_options(self):
        """Test that activity findings include question options for choice questions"""
        activity = MonitoringActivityFactory(partners=[self.partner])

        # Create HACT question with options
        hact_question = QuestionFactory(
            is_hact=True,
            level='partner',
            is_active=True,
        )
        # Add some options to the question
        OptionFactory(question=hact_question, label='Yes', value=1)
        OptionFactory(question=hact_question, label='No', value=0)

        activity_question = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=hact_question,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=activity_question,
            value={'option': 'yes'}
        )

        url = reverse('rss_admin:rss-admin-activity-findings-list', kwargs={'monitoring_activity_pk': activity.pk})
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Check that options are included
        self.assertIn('question', resp.data[0]['activity_question'])
        self.assertIn('options', resp.data[0]['activity_question']['question'])
        # At least the 2 options we created should be present (factory may add defaults)
        self.assertGreaterEqual(len(resp.data[0]['activity_question']['question']['options']), 2)

    def test_activity_overall_findings_list(self):
        """Test that activity overall findings endpoint returns findings for specific activity (matching eTools)"""
        activity = MonitoringActivityFactory(partners=[self.partner])

        # Create HACT question
        hact_question = QuestionFactory(is_hact=True, level='partner', is_active=True)
        ActivityQuestionFactory(  # noqa: F841
            monitoring_activity=activity,
            question=hact_question,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )

        # Create activity overall finding
        ActivityOverallFinding.objects.create(  # noqa: F841
            monitoring_activity=activity,
            partner=self.partner,
            narrative_finding='Test finding',
            on_track=True
        )

        # Create overall finding for different activity (should be excluded)
        other_activity = MonitoringActivityFactory(partners=[self.partner])
        ActivityOverallFinding.objects.create(
            monitoring_activity=other_activity,
            partner=self.partner,
            narrative_finding='Other finding',
            on_track=False
        )

        url = reverse('rss_admin:rss-admin-activity-overall-findings-list', kwargs={'monitoring_activity_pk': activity.pk})
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Should return overall findings for this activity only (matches eTools behavior)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['partner'], self.partner.pk)
        self.assertEqual(resp.data[0]['narrative_finding'], 'Test finding')
        self.assertEqual(resp.data[0]['on_track'], True)

        # Check structure matches field monitoring
        self.assertIn('attachments', resp.data[0])
        self.assertIn('findings', resp.data[0])

    def test_activity_overall_findings_patch(self):
        """Test updating activity overall finding via PATCH"""
        activity = MonitoringActivityFactory(partners=[self.partner])

        # Create question for this activity
        question = QuestionFactory(is_hact=True, level='partner', is_active=True)
        ActivityQuestionFactory(
            monitoring_activity=activity,
            question=question,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )

        # Create activity overall finding
        overall_finding = ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=self.partner,
            narrative_finding='Initial finding',
            on_track=False
        )

        url = reverse('rss_admin:rss-admin-activity-overall-findings-detail',
                      kwargs={'monitoring_activity_pk': activity.pk, 'pk': overall_finding.pk})

        # Update the finding
        payload = {'narrative_finding': 'Updated finding', 'on_track': True}
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify the update
        overall_finding.refresh_from_db()
        self.assertEqual(overall_finding.narrative_finding, 'Updated finding')
        self.assertEqual(overall_finding.on_track, True)

    def test_activity_findings_patch_single(self):
        """Test PATCH on a single finding"""
        activity = MonitoringActivityFactory(partners=[self.partner])

        # Create HACT question with overall finding
        hact_question = QuestionFactory(is_hact=True, level='partner', is_active=True)
        activity_question = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=hact_question,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )
        overall_finding = ActivityQuestionOverallFinding.objects.create(
            activity_question=activity_question
        )

        url = reverse(
            'rss_admin:rss-admin-activity-findings-detail',
            kwargs={'monitoring_activity_pk': activity.pk, 'pk': overall_finding.pk}
        )

        # PATCH to update the value
        payload = {'value': 'Updated finding value'}
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        overall_finding.refresh_from_db()
        self.assertEqual(overall_finding.value, 'Updated finding value')

    def test_activity_findings_patch_bulk(self):
        """Test bulk PATCH on multiple findings"""
        activity = MonitoringActivityFactory(partners=[self.partner])

        # Create multiple questions with overall findings
        hact_question1 = QuestionFactory(is_hact=True, level='partner', is_active=True)
        activity_question1 = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=hact_question1,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )
        overall_finding1 = ActivityQuestionOverallFinding.objects.create(
            activity_question=activity_question1
        )

        hact_question2 = QuestionFactory(is_hact=True, level='partner', is_active=True)
        activity_question2 = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=hact_question2,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )
        overall_finding2 = ActivityQuestionOverallFinding.objects.create(
            activity_question=activity_question2
        )

        url = reverse('rss_admin:rss-admin-activity-findings-list', kwargs={'monitoring_activity_pk': activity.pk})

        # Bulk PATCH to update multiple findings
        payload = [
            {'id': overall_finding1.pk, 'value': 'Bulk update value 1'},
            {'id': overall_finding2.pk, 'value': 'Bulk update value 2'}
        ]
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify both findings were updated
        overall_finding1.refresh_from_db()
        overall_finding2.refresh_from_db()
        self.assertEqual(overall_finding1.value, 'Bulk update value 1')
        self.assertEqual(overall_finding2.value, 'Bulk update value 2')

    def test_activity_findings_patch_bulk_requires_list(self):
        """Test that bulk PATCH requires a list, not a single object"""
        activity = MonitoringActivityFactory(partners=[self.partner])

        hact_question = QuestionFactory(is_hact=True, level='partner', is_active=True)
        activity_question = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=hact_question,
            partner=self.partner,
            is_hact=True,
            is_enabled=True,
        )
        overall_finding = ActivityQuestionOverallFinding.objects.create(
            activity_question=activity_question
        )

        url = reverse('rss_admin:rss-admin-activity-findings-list', kwargs={'monitoring_activity_pk': activity.pk})

        # Send a single object instead of a list - should fail
        payload = {'id': overall_finding.pk, 'value': 'Single object'}
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)

        # Should return 400 Bad Request because it expects a list
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activity_findings_patch_bulk_only_updates_specified_ids(self):
        """Test that bulk PATCH only updates findings with specified IDs"""
        activity = MonitoringActivityFactory(partners=[self.partner])

        # Create three findings
        findings = []
        for i in range(3):
            hact_question = QuestionFactory(is_hact=True, level='partner', is_active=True)
            activity_question = ActivityQuestionFactory(
                monitoring_activity=activity,
                question=hact_question,
                partner=self.partner,
                is_hact=True,
                is_enabled=True,
            )
            finding = ActivityQuestionOverallFinding.objects.create(
                activity_question=activity_question,
                value=f'Original value {i}'
            )
            findings.append(finding)

        url = reverse('rss_admin:rss-admin-activity-findings-list', kwargs={'monitoring_activity_pk': activity.pk})

        # Only update the first two
        payload = [
            {'id': findings[0].pk, 'value': 'Updated 0'},
            {'id': findings[1].pk, 'value': 'Updated 1'}
        ]
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify only the first two were updated
        findings[0].refresh_from_db()
        findings[1].refresh_from_db()
        findings[2].refresh_from_db()

        self.assertEqual(findings[0].value, 'Updated 0')
        self.assertEqual(findings[1].value, 'Updated 1')
        self.assertEqual(findings[2].value, 'Original value 2')  # Unchanged

    def test_findings_endpoint_returns_same_count_as_etools(self):
        """Test that RSS admin findings endpoint returns the same number of items as eTools endpoint."""
        activity = MonitoringActivityFactory(partners=[self.partner])

        # Create 10 activity questions with overall findings
        for i in range(10):
            question = QuestionFactory(is_hact=(i % 2 == 0), level='partner', is_active=True)
            activity_question = ActivityQuestionFactory(
                monitoring_activity=activity,
                question=question,
                partner=self.partner,
                is_hact=(i % 2 == 0),  # Mix of HACT and non-HACT
                is_enabled=True,
            )
            ActivityQuestionOverallFinding.objects.create(
                activity_question=activity_question,
                value=f'Finding value {i}'
            )

        # Fetch from RSS admin endpoint
        rss_admin_url = reverse(
            'rss_admin:rss-admin-activity-findings-list',
            kwargs={'monitoring_activity_pk': activity.pk}
        )
        rss_admin_resp = self.forced_auth_req('get', rss_admin_url, user=self.user)
        self.assertEqual(rss_admin_resp.status_code, status.HTTP_200_OK)

        # Fetch from eTools endpoint
        etools_url = reverse(
            'field_monitoring_data_collection:activity-findings-list',
            kwargs={'monitoring_activity_pk': activity.pk}
        )
        etools_resp = self.forced_auth_req('get', etools_url, user=self.user, data={'page_size': 'all'})
        self.assertEqual(etools_resp.status_code, status.HTTP_200_OK)

        # Get counts - handle both list and paginated responses
        rss_admin_data = rss_admin_resp.data
        etools_data = etools_resp.data
        if isinstance(etools_data, dict) and 'results' in etools_data:
            etools_count = len(etools_data['results'])
        else:
            etools_count = len(etools_data)
        rss_admin_count = len(rss_admin_data)

        # Assert both endpoints return the same count
        self.assertEqual(rss_admin_count, etools_count)
        self.assertEqual(rss_admin_count, 10)  # We created exactly 10 items

    def test_overall_findings_endpoint_returns_same_count_as_etools(self):
        """Test that RSS admin overall-findings endpoint returns the same number of items as eTools endpoint."""
        # Create 10 partners for the activity
        partners = [PartnerFactory() for _ in range(10)]
        activity = MonitoringActivityFactory(partners=partners)

        # Create 10 activity overall findings (one per partner)
        for i, partner in enumerate(partners):
            ActivityOverallFinding.objects.create(
                monitoring_activity=activity,
                partner=partner,
                narrative_finding=f'Overall finding {i}',
                on_track=(i % 2 == 0)
            )

        # Fetch from RSS admin endpoint
        rss_admin_url = reverse(
            'rss_admin:rss-admin-activity-overall-findings-list',
            kwargs={'monitoring_activity_pk': activity.pk}
        )
        rss_admin_resp = self.forced_auth_req('get', rss_admin_url, user=self.user)
        self.assertEqual(rss_admin_resp.status_code, status.HTTP_200_OK)

        # Fetch from eTools endpoint
        etools_url = reverse(
            'field_monitoring_data_collection:activity-overall-findings-list',
            kwargs={'monitoring_activity_pk': activity.pk}
        )
        etools_resp = self.forced_auth_req('get', etools_url, user=self.user, data={'page_size': 'all'})
        self.assertEqual(etools_resp.status_code, status.HTTP_200_OK)

        # Get counts - handle both list and paginated responses
        rss_admin_data = rss_admin_resp.data
        etools_data = etools_resp.data
        if isinstance(etools_data, dict) and 'results' in etools_data:
            etools_count = len(etools_data['results'])
        else:
            etools_count = len(etools_data)
        rss_admin_count = len(rss_admin_data)

        # Assert both endpoints return the same count
        self.assertEqual(rss_admin_count, etools_count)
        self.assertEqual(rss_admin_count, 10)  # We created exactly 10 items

    def test_findings_endpoints_exclude_other_activities(self):
        """Test that both endpoints only return items for the requested activity, not others."""
        activity1 = MonitoringActivityFactory(partners=[self.partner])
        activity2 = MonitoringActivityFactory(partners=[self.partner])

        # Create 10 findings for activity1
        for i in range(10):
            question = QuestionFactory(is_hact=True, level='partner', is_active=True)
            aq = ActivityQuestionFactory(
                monitoring_activity=activity1,
                question=question,
                partner=self.partner,
                is_hact=True,
                is_enabled=True,
            )
            ActivityQuestionOverallFinding.objects.create(activity_question=aq, value=f'Activity1 finding {i}')

        # Create 5 findings for activity2 (should NOT appear in activity1 results)
        for i in range(5):
            question = QuestionFactory(is_hact=True, level='partner', is_active=True)
            aq = ActivityQuestionFactory(
                monitoring_activity=activity2,
                question=question,
                partner=self.partner,
                is_hact=True,
                is_enabled=True,
            )
            ActivityQuestionOverallFinding.objects.create(activity_question=aq, value=f'Activity2 finding {i}')

        # Fetch activity1 from RSS admin
        rss_admin_url = reverse(
            'rss_admin:rss-admin-activity-findings-list',
            kwargs={'monitoring_activity_pk': activity1.pk}
        )
        rss_admin_resp = self.forced_auth_req('get', rss_admin_url, user=self.user)
        self.assertEqual(rss_admin_resp.status_code, status.HTTP_200_OK)

        # Fetch activity1 from eTools
        etools_url = reverse(
            'field_monitoring_data_collection:activity-findings-list',
            kwargs={'monitoring_activity_pk': activity1.pk}
        )
        etools_resp = self.forced_auth_req('get', etools_url, user=self.user, data={'page_size': 'all'})
        self.assertEqual(etools_resp.status_code, status.HTTP_200_OK)

        # Get counts
        rss_admin_data = rss_admin_resp.data
        etools_data = etools_resp.data
        if isinstance(etools_data, dict) and 'results' in etools_data:
            etools_count = len(etools_data['results'])
        else:
            etools_count = len(etools_data)
        rss_admin_count = len(rss_admin_data)

        # Both should return exactly 10 (only activity1's findings)
        self.assertEqual(rss_admin_count, 10)
        self.assertEqual(etools_count, 10)
        self.assertEqual(rss_admin_count, etools_count)
