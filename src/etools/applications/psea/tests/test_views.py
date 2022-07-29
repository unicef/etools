import datetime
import json
from unittest.mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from factory import fuzzy
from rest_framework import status
from unicef_attachments.models import Attachment
from unicef_rest_export import renderers

from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.audit.models import UNICEFAuditFocalPoint
from etools.applications.audit.tests.factories import (
    AuditorStaffMemberFactory,
    AuditPartnerFactory,
    PurchaseOrderFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.psea.models import Answer, Assessment, AssessmentStatusHistory, Assessor, Indicator
from etools.applications.psea.tests.factories import (
    AnswerEvidenceFactory,
    AnswerFactory,
    AssessmentFactory,
    AssessorFactory,
    EvidenceFactory,
    IndicatorFactory,
    RatingFactory,
)
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class TestPSEAStaticDropdownsListApiView(BaseTenantTestCase):
    """exercise PmpStaticDropdownsListApiView"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)
        cls.url = reverse("psea:psea-static-list")

    def test_static(self):

        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertEqual(sorted(response_json.keys()), ['ingo_reasons', 'ratings', 'types'])


class TestAssessmentViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.send_path = "etools.applications.psea.validation.send_notification_with_template"
        cls.user = UserFactory()
        cls.focal_user = UserFactory()
        cls.focal_user.groups.add(
            GroupFactory(name=UNICEFAuditFocalPoint.name),
        )
        cls.partner = PartnerFactory()

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        num = 10
        for _ in range(num):
            assessment = AssessmentFactory()
            AnswerFactory(assessment=assessment)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), num)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list_external_user(self):
        num = 10
        for _ in range(num):
            assessment = AssessmentFactory()
            AnswerFactory(assessment=assessment)
        external_user = UserFactory(email="me@extra.example.com")
        assessor = AssessorFactory(user=external_user)
        assessment = AssessmentFactory(assessor=assessor)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            user=external_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), 1)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_get(self):
        partner = PartnerFactory()
        date = str(timezone.now().date())
        assessment = AssessmentFactory(
            partner=partner,
            assessment_date=date,
        )

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=self.focal_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], assessment.pk)
        self.assertEqual(data["partner"], partner.pk)
        self.assertEqual(data["assessment_date"], date)
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["available_actions"], ["assign", "cancel"])
        self.assertTrue(data["permissions"]["edit"]["info_card"])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_status(self):
        for _ in range(10):
            AssessmentFactory()

        status_val = Assessment.STATUS_CANCELLED
        assessment = AssessmentFactory(status=status_val)
        assessment.status = status_val
        assessment.save()
        self.assertEqual(assessment.status, status_val)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"status": status_val},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Assessment.objects.filter(status=status_val).count()
        )
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_partner(self):
        for _ in range(10):
            AssessmentFactory()

        partner = PartnerFactory()
        assessment = AssessmentFactory(partner=partner)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"partner": partner.pk},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_focal_point(self):
        for _ in range(10):
            AssessmentFactory()

        assessment = AssessmentFactory()
        assessment.focal_points.set([self.user])

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"unicef_focal_point": self.user.pk},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_assessment_date_before(self):
        date = datetime.date(2001, 1, 1)
        assessment = AssessmentFactory(assessment_date=date)
        date_after = date + datetime.timedelta(days=20)
        for _ in range(10):
            AssessmentFactory(assessment_date=date_after)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={
                "assessment_date__lt": (
                    date + datetime.timedelta(days=1)
                ).strftime("%Y-%m-%d"),
            },
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_assessment_date_after(self):
        date = datetime.date(2001, 1, 1)
        assessment = AssessmentFactory(assessment_date=date)
        date_after = date - datetime.timedelta(days=20)
        for _ in range(10):
            AssessmentFactory(assessment_date=date_after)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={
                "assessment_date__gt": (
                    date - datetime.timedelta(days=1)
                ).strftime("%Y-%m-%d"),
            },
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_assessor_staff(self):
        for _ in range(10):
            AssessmentFactory()

        assessment = AssessmentFactory()
        user = UserFactory()
        AssessorFactory(assessment=assessment, user=user)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"assessor_staff": user.pk},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_assessor_firm(self):
        for _ in range(10):
            AssessmentFactory()

        firm = AuditPartnerFactory()
        assessment = AssessmentFactory()
        AssessorFactory(assessment=assessment, auditor_firm=firm)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"assessor_firm": firm.pk},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_reference_number(self):
        for _ in range(10):
            AssessmentFactory()

        assessment = AssessmentFactory()

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"q": assessment.reference_number[-10:]},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_auditor_firm(self):
        for _ in range(10):
            AssessmentFactory()

        firm = AuditPartnerFactory(name="Auditor")
        assessment = AssessmentFactory()
        AssessorFactory(assessment=assessment, auditor_firm=firm)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"q": firm.name[:5]},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_user_first_name(self):
        for _ in range(10):
            AssessmentFactory()

        user = UserFactory(first_name="User First")
        assessment = AssessmentFactory()
        AssessorFactory(assessment=assessment, user=user)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"q": user.first_name[:5]},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_user_last_name(self):
        for _ in range(10):
            AssessmentFactory()

        user = UserFactory(last_name="User Last")
        assessment = AssessmentFactory()
        AssessorFactory(assessment=assessment, user=user)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"q": user.last_name[:5]},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sort_reference_number_asc(self):
        for _ in range(10):
            AssessmentFactory()

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"sort": "reference_number.asc"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), Assessment.objects.count())
        self.assertEqual(
            data[0]["id"],
            Assessment.objects.order_by("reference_number").first().pk,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sort_reference_number_desc(self):
        for _ in range(10):
            AssessmentFactory()

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"sort": "reference_number.desc"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), Assessment.objects.count())
        self.assertEqual(
            data[0]["id"],
            Assessment.objects.order_by("-reference_number").first().pk,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sort_assessment_date_asc(self):
        date = datetime.date.today()
        for i in range(10):
            AssessmentFactory(
                assessment_date=date + datetime.timedelta(days=i),
            )

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"sort": "assessment_date.asc"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), Assessment.objects.count())
        self.assertEqual(
            data[0]["id"],
            Assessment.objects.order_by("assessment_date").first().pk,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sort_assessment_date_desc(self):
        date = datetime.date.today()
        for i in range(10):
            AssessmentFactory(
                assessment_date=date + datetime.timedelta(days=i),
            )

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"sort": "assessment_date.desc"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), Assessment.objects.count())
        self.assertEqual(
            data[0]["id"],
            Assessment.objects.order_by("-assessment_date").first().pk,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sort_partner_name_asc(self):
        for _ in range(10):
            partner = PartnerFactory()
            AssessmentFactory(partner=partner)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"sort": "partner_name.asc"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), Assessment.objects.count())
        self.assertEqual(
            data[0]["id"],
            Assessment.objects.order_by("partner__organization__name").first().pk,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sort_partner_name_desc(self):
        for _ in range(10):
            partner = PartnerFactory()
            AssessmentFactory(partner=partner)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"sort": "partner_name.desc"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), Assessment.objects.count())
        self.assertEqual(
            data[0]["id"],
            Assessment.objects.order_by("-partner__organization__name").first().pk,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sort_multiple(self):
        for _ in range(10):
            partner = PartnerFactory()
            AssessmentFactory(partner=partner)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"sort": "reference_number.desc|partner_name.asc"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), Assessment.objects.count())
        self.assertEqual(
            data[0]["id"],
            Assessment.objects.order_by(
                "-reference_number",
                "partner__organization__name",
            ).first().pk,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_post(self):
        partner = PartnerFactory()
        assessment_qs = Assessment.objects.filter(partner=partner)
        self.assertFalse(assessment_qs.exists())
        date = timezone.now().date()

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessment-list'),
            user=self.focal_user,
            data={
                "partner": partner.pk,
                "focal_points": [self.user.pk],
                "assessment_date": date,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessment_qs.exists())
        assessment = assessment_qs.first()
        self.assertIsNotNone(assessment.reference_number)
        self.assertEqual(assessment.assessment_date, date)
        self.assertEqual(assessment.status, Assessment.STATUS_DRAFT)
        self.assertIn(self.user, assessment.focal_points.all())

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_post_assessment_date(self):
        partner = PartnerFactory()
        assessment_qs = Assessment.objects.filter(partner=partner)
        self.assertFalse(assessment_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessment-list'),
            user=self.focal_user,
            data={
                "partner": partner.pk,
                "focal_points": [self.user.pk],
                "assessment_date": "",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessment_qs.exists())
        assessment = assessment_qs.first()
        self.assertIsNotNone(assessment.reference_number)
        self.assertIsNone(assessment.assessment_date)
        self.assertEqual(assessment.status, Assessment.STATUS_DRAFT)
        self.assertIn(self.user, assessment.focal_points.all())

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_post_permission(self):
        partner = PartnerFactory()
        assessment_qs = Assessment.objects.filter(partner=partner)
        self.assertFalse(assessment_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessment-list'),
            user=self.user,
            data={
                "partner": partner.pk,
                "focal_points": [self.user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_validation(self):
        partner_1 = PartnerFactory()
        partner_2 = PartnerFactory()
        assessment = AssessmentFactory(partner=partner_1)

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=self.user,
            data={
                "partner": partner_2.pk
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assessment.refresh_from_db()
        self.assertEqual(assessment.partner, partner_1)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_patch(self):
        partner_1 = PartnerFactory()
        partner_2 = PartnerFactory()
        assessment = AssessmentFactory(partner=partner_1)
        assessment.focal_points.set([self.user])
        user = UserFactory()

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=self.focal_user,
            data={
                "partner": partner_2.pk,
                "focal_points": [user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessment.refresh_from_db()
        self.assertEqual(assessment.partner, partner_2)
        self.assertEqual(list(assessment.focal_points.all()), [user])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_patch_assessment_date(self):
        assessment = AssessmentFactory(assessment_date=None)
        assessment.status = Assessment.STATUS_IN_PROGRESS
        assessment.save()
        assessor = AssessorFactory(assessment=assessment)
        date = timezone.now().date()
        self.assertIsNone(assessment.assessment_date)

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=assessor.user,
            data={
                "assessment_date": date,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessment.refresh_from_db()
        self.assertEqual(assessment.assessment_date, date)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_assign(self):
        assessment = AssessmentFactory(partner=self.partner)
        self.assertEqual(assessment.status, assessment.STATUS_DRAFT)
        AssessorFactory(assessment=assessment)
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-assign", args=[assessment.pk]),
                user=self.focal_user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            assessment.STATUS_IN_PROGRESS,
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)
        self.assertEqual(mock_send.call_count, 2)

        # no subsequent assign requests allowed
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-assign", args=[assessment.pk]),
                user=self.focal_user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)
        self.assertEqual(mock_send.call_count, 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_assign_staff_member_required(self):
        assessment = AssessmentFactory(partner=self.partner)
        self.assertEqual(assessment.status, assessment.STATUS_DRAFT)
        firm = AuditPartnerFactory()
        staff = AuditorStaffMemberFactory(auditor_firm=firm)
        assessor = AssessorFactory(
            assessment=assessment,
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=firm,
        )
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-assign", args=[assessment.pk]),
                user=self.focal_user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock_send.call_count, 0)

        assessor.auditor_firm_staff.add(staff)

        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-assign", args=[assessment.pk]),
                user=self.focal_user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            assessment.STATUS_IN_PROGRESS,
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)
        self.assertEqual(mock_send.call_count, 2)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_submit(self):
        assessment = AssessmentFactory(
            partner=self.partner,
            assessment_date=None,
        )
        assessment.status = assessment.STATUS_IN_PROGRESS
        assessment.save()
        assessment.focal_points.add(self.focal_user)
        AnswerFactory(assessment=assessment)
        AssessorFactory(assessment=assessment)
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)
        self.assertIsNone(assessment.assessment_date)

        # check that assessment date required
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-submit", args=[assessment.pk]),
                user=self.focal_user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(mock_send.called)

        assessment.assessment_date = timezone.now().date()
        assessment.save()
        self.assertIsNotNone(assessment.assessment_date)

        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-submit", args=[assessment.pk]),
                user=self.focal_user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            response.data.get("status"),
            assessment.STATUS_SUBMITTED,
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)
        self.assertIsNotNone(assessment.assessment_date)
        self.assertEqual(mock_send.call_count, 1)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_finalize(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_SUBMITTED
        assessment.save()
        AnswerFactory(assessment=assessment)
        AssessorFactory(assessment=assessment)
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-finalize", args=[assessment.pk]),
                user=self.focal_user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            assessment.STATUS_FINAL,
        )
        self.assertFalse(response.data["permissions"]["edit"]["info_card"])
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_FINAL)
        self.assertEqual(mock_send.call_count, 1)

        # ensure notification not sent again, on subsequent finalize call
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-finalize", args=[assessment.pk]),
                user=self.focal_user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock_send.call_count, 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_cancel(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_IN_PROGRESS
        assessment.save()
        AnswerFactory(assessment=assessment)
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)
        response = self.forced_auth_req(
            "patch",
            reverse("psea:assessment-cancel", args=[assessment.pk]),
            user=self.focal_user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            assessment.STATUS_CANCELLED,
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_CANCELLED)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_cancel_assessor(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_IN_PROGRESS
        assessment.save()
        AnswerFactory(assessment=assessment)
        user = UserFactory()
        AssessorFactory(assessment=assessment, user=user)
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)
        response = self.forced_auth_req(
            "patch",
            reverse("psea:assessment-cancel", args=[assessment.pk]),
            user=user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_reject(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_SUBMITTED
        assessment.save()
        AssessorFactory(assessment=assessment)
        AnswerFactory(assessment=assessment)
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)
        history_qs = AssessmentStatusHistory.objects.filter(
            assessment=assessment,
        )
        status_count = history_qs.count()
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-reject", args=[assessment.pk]),
                user=self.focal_user,
                data={"comment": "Test reject"},
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            assessment.STATUS_REJECTED,
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_REJECTED)
        self.assertEqual(history_qs.count(), status_count + 1)
        history = history_qs.first()
        self.assertNotEqual(history.comment, "")
        self.assertEqual(mock_send.call_count, 1)

        # check that subsequent reject requests are not valid
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-reject", args=[assessment.pk]),
                user=self.focal_user,
                data={"comment": "Test reject"},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock_send.call_count, 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_reject_validation(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_SUBMITTED
        assessment.save()
        AssessorFactory(assessment=assessment)
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)
        history_qs = AssessmentStatusHistory.objects.filter(
            assessment=assessment,
        )
        status_count = history_qs.count()
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("psea:assessment-reject", args=[assessment.pk]),
                user=self.focal_user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)
        self.assertEqual(history_qs.count(), status_count)
        self.assertEqual(mock_send.call_count, 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list_export_csv(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.focal_points.set([self.user])
        response = self.forced_auth_req(
            "get",
            reverse("psea:assessment-list-export-csv"),
            user=self.focal_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            isinstance(
                response.accepted_renderer,
                renderers.ExportCSVRenderer,
            )
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_get_export_csv(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.focal_points.set([self.user])
        response = self.forced_auth_req(
            "get",
            reverse(
                "psea:assessment-single-export-csv",
                args=[assessment.pk],
            ),
            user=self.focal_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            isinstance(
                response.accepted_renderer,
                renderers.ExportCSVRenderer,
            )
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list_export_xlsx(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.focal_points.set([self.user])
        response = self.forced_auth_req(
            "get",
            reverse("psea:assessment-list-export-xlsx"),
            user=self.focal_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            isinstance(
                response.accepted_renderer,
                renderers.ExportOpenXMLRenderer,
            )
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_get_export_xlsx(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.focal_points.set([self.user])
        response = self.forced_auth_req(
            "get",
            reverse(
                "psea:assessment-single-export-xlsx",
                args=[assessment.pk],
            ),
            user=self.focal_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            isinstance(
                response.accepted_renderer,
                renderers.ExportOpenXMLRenderer,
            )
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_answer_permissions(self):
        assessment = AssessmentFactory(partner=self.partner)
        AssessorFactory(
            assessment=assessment,
            user=self.user,
            assessor_type=Assessor.TYPE_UNICEF,
        )
        for assessment_status in Assessment.STATUS_CHOICES:
            assessment.status = assessment_status
            assessment.save()
            response = self.forced_auth_req(
                "get",
                reverse("psea:assessment-detail", args=[assessment.pk]),
                user=self.user,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            perm = response.data["permissions"]["edit"]["answers"]

            if assessment.status == Assessment.STATUS_IN_PROGRESS:
                self.assertTrue(perm)
            else:
                self.assertFalse(perm)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_focal_point_permissions(self):
        assessment = AssessmentFactory(partner=self.partner)
        self.assertNotIn(self.user, assessment.focal_points.all())

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=self.user,
            data={
                "focal_points": [self.user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessment.refresh_from_db()
        self.assertIn(self.user, assessment.focal_points.all())

        # change user to external and attempt to add/change
        # focal points for assessment
        external_user = UserFactory()
        AssessorFactory(
            assessment=assessment,
            assessor_type=Assessor.TYPE_EXTERNAL,
            user=external_user,
        )
        assessment.status = Assessment.STATUS_IN_PROGRESS
        assessment.save()
        self.assertEqual(assessment.status, Assessment.STATUS_IN_PROGRESS)
        self.assertNotIn(self.focal_user, assessment.focal_points.all())
        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=external_user,
            data={
                "focal_points": [self.focal_user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assessment.refresh_from_db()
        self.assertNotIn(self.focal_user, assessment.focal_points.all())

        # change assessment status to FINAL and attempt to add/change
        # focal points for assessment
        assessment.status = Assessment.STATUS_FINAL
        assessment.save()
        AnswerFactory(assessment=assessment)
        self.assertEqual(assessment.status, Assessment.STATUS_FINAL)
        self.assertNotIn(self.focal_user, assessment.focal_points.all())
        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=self.user,
            data={
                "focal_points": [self.focal_user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assessment.refresh_from_db()
        self.assertNotIn(self.focal_user, assessment.focal_points.all())


class TestAssessmentActionPointViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_psea_permissions', verbosity=0)
        call_command('update_notifications')
        cls.send_path = "etools.applications.action_points.models.send_notification_with_template"
        cls.focal_user = UserFactory()
        cls.focal_user.groups.add(
            GroupFactory(name=UNICEFAuditFocalPoint.name),
        )
        cls.unicef_user = UserFactory()
        cls.unicef_user.groups.add(
            GroupFactory(name="UNICEF User"),
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_action_point_added(self):
        assessment = AssessmentFactory()
        assessment.status = Assessment.STATUS_FINAL
        assessment.save()
        assessment.focal_points.set([self.focal_user])
        AssessorFactory(assessment=assessment)
        self.assertEqual(assessment.action_points.count(), 0)

        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                'post',
                reverse("psea:action-points-list", args=[assessment.pk]),
                user=self.focal_user,
                data=self._get_post_payload()
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(assessment.action_points.count(), 1)
        self.assertIsNotNone(assessment.action_points.first().partner)
        self.assertTrue(mock_send)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_action_point_added_no_assessor(self):
        assessment = AssessmentFactory()
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                'post',
                reverse("psea:action-points-list", args=[assessment.pk]),
                user=self.focal_user,
                data=self._get_post_payload()
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(assessment.action_points.count(), 1)
        self.assertIsNotNone(assessment.action_points.first().partner)
        self.assertTrue(mock_send)

    def _get_post_payload(self):
        return {
            'description': fuzzy.FuzzyText(length=100).fuzz(),
            'due_date': fuzzy.FuzzyDate(
                timezone.now().date(),
                timezone.now().date() + datetime.timedelta(days=5)
            ).fuzz(),
            'assigned_to': self.unicef_user.pk,
            'office': self.focal_user.profile.tenant_profile.office.pk,
            'section': SectionFactory().pk,
        }

    def _test_action_point_editable(self, action_point, user, editable=True):
        assessment = action_point.psea_assessment

        response = self.forced_auth_req(
            'options',
            reverse(
                "psea:action-points-detail",
                args=[assessment.pk, action_point.pk],
            ),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if editable:
            self.assertIn('PUT', response.data['actions'].keys())
            self.assertCountEqual(
                sorted([
                    'assigned_to',
                    'high_priority',
                    'due_date',
                    'description',
                    'office',
                    'section',
                ]),
                sorted(response.data['actions']['PUT'].keys())
            )
        else:
            self.assertNotIn('PUT', response.data['actions'].keys())

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_action_point_editable_by_focal_user(self):
        assessment = AssessmentFactory()
        action_point = ActionPointFactory(
            psea_assessment=assessment,
            status='pre_completed',
        )

        self._test_action_point_editable(action_point, self.focal_user)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_action_point_readonly_by_unicef_user(self):
        assessment = AssessmentFactory()
        action_point = ActionPointFactory(
            psea_assessment=assessment,
            status='pre_completed',
        )

        self._test_action_point_editable(
            action_point,
            self.unicef_user,
            editable=False,
        )


class TestAssessorViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user.groups.add(GroupFactory(name=UNICEFAuditFocalPoint.name))
        cls.unicef_user = UserFactory(email="staff@unicef.org")

    def _validate_assessor(self, assessor, expected):
        self.assertEqual(assessor.assessor_type, expected.get("assessor_type"))
        self.assertEqual(assessor.user, expected.get("user"))
        self.assertEqual(assessor.auditor_firm, expected.get("auditor_firm"))
        if assessor.auditor_firm:
            self.assertEqual(
                assessor.auditor_firm.name,
                expected.get("auditor_firm_name"),
            )
        self.assertEqual(assessor.order_number, expected.get("order_number"))

    def test_get(self):
        assessor = AssessorFactory()
        response = self.forced_auth_req(
            "get",
            reverse('psea:assessor-list', args=[assessor.assessment.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], assessor.pk)

    def test_get_empty(self):
        assessment = AssessmentFactory()
        response = self.forced_auth_req(
            "get",
            reverse('psea:assessor-list', args=[assessment.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_unicef(self):
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list', args=[assessment.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_UNICEF,
                "user": self.unicef_user.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessor_qs.exists())
        assessor = assessor_qs.first()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_UNICEF,
            "user": self.unicef_user,
            "auditor_firm": None,
            "order_number": "",
        })

    def test_post_external(self):
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list', args=[assessment.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_EXTERNAL,
                "user": self.user.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessor_qs.exists())
        assessor = assessor_qs.first()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_EXTERNAL,
            "user": self.user,
            "auditor_firm": None,
            "order_number": "",
        })

    def test_post_vendor(self):
        firm = AuditPartnerFactory()
        purchase_order = PurchaseOrderFactory(auditor_firm=firm)
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list', args=[assessment.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_VENDOR,
                "auditor_firm": firm.pk,
                "order_number": purchase_order.order_number,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessor_qs.exists())
        assessor = assessor_qs.first()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_VENDOR,
            "user": None,
            "auditor_firm": firm,
            "auditor_firm_name": firm.name,
            "order_number": purchase_order.order_number,
        })

    def test_post_permission(self):
        firm = AuditPartnerFactory()
        purchase_order = PurchaseOrderFactory(auditor_firm=firm)
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list', args=[assessment.pk]),
            user=self.unicef_user,
            data={
                "assessor_type": Assessor.TYPE_VENDOR,
                "auditor_firm": firm.pk,
                "order_number": purchase_order.order_number,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Assessor cannot be changed", response.data[0])
        self.assertFalse(assessor_qs.exists())

    def test_patch_vendor(self):
        firm_1 = AuditPartnerFactory()
        firm_2 = AuditPartnerFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=firm_1,
            order_number="123",
        )

        response = self.forced_auth_req(
            "patch",
            reverse(
                'psea:assessor-detail',
                args=[assessor.assessment.pk, assessor.pk],
            ),
            user=self.user,
            data={
                "auditor_firm": firm_2.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        self.assertEqual(assessor.auditor_firm, firm_2)

    def test_patch_vendor_staff(self):
        firm = AuditPartnerFactory()
        staff_1 = AuditorStaffMemberFactory(auditor_firm=firm)
        staff_2 = AuditorStaffMemberFactory(auditor_firm=firm)
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=firm,
            order_number="123",
        )
        self.assertEqual(list(assessor.auditor_firm_staff.all()), [])

        response = self.forced_auth_req(
            "patch",
            reverse(
                'psea:assessor-detail',
                args=[assessor.assessment.pk, assessor.pk],
            ),
            user=self.user,
            data={
                "auditor_firm_staff": [staff_1.pk, staff_2.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        staff = assessor.auditor_firm_staff.all()
        self.assertEqual(len(staff), 2)
        self.assertIn(staff_1, staff)
        self.assertIn(staff_2, staff)

    def test_patch_vendor_to_unicef(self):
        firm = AuditPartnerFactory()
        staff_1 = AuditorStaffMemberFactory(auditor_firm=firm)
        staff_2 = AuditorStaffMemberFactory(auditor_firm=firm)
        assessment = AssessmentFactory()
        assessor = AssessorFactory(
            assessment=assessment,
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=firm,
            order_number="123",
        )
        assessor.auditor_firm_staff.set([staff_1, staff_2])

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessor-detail', args=[assessment.pk, assessor.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_UNICEF,
                "user": self.unicef_user.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_UNICEF,
            "user": self.unicef_user,
            "order_number": "",
        })
        self.assertEqual(list(assessor.auditor_firm_staff.all()), [])

    def test_patch_unicef_to_vendor(self):
        firm = AuditPartnerFactory()
        purchase_order = PurchaseOrderFactory(auditor_firm=firm)
        staff_1 = AuditorStaffMemberFactory(auditor_firm=firm)
        staff_2 = AuditorStaffMemberFactory(auditor_firm=firm)
        assessment = AssessmentFactory()
        assessor = AssessorFactory(
            assessment=assessment,
            assessor_type=Assessor.TYPE_UNICEF,
            user=self.user,
        )

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessor-detail', args=[assessment.pk, assessor.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_VENDOR,
                "auditor_firm": firm.pk,
                "order_number": purchase_order.order_number,
                "auditor_firm_staff": [staff_1.pk, staff_2.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_VENDOR,
            "order_number": purchase_order.order_number,
            "auditor_firm": firm,
            "auditor_firm_name": firm.name,
        })
        staff = assessor.auditor_firm_staff.all()
        self.assertEqual(len(staff), 2)
        self.assertIn(staff_1, staff)
        self.assertIn(staff_2, staff)

    def test_patch_permission(self):
        firm_1 = AuditPartnerFactory()
        firm_2 = AuditPartnerFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=firm_1,
            order_number="123",
        )

        response = self.forced_auth_req(
            "patch",
            reverse(
                'psea:assessor-detail',
                args=[assessor.assessment.pk, assessor.pk],
            ),
            user=self.unicef_user,
            data={
                "auditor_firm": firm_2.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Assessor cannot be changed", response.data[0])


class TestIndicatorViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.rating_high = RatingFactory(label="High", weight=10)
        cls.rating_medium = RatingFactory(label="Medium", weight=20)
        cls.rating_low = RatingFactory(label="Low", weight=30)
        cls.rating_inactive = RatingFactory(
            label="InActive",
            weight=100,
            active=False,
        )
        cls.evidence_1 = EvidenceFactory(label="Evidence 1")
        cls.evidence_2 = EvidenceFactory(label="Evidence 2")
        cls.evidence_inactive = EvidenceFactory(
            label="Evidence InActive",
            active=False,
        )
        cls.indicator = IndicatorFactory()
        cls.indicator.ratings.set([
            cls.rating_high,
            cls.rating_medium,
            cls.rating_low,
            cls.rating_inactive
        ])
        cls.indicator.evidences.set([
            cls.evidence_1,
            cls.evidence_2,
            cls.evidence_inactive,
        ])
        cls.indicator_inactive = IndicatorFactory(active=False)

    def test_list(self):
        indicator_qs = Indicator.objects.filter(active=True)
        response = self.forced_auth_req(
            "get",
            reverse("psea:indicator-list"),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(len(data), indicator_qs.count())
        self.assertNotIn(
            self.rating_inactive.pk,
            [r["id"] for d in data for r in d["ratings"]],
        )
        self.assertNotIn(
            self.evidence_inactive.pk,
            [e["id"] for d in data for e in d["evidences"]],
        )


class TestAnswerListViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.assessment = AssessmentFactory()
        cls.file_type = AttachmentFileTypeFactory(group=["psea_answer"])
        cls.indicator = IndicatorFactory()
        cls.rating = RatingFactory()
        cls.indicator.ratings.add(cls.rating)
        cls.evidence = EvidenceFactory()
        cls.indicator.evidences.add(cls.evidence)
        cls.content_type = ContentType.objects.get_for_model(Answer)

    def test_list(self):
        answer = AnswerFactory(assessment=self.assessment)
        answer_count = Answer.objects.filter(
            assessment=self.assessment,
        ).count()
        response = self.forced_auth_req(
            "get",
            reverse("psea:answer-list-list", args=[self.assessment.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), answer_count)
        self.assertEqual(response.data[0]["id"], answer.pk)


class TestAnswerViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.assessment = AssessmentFactory()
        cls.assessment.status = Assessment.STATUS_IN_PROGRESS
        cls.assessment.save()
        cls.file_type = AttachmentFileTypeFactory(group=["psea_answer"])
        cls.indicator = IndicatorFactory()
        cls.rating = RatingFactory()
        cls.indicator.ratings.add(cls.rating)
        cls.evidence = EvidenceFactory()
        cls.indicator.evidences.add(cls.evidence)
        cls.content_type = ContentType.objects.get_for_model(Answer)

    def test_post(self):
        attachment_1 = AttachmentFactory(file="sample_1.pdf")
        attachment_2 = AttachmentFactory(file="sample_2.pdf")
        AssessorFactory(assessment=self.assessment, user=self.user)
        self.assertTrue(self.assessment.user_belongs(self.user))
        answer_qs = Answer.objects.filter(assessment=self.assessment)
        self.assertFalse(answer_qs.exists())
        response = self.forced_auth_req(
            "post",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
            data={
                "evidences": [
                    {"evidence": self.evidence.pk},
                ],
                "attachments": [
                    {"id": attachment_1.pk, "file_type": self.file_type.pk},
                    {"id": attachment_2.pk, "file_type": self.file_type.pk},
                ],
                "comments": "Sample comment",
                "rating": self.rating.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(answer_qs.exists())
        answer = answer_qs.first()
        self.assertEqual(answer.indicator, self.indicator)
        self.assertEqual(answer.rating, self.rating)
        self.assertEqual(len(answer.evidences.all()), 1)
        answer_evidence = answer.evidences.first()
        self.assertEqual(answer_evidence.evidence, self.evidence)
        self.assertEqual(len(answer.attachments.all()), 2)

    def test_post_validation(self):
        evidence = EvidenceFactory(requires_description=True)
        self.indicator.evidences.add(evidence)
        AssessorFactory(assessment=self.assessment, user=self.user)
        self.assertTrue(self.assessment.user_belongs(self.user))
        answer_qs = Answer.objects.filter(assessment=self.assessment)
        self.assertFalse(answer_qs.exists())
        response = self.forced_auth_req(
            "post",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
            data={
                "evidences": [
                    {"evidence": self.evidence.pk},
                    {"evidence": evidence.pk},
                ],
                "comments": "Sample comment",
                "rating": self.rating.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("evidences", response.data)
        self.assertFalse(answer_qs.exists())

    def test_get(self):
        answer = AnswerFactory(
            assessment=self.assessment,
            indicator=self.indicator,
            rating=self.rating,
        )
        AnswerEvidenceFactory(answer=answer, evidence=self.evidence)
        AttachmentFactory(
            file="sample_1.pdf",
            file_type=self.file_type,
            object_id=answer.pk,
            content_type=self.content_type,
            code="psea_answer",
        )
        AttachmentFactory(
            file="sample_2.pdf",
            file_type=self.file_type,
            object_id=answer.pk,
            content_type=self.content_type,
            code="psea_answer",
        )
        response = self.forced_auth_req(
            "get",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], answer.pk)
        self.assertEqual(len(data["evidences"]), 1)
        self.assertEqual(len(data["attachments"]), 2)

    def test_put(self):
        answer = AnswerFactory(
            assessment=self.assessment,
            indicator=self.indicator,
            rating=self.rating,
            comments="Initial comment",
        )
        AnswerEvidenceFactory(answer=answer, evidence=self.evidence)
        response = self.forced_auth_req(
            "put",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
            data={
                "indicator": self.indicator.pk,
                "evidences": [
                    {"evidence": self.evidence.pk},
                ],
                "comments": "Changed comment",
                "rating": self.rating.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        answer.refresh_from_db()
        self.assertEqual(answer.comments, "Changed comment")

    def test_patch(self):
        answer = AnswerFactory(
            assessment=self.assessment,
            indicator=self.indicator,
            rating=self.rating,
            comments="Initial comment",
        )
        attachment_1 = AttachmentFactory(
            file="sample_1.pdf",
            file_type=self.file_type,
            object_id=answer.pk,
            content_type=self.content_type,
            code="psea_answer",
        )
        AnswerEvidenceFactory(answer=answer, evidence=self.evidence)
        attachment_2 = AttachmentFactory(
            file="sample_2.pdf",
            file_type=self.file_type,
        )
        evidence = EvidenceFactory()
        self.indicator.evidences.add(evidence)
        self.assertEqual(len(answer.evidences.all()), 1)
        self.assertEqual(len(answer.attachments.all()), 1)
        response = self.forced_auth_req(
            "patch",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
            data={
                "indicator": self.indicator.pk,
                "evidences": [
                    {"evidence": self.evidence.pk},
                    {"evidence": evidence.pk},
                ],
                "attachments": [
                    {"id": attachment_1.pk, "file_type": self.file_type.pk},
                    {"id": attachment_2.pk, "file_type": self.file_type.pk},
                ]
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        answer.refresh_from_db()
        self.assertEqual(len(answer.evidences.all()), 2)
        attachments = list(answer.attachments.all())
        self.assertEqual(len(attachments), 2)
        self.assertIn(attachment_1, attachments)
        self.assertIn(attachment_2, attachments)

    def test_delete(self):
        answer = AnswerFactory(
            assessment=self.assessment,
            indicator=self.indicator,
            rating=self.rating,
        )
        AnswerEvidenceFactory(answer=answer, evidence=self.evidence)
        answer_qs = Answer.objects.filter(pk=answer.pk)
        self.assertTrue(answer_qs.exists())
        response = self.forced_auth_req(
            "delete",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(answer_qs.exists())

    def test_permission(self):
        focal_user = UserFactory()
        self.assessment.focal_points.add(focal_user)
        answer = AnswerFactory(
            assessment=self.assessment,
            indicator=self.indicator,
            rating=self.rating,
            comments="Initial comment",
        )
        AnswerEvidenceFactory(answer=answer, evidence=self.evidence)
        response = self.forced_auth_req(
            "post",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=focal_user,
            data={
                "indicator": self.indicator.pk,
                "evidences": [
                    {"evidence": self.evidence.pk},
                ],
                "comments": "Changed comment",
                "rating": self.rating.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        answer.refresh_from_db()
        self.assertEqual(answer.comments, "Initial comment")


class TestAnswerAttachmentViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.file_type = AttachmentFileTypeFactory(group=["psea_answer"])
        cls.assessment = AssessmentFactory()
        cls.indicator = IndicatorFactory()
        cls.answer = AnswerFactory(
            assessment=cls.assessment,
            indicator=cls.indicator,
        )
        cls.user = UserFactory()

    def test_list(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Answer),
            object_id=self.answer.pk,
            code="psea_answer",
        )
        self.answer.attachments.add(attachment)
        attachment_count = self.answer.attachments.count()
        response = self.forced_auth_req(
            "get",
            reverse(
                "psea:answer-attachments-list",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), attachment_count)
        self.assertEqual(response.data[0]["id"], attachment.pk)

    def test_post(self):
        attachment = AttachmentFactory(file="sample.pdf")
        self.assertIsNone(attachment.object_id)
        self.assertNotEqual(attachment.code, "psea_answer")

        response = self.forced_auth_req(
            "post",
            reverse(
                "psea:answer-attachments-list",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
            data={
                "id": attachment.pk,
                "file_type": self.file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attachment.refresh_from_db()
        self.assertEqual(attachment.object_id, self.answer.pk)
        self.assertEqual(attachment.code, "psea_answer")

    def test_patch(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            code="psea_answer",
            content_type=ContentType.objects.get_for_model(Answer),
            object_id=self.answer.pk,
        )
        file_type = AttachmentFileTypeFactory(group=["psea_answer"])

        response = self.forced_auth_req(
            "patch",
            reverse(
                "psea:answer-attachments-detail",
                args=[self.assessment.pk, self.indicator.pk, attachment.pk],
            ),
            user=self.user,
            data={
                "id": attachment.pk,
                "file_type": file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachment.refresh_from_db()
        self.assertEqual(attachment.file_type, file_type)

    def test_delete(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            code="psea_answer",
            content_type=ContentType.objects.get_for_model(Answer),
            object_id=self.answer.pk,
        )
        attachment_qs = Attachment.objects.filter(pk=attachment.pk)
        self.assertTrue(attachment_qs.exists())

        response = self.forced_auth_req(
            "delete",
            reverse(
                "psea:answer-attachments-detail",
                args=[self.assessment.pk, self.indicator.pk, attachment.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(attachment_qs.exists())
