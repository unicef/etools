import datetime

from django.contrib.admin.sites import AdminSite

from unicef_snapshot.models import Activity

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.admin import AgreementAdmin, InterventionAdmin, PartnerStaffMemberAdmin
from etools.applications.partners.models import Agreement, Intervention, PartnerStaffMember
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.reports.tests.factories import CountryProgrammeFactory
from etools.applications.users.tests.factories import UserFactory


class MockRequest:
    pass


class TestAdminCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.user = UserFactory()
        self.request = MockRequest()
        self.request.user = self.user


class TestInterventionAdmin(TestAdminCase):
    def test_save_model_create(self):
        self.assertFalse(Activity.objects.exists())
        agreement = AgreementFactory()
        ia = InterventionAdmin(Intervention, self.site)
        obj = Intervention(agreement=agreement)
        ia.save_model(self.request, obj, {}, False)
        self.assertTrue(
            Activity.objects.filter(action=Activity.CREATE).exists()
        )
        activity = Activity.objects.first()
        self.assertEqual(activity.target, obj)
        self.assertEqual(activity.by_user, self.user)
        self.assertEqual(activity.change, {})

    def test_save_model_update(self):
        self.assertFalse(Activity.objects.exists())
        ia = InterventionAdmin(Intervention, self.site)
        obj = InterventionFactory()
        title_before = obj.title
        obj.title = "Title Change"
        ia.save_model(self.request, obj, {}, True)
        self.assertTrue(
            Activity.objects.filter(action=Activity.UPDATE).exists()
        )
        activity = Activity.objects.first()
        self.assertEqual(activity.target, obj)
        self.assertEqual(activity.by_user, self.user)
        self.assertDictEqual(activity.change, {
            "title": {
                "before": title_before,
                "after": "Title Change"
            }
        })


# TODO REALMS clean up
class TestPartnerStaffMemberAdmin(TestAdminCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory()

    def test_save_model_create(self):
        self.assertFalse(Activity.objects.exists())
        obj = PartnerStaffMember(
            user=self.user,
            email="test@example.com",
            partner=self.partner,
        )
        sa = PartnerStaffMemberAdmin(PartnerStaffMember, self.site)
        sa.save_model(self.request, obj, {}, False)
        self.assertTrue(
            Activity.objects.filter(action=Activity.CREATE).exists()
        )
        activity = Activity.objects.first()
        self.assertEqual(activity.target, obj)
        self.assertEqual(activity.by_user, self.user)
        self.assertEqual(activity.change, {})


class TestAgreementAdmin(TestAdminCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory()

    def test_save_model_create(self):
        self.assertFalse(Activity.objects.exists())
        obj = Agreement(
            partner=self.partner,
            country_programme=CountryProgrammeFactory(),
            agreement_type=Agreement.PCA,
            reference_number_year=datetime.date.today().year
        )
        aa = AgreementAdmin(Agreement, self.site)
        aa.save_model(self.request, obj, {}, False)
        self.assertTrue(
            Activity.objects.filter(action=Activity.CREATE).exists()
        )
        activity = Activity.objects.first()
        self.assertEqual(activity.target, obj)
        self.assertEqual(activity.by_user, self.user)
        self.assertEqual(activity.change, {})

    def test_save_model_update(self):
        self.assertFalse(Activity.objects.exists())
        obj = AgreementFactory(partner=self.partner)
        status_before = obj.status
        obj.status = Agreement.TERMINATED
        aa = AgreementAdmin(Agreement, self.site)
        aa.save_model(self.request, obj, {}, True)
        self.assertTrue(
            Activity.objects.filter(action=Activity.UPDATE).exists()
        )
        activity = Activity.objects.first()
        self.assertEqual(activity.target, obj)
        self.assertEqual(activity.by_user, self.user)
        self.assertEqual(activity.change, {
            "status": {
                "before": status_before,
                "after": Agreement.TERMINATED
            }
        })
