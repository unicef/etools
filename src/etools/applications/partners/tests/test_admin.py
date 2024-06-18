import datetime

from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile

from unicef_snapshot.models import Activity

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.admin import AgreementAdmin, InterventionAdmin
from etools.applications.partners.models import Agreement, Intervention
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.reports.tests.factories import CountryProgrammeFactory
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, RealmFactory, UserFactory


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

    def test_revert_termination(self):
        RealmFactory(
            user=self.user,
            country=CountryFactory(),
            organization=self.user.profile.organization,
            group=GroupFactory(name='RSS')
        )

        agreement = AgreementFactory(
            partner=self.partner, status=Agreement.TERMINATED, end=datetime.date.today() + datetime.timedelta(days=7))
        a = AttachmentFactory(
            code='partners_agreement_termination_doc',
            content_object=agreement,
            file=SimpleUploadedFile('simple_file.txt', b'simple_file.txt'),
        )
        agreement.termination_doc.add(a)
        suspended_pd = InterventionFactory(
            agreement=agreement,
            title='Intervention 1',
            status=Intervention.SUSPENDED,
        )
        ia = InterventionAdmin(Intervention, self.site)
        suspended_pd.status = Intervention.TERMINATED
        ia.save_model(self.request, suspended_pd, {}, True)

        closed_pd = InterventionFactory(
            agreement=agreement,
            title='Intervention 1',
            status=Intervention.CLOSED,
        )
        closed_pd.status = Intervention.TERMINATED
        ia.save_model(self.request, closed_pd, {}, True)

        aa = AgreementAdmin(Agreement, self.site)
        aa.revert_termination(self.request, pk=agreement.pk)

        agreement.refresh_from_db()
        self.assertEqual(agreement.status, Agreement.SIGNED)
        self.assertEqual(agreement.termination_doc.count(), 0)

        suspended_pd.refresh_from_db()
        self.assertEqual(suspended_pd.status, Intervention.SUSPENDED)

        closed_pd.refresh_from_db()
        self.assertEqual(closed_pd.status, Intervention.TERMINATED)
