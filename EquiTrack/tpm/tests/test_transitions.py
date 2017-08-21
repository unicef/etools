from django.core.management import call_command

from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from tpm.models import TPMVisit
from .base import TPMTestCaseMixin


class TestTPMTransitions(TPMTestCaseMixin, APITenantTestCase):
    def setUp(self):
        super(TestTPMTransitions, self).setUp()
        call_command('update_tpm_permissions', verbosity=0)

    def _do_transition(self, visit, action, user, data={}):
        return self.forced_auth_req(
            'post',
            '/api/tpm/visits/{0}/{1}/'.format(visit.id, action),
            user=user,
            data=data
        )

    def _refresh_tpm_visit_instace(self, visit):
        # Calling refresh_from_db will cause an exception.
        return TPMVisit.objects.get(id=visit.id)

    def test_assign_without_perms(self):
        for user in [self.unicef_user, self.unicef_focal_point]:
            self.assertEquals(self.tpm_visit.status, 'draft')

            response = self._do_transition(self.tpm_visit, 'assign', user)
            self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
            self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEquals(self.tpm_visit.status, 'draft')

    def test_assign_without_activities(self):
        self.assertEquals(self.tpm_visit.status, 'draft')

        self.tpm_visit.tpm_activities.all().delete()

        response = self._do_transition(self.tpm_visit, 'assign', self.pme_user)

        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'draft')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_success_assign(self):
        self.assertEquals(self.tpm_visit.status, 'draft')
        response = self._do_transition(self.tpm_visit, 'assign', self.pme_user)
        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(self.tpm_visit.status, 'assigned')

    def test_success_cancel(self):
        self.assertEquals(self.tpm_visit.status, 'draft')
        response = self._do_transition(self.tpm_visit, 'cancel', self.pme_user)
        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(self.tpm_visit.status, 'cancelled')

    def test_tpm_accept_fails(self):
        self.test_success_assign()

        for user in [self.unicef_user, self.unicef_focal_point, self.pme_user]:
            response = self._do_transition(self.tpm_visit, 'accept', user)
            self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
            self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEquals(self.tpm_visit.status, 'assigned')

    def test_tpm_accept_success(self):
        self.test_success_assign()

        self.assertEquals(self.tpm_visit.status, 'assigned')
        response = self._do_transition(self.tpm_visit, 'accept', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_accepted')

    def test_tpm_report_without_report(self):
        self.test_tpm_accept_success()
        self.assertEquals(self.tpm_visit.status, 'tpm_accepted')
        response = self._do_transition(self.tpm_visit, 'send_report', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_accepted')

    def test_tpm_report_without_perms(self):
        self.test_tpm_accept_success()
        for user in [self.unicef_user, self.unicef_focal_point, self.pme_user]:
            self.assertEquals(self.tpm_visit.status, 'tpm_accepted')
            response = self._do_transition(self.tpm_visit, 'send_report', user)
            self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
            self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEquals(self.tpm_visit.status, 'tpm_accepted')

    def test_tpm_report_success(self):
        self.test_tpm_accept_success()
        self._add_attachment('report', self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_accepted')
        response = self._do_transition(self.tpm_visit, 'send_report', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_reported')

    def test_tpm_report_reject(self):
        self.test_tpm_report_success()
        self.assertEquals(self.tpm_visit.status, 'tpm_reported')
        self.assertEquals(self.tpm_visit.report_reject_comments.count(), 0)
        response = self._do_transition(self.tpm_visit, 'reject_report', self.pme_user, data={
            "reject_comment": 'Just because'
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_report_rejected')
        self.assertEquals(self.tpm_visit.report_reject_comments.count(), 1)

    def test_tpm_report_after_reject(self):
        self.test_tpm_report_reject()
        self._add_attachment('report', self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_report_rejected')
        response = self._do_transition(self.tpm_visit, 'send_report', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_reported')
