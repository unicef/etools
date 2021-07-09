from etools.applications.eface.tests.factories import EFaceFormFactory, FormActivityFactory
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase
from etools.applications.partners.tests.factories import PartnerStaffFactory, InterventionFactory
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

    def test_create(self):
        staff_member = PartnerStaffFactory()
        self._test_create(
            staff_member.user,
            {
                'intervention': InterventionFactory(agreement__partner=staff_member.partner).pk,
                'title': 'test',
                'request_type': 'dct',
            }
        )

    def test_flow(self):
        form = EFaceFormFactory()
        staff_member = PartnerStaffFactory()
        form.intervention.partner_focal_points.add(staff_member)

        def goto(next_status, user, extra_data=None):
            data = {
                'status': next_status
            }
            if extra_data:
                data.update(extra_data)

            return self._test_update(user, form, data)

        response = goto('submitted', staff_member.user)
        self.assertEqual(response.data['status'], 'submitted')
        response = goto('draft', self.unicef_user)
        self.assertEqual(response.data['status'], 'draft')
        response = goto('submitted', staff_member.user)
        self.assertEqual(response.data['status'], 'submitted')
        response = goto('unicef_approved', self.unicef_user)
        self.assertEqual(response.data['status'], 'unicef_approved')
        response = goto('draft', self.unicef_user)
        self.assertEqual(response.data['status'], 'draft')
        response = goto('submitted', staff_member.user)
        self.assertEqual(response.data['status'], 'submitted')
        response = goto('unicef_approved', self.unicef_user)
        self.assertEqual(response.data['status'], 'unicef_approved')
        response = goto('finalized', self.unicef_user)
        self.assertEqual(response.data['status'], 'finalized')

    def test_bad_transition(self):
        form = EFaceFormFactory()
        self._test_update(self.unicef_user, form, {'status': 'finalized'}, expected_status=400)


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
