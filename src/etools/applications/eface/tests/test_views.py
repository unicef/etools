from rest_framework import status

from etools.applications.eface.tests.factories import EFaceFormFactory, FormActivityFactory
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import InterventionActivityFactory, ResultFactory
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

    def test_detail_pd_activities_presented(self):
        form = EFaceFormFactory()
        activity = InterventionActivityFactory(
            result__result_link=InterventionResultLinkFactory(
                intervention=form.intervention,
                cp_output=ResultFactory(result_type__name=ResultType.OUTPUT),
            ),
        )
        response = self._test_retrieve(self.unicef_user, form)
        self.assertEqual(
            response.data['intervention']['result_links'][0]['ll_results'][0]['activities'][0]['id'],
            activity.id
        )

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
        form.intervention.unicef_focal_points.add(self.unicef_user)

        def goto(next_status, user, extra_data=None):
            data = {
                'status': next_status
            }
            if extra_data:
                data.update(extra_data)

            return self._test_update(user, form, data)

        response = goto('submitted', staff_member.user)
        self.assertEqual(response.data['status'], 'submitted')
        response = goto('rejected', self.unicef_user)
        self.assertEqual(response.data['status'], 'rejected')
        response = goto('submitted', staff_member.user)
        self.assertEqual(response.data['status'], 'submitted')
        response = goto('pending', self.unicef_user)
        self.assertEqual(response.data['status'], 'pending')
        response = goto('approved', self.unicef_user)
        self.assertEqual(response.data['status'], 'approved')

    def test_bad_transition(self):
        form = EFaceFormFactory()
        form.intervention.unicef_focal_points.add(self.unicef_user)
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

    def test_create(self):
        staff_member = PartnerStaffFactory()
        self.form.intervention.partner_focal_points.add(staff_member)
        self._test_create(
            staff_member.user,
            {
                'kind': 'custom',
                'description': 'test',
            }
        )

    def test_create_activity_required(self):
        staff_member = PartnerStaffFactory()
        self.form.intervention.partner_focal_points.add(staff_member)
        self._test_create(
            staff_member.user,
            {
                'kind': 'activity',
            },
            expected_status=status.HTTP_400_BAD_REQUEST,
            field_errors=['non_field_errors']
        )

    def test_list(self):
        activities = [FormActivityFactory(form=self.form), FormActivityFactory(form=self.form)]
        FormActivityFactory()
        self._test_list(self.unicef_user, activities)

    def test_update(self):
        activity = FormActivityFactory(form=self.form)
        staff_member = PartnerStaffFactory()
        self.form.intervention.partner_focal_points.add(staff_member)
        response = self._test_update(staff_member.user, activity, {'description': 'new'})
        self.assertEqual(response.data['description'], 'new')
        activity.refresh_from_db()
        self.assertEqual(activity.description, 'new')

    def test_delete(self):
        activity = FormActivityFactory(form=self.form)
        staff_member = PartnerStaffFactory()
        self.form.intervention.partner_focal_points.add(staff_member)
        self._test_destroy(staff_member.user, activity)
