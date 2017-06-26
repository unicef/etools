from django.core.management import call_command

from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from tpm.models import TPMVisit
from utils.common.tests.mixins import AttachmentMixin
from .base import TPMTestCaseMixin
from .factories import TPMVisitFactory, TPMVisitReportFactory


class TestTPMTransitions(AttachmentMixin, TPMTestCaseMixin, APITenantTestCase):
    def setUp(self):
        super(TestTPMTransitions, self).setUp()
        call_command('update_tpm_permissions')

    def _do_transition(self, visit, action, user):
        return self.forced_auth_req(
            'post',
            '/api/tpm/visits/{0}/{1}/'.format(visit.id, action),
            user=user
        )

    def _refresh_tpm_visit_instace(self, visit):
        # Calling refresh_from_db will cause an exception.
        return TPMVisit.objects.get(id=visit.id)

    def test_submit_without_perms(self):
        for user in [self.unicef_user, self.unicef_focal_point, self.tpm_user]:
            self.assertEquals(self.tpm_visit.status, 'draft')

            response = self._do_transition(self.tpm_visit, 'submit', user)
            self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
            self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEquals(self.tpm_visit.status, 'draft')

    def test_submit_without_activities(self):
        self.assertEquals(self.tpm_visit.status, 'draft')

        self.tpm_visit.tpm_activities.all().delete()

        response = self._do_transition(self.tpm_visit, 'submit', self.pme_user)

        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'draft')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_success_submit(self):
        self.assertEquals(self.tpm_visit.status, 'draft')
        response = self._do_transition(self.tpm_visit, 'submit', self.pme_user)
        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(self.tpm_visit.status, 'submitted')

    def test_tpm_accept_fails(self):
        self.test_success_submit()

        for user in [self.unicef_user, self.unicef_focal_point, self.pme_user]:
            response = self._do_transition(self.tpm_visit, 'accept', user)
            self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
            self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEquals(self.tpm_visit.status, 'submitted')

    def test_tpm_accept_success(self):
        self.test_success_submit()

        self.assertEquals(self.tpm_visit.status, 'submitted')
        response = self._do_transition(self.tpm_visit, 'accept', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_accepted')

    def test_tpm_report_without_report(self):
        self.test_tpm_accept_success()
        self.assertEquals(self.tpm_visit.status, 'tpm_accepted')
        response = self._do_transition(self.tpm_visit, 'report', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_accepted')

    def test_tpm_report_without_perms(self):
        self.test_tpm_accept_success()
        for user in [self.unicef_user, self.unicef_focal_point, self.pme_user]:
            self.assertEquals(self.tpm_visit.status, 'tpm_accepted')
            response = self._do_transition(self.tpm_visit, 'report', user)
            self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
            self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEquals(self.tpm_visit.status, 'tpm_accepted')

    def test_tpm_report_success(self):
        self.test_tpm_accept_success()
        report = TPMVisitReportFactory(tpm_visit=self.tpm_visit)
        self._add_attachment('tpm_report', report)
        self.assertEquals(self.tpm_visit.status, 'tpm_accepted')
        response = self._do_transition(self.tpm_visit, 'report', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.tpm_visit = self._refresh_tpm_visit_instace(self.tpm_visit)
        self.assertEquals(self.tpm_visit.status, 'tpm_reported')
