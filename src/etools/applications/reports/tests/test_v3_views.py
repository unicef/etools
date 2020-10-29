import datetime

from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory, PartnerStaffFactory
from etools.applications.reports.models import Office, Section, SpecialReportingRequirement
from etools.applications.reports.tests.factories import (
    OfficeFactory,
    SectionFactory,
    SpecialReportingRequirementFactory,
)
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class BasePMPTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory()
        cls.partner_staff = cls.partner.staff_members.all().first()
        cls.partner_user = UserFactory(email=cls.partner_staff.email)
        cls.partner_user.profile.partner_staff_member = True
        cls.partner_user.profile.save()


class TestPMPOfficeViews(BasePMPTestCase):
    def test_list(self):
        for __ in range(10):
            OfficeFactory()
        office = OfficeFactory()
        pd = InterventionFactory()
        pd.offices.add(office)
        pd.partner_focal_points.add(self.partner_staff)

        url = reverse('offices-pmp-list')
        office_qs = Office.objects
        self.assertTrue(office_qs.count() > 10)

        # unicef staff
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), office_qs.count())

        # partner
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]["id"]), str(office.pk))

    def test_detail(self):
        office = OfficeFactory()

        # unicef staff
        url = reverse('offices-pmp-detail', args=[office.pk])
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # partner not associated
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # partner
        pd = InterventionFactory()
        pd.offices.add(office)
        pd.partner_focal_points.add(self.partner_staff)
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestPMPSectionViews(BasePMPTestCase):
    def test_list(self):
        for __ in range(10):
            SectionFactory()
        section = SectionFactory()
        pd = InterventionFactory()
        pd.sections.add(section)
        pd.partner_focal_points.add(self.partner_staff)

        url = reverse('sections-pmp-list')
        section_qs = Section.objects
        self.assertTrue(section_qs.count() > 10)

        # unicef staff
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), section_qs.count())

        # partner
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]["id"]), str(section.pk))

    def test_detail(self):
        section = SectionFactory()

        # unicef staff
        url = reverse('sections-pmp-detail', args=[section.pk])
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # partner not associated
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # partner
        pd = InterventionFactory()
        pd.sections.add(section)
        pd.partner_focal_points.add(self.partner_staff)
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestPMPSpecialReportingRequirementListCreateView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unicef_staff = UserFactory(is_staff=True)
        group = GroupFactory(name='Partnership Manager')
        cls.unicef_staff.groups.add(group)
        cls.intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            status=Intervention.DRAFT,
            in_amendment=True,
        )

        cls.url = reverse(
            "reports_v3:interventions-special-reporting-requirements",
            kwargs={'intervention_pk': cls.intervention.pk}
        )

    def test_get(self):
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=datetime.date(2001, 4, 15),
            description="Current",
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        data = response.data[0]
        self.assertEqual(data["id"], requirement.pk)
        self.assertEqual(data["intervention"], self.intervention.pk)
        self.assertEqual(data["due_date"], str(requirement.due_date))
        self.assertEqual(data["description"], "Current")

    def test_post(self):
        requirement_qs = SpecialReportingRequirement.objects.filter(
            intervention=self.intervention,
        )
        init_count = requirement_qs.count()
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={
                "due_date": datetime.date(2001, 4, 15),
                "description": "Randomness"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(requirement_qs.count(), init_count + 1)
        self.assertEqual(response.data["intervention"]['id'], self.intervention.pk)
        self.assertEqual(response.data["description"], "Randomness")

    def test_post_invalid_due_dates(self):
        due_date = datetime.date(2001, 4, 15)
        SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=due_date,
        )
        requirement_qs = SpecialReportingRequirement.objects.filter(
            intervention=self.intervention,
        )
        init_count = requirement_qs.count()
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={
                "due_date": due_date,
                "description": "Randomness"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(requirement_qs.count(), init_count)
        self.assertEqual(response.data, {
            "due_date": [
                "There is already a special report with this due date.",
            ]
        })

        due_date += datetime.timedelta(days=2)
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={
                "due_date": due_date,
                "description": "Randomness"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(requirement_qs.count(), init_count + 1)


class TestSpecialReportingRequirementRetrieveUpdateDestroyView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        group = GroupFactory(name='Partnership Manager')
        cls.unicef_staff.groups.add(group)

        cls.partner = PartnerFactory()
        cls.partner_focal_point = UserFactory(is_staff=False, groups__data=[])
        partner_focal_point_staff = PartnerStaffFactory(
            partner=cls.partner, email=cls.partner_focal_point.email
        )
        cls.partner_focal_point.profile.partner_staff_member = partner_focal_point_staff.id
        cls.partner_focal_point.profile.save()

        cls.intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            status=Intervention.DRAFT,
            in_amendment=True,
            agreement__partner=cls.partner,
            date_sent_to_partner=datetime.date.today()
        )
        cls.intervention.partner_focal_points.add(partner_focal_point_staff)

    def _get_url(self, requirement):
        return reverse(
            "reports_v3:interventions-special-reporting-requirements-update",
            args=[requirement.intervention.pk, requirement.pk]
        )

    def test_get(self):
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=datetime.date(2001, 4, 15),
            description="Current",
        )
        response = self.forced_auth_req(
            "get",
            self._get_url(requirement),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], requirement.pk)
        self.assertEqual(response.data["intervention"], self.intervention.pk)
        self.assertEqual(response.data["due_date"], str(requirement.due_date))
        self.assertEqual(response.data["description"], "Current")

    def test_patch(self):
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=datetime.date(2001, 4, 15),
            description="Old",
        )
        response = self.forced_auth_req(
            "patch",
            self._get_url(requirement),
            user=self.unicef_staff,
            data={
                "due_date": datetime.date(2001, 4, 15),
                "description": "New"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], "New")
        requirement_update = SpecialReportingRequirement.objects.get(
            pk=requirement.pk
        )
        self.assertEqual(requirement_update.description, "New")

    def test_patch_as_partner_staff(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        requirement = SpecialReportingRequirementFactory(intervention=self.intervention)
        response = self.forced_auth_req(
            "patch",
            self._get_url(requirement),
            user=self.partner_focal_point,
            data={
                "due_date": datetime.date(2001, 4, 15),
                "description": "New",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_invalid_old(self):
        """Cannot delete special reporting requirements in the past"""
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=datetime.date(2001, 4, 15),
            description="Old",
        )
        response = self.forced_auth_req(
            "delete",
            self._get_url(requirement),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            ["Cannot delete special reporting requirements in the past."]
        )
        self.assertTrue(SpecialReportingRequirement.objects.filter(
            pk=requirement.pk
        ).exists())

    def test_delete(self):
        date = datetime.date.today() + datetime.timedelta(days=10)
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=date,
            description="Old",
        )
        response = self.forced_auth_req(
            "delete",
            self._get_url(requirement),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SpecialReportingRequirement.objects.filter(
            pk=requirement.pk
        ).exists())
