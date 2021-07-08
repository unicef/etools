from etools.applications.eface.tests.factories import EFaceFormFactory, FormActivityFactory
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase
from etools.applications.partners.tests.factories import PartnerStaffFactory
from etools.applications.users.tests.factories import UserFactory


class TestFormsView(APIViewSetTestCase):
    base_view = 'eface_v1:forms'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unicef_user = UserFactory()

    def test_list(self):
        forms = [
            EFaceFormFactory(),
            EFaceFormFactory(),
        ]
        self._test_list(self.unicef_user, forms)

    def test_partner_list(self):
        form1 = EFaceFormFactory()
        EFaceFormFactory()
        staff_member = PartnerStaffFactory()
        form1.intervention.partner_focal_points.add(staff_member)
        self._test_list(staff_member.user, [form1])

    def test_detail(self):
        form = EFaceFormFactory()
        self._test_retrieve(self.unicef_user, form)

    def test_update(self):
        form = EFaceFormFactory()
        staff_member = PartnerStaffFactory()
        form.intervention.partner_focal_points.add(staff_member)
        response = self._test_update(staff_member.user, form, {'title': 'new'})
        self.assertEqual(response.data['title'], 'new')
        form.refresh_from_db()
        self.assertEqual(form.title, 'new')


class TestFormActivitiesView(APIViewSetTestCase):
    base_view = 'eface_v1:form_activities'

    def get_list_args(self):
        return [self.form.pk]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unicef_user = UserFactory()
        cls.form = EFaceFormFactory()

    def test_list(self):
        activities = [FormActivityFactory(form=self.form), FormActivityFactory(form=self.form)]
        FormActivityFactory()
        self._test_list(self.unicef_user, activities)

    def test_update(self):
        activity = FormActivityFactory(form=self.form)
        staff_member = PartnerStaffFactory()
        activity.form.intervention.partner_focal_points.add(staff_member)
        response = self._test_update(staff_member.user, activity, {'description': 'new'})
        self.assertEqual(response.data['description'], 'new')
        activity.refresh_from_db()
        self.assertEqual(activity.description, 'new')

    def test_delete(self):
        activity = FormActivityFactory(form=self.form)
        staff_member = PartnerStaffFactory()
        activity.form.intervention.partner_focal_points.add(staff_member)
        self._test_destroy(staff_member.user, activity)
