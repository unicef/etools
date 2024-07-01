
from django.core.management import call_command
from django.urls import reverse
from django.utils.translation import gettext as _

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.permissions2.tests.mixins import TransitionPermissionsTestCaseMixin
from etools.applications.tpm.models import TPMVisit
from etools.applications.tpm.tests.base import TPMTestCaseMixin
from etools.applications.tpm.tests.factories import TPMUserFactory, TPMVisitFactory
from etools.applications.users.tests.factories import PMEUserFactory, UserFactory


class TPMTransitionTestCase(TPMTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('update_tpm_permissions', verbosity=0)
        call_command('update_notifications')

    def _do_transition(self, visit, action, user, data=None):
        data = data or {}
        return self.forced_auth_req(
            'post',
            reverse('tpm:visits-transition', args=(visit.id, action)),
            user=user,
            data=data
        )

    def _refresh_tpm_visit_instance(self, visit):
        # Calling refresh_from_db will cause an exception.
        return TPMVisit.objects.get(id=visit.id)


class TestTPMTransitionConditions(TPMTransitionTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.pme_user = PMEUserFactory()
        cls.tpm_user = TPMUserFactory()
        cls.tpm_staff = cls.tpm_user
        cls.tpm_partner = cls.tpm_staff.profile.organization.tpmpartner

    def test_assign_without_activities(self):
        visit = TPMVisitFactory(status='draft',
                                tpm_activities__count=0)

        response = self._do_transition(visit, 'assign', self.pme_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'draft')

    def test_assign_without_focal_points(self):
        visit = TPMVisitFactory(status='draft',
                                tpm_activities__count=3,
                                tpm_activities__unicef_focal_points__count=0)

        response = self._do_transition(visit, 'assign', self.pme_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'draft')

    def test_success_assign(self):
        visit = TPMVisitFactory(status='draft',
                                tpm_activities__count=3,
                                tpm_activities__unicef_focal_points__count=3,
                                tpm_partner_focal_points__count=3)

        response = self._do_transition(visit, 'assign', self.pme_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'assigned')

    def test_cancel_without_msg(self):
        visit = TPMVisitFactory(status='draft')

        response = self._do_transition(visit, 'cancel', self.pme_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cancel_comment', response.data)

    def test_success_cancel(self):
        visit = TPMVisitFactory(status='draft')

        response = self._do_transition(visit, 'cancel', self.pme_user, data={'cancel_comment': 'Just because'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'cancelled')

    def test_tpm_accept_success(self):
        visit = TPMVisitFactory(status='assigned',
                                tpm_partner=self.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_staff])

        response = self._do_transition(visit, 'accept', self.tpm_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'tpm_accepted')

    def test_tpm_report_without_report(self):
        visit = TPMVisitFactory(status='tpm_accepted',
                                tpm_partner=self.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_staff])

        response = self._do_transition(visit, 'send_report', self.tpm_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('report_attachments', response.data.keys())
        self.assertEqual(response.data['report_attachments'], _('You should attach report.'))

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'tpm_accepted')

    def test_tpm_report_success(self):
        visit = TPMVisitFactory(status='tpm_accepted',
                                tpm_activities__report_attachments__count=1,
                                tpm_activities__report_attachments__file_type__name='report',
                                tpm_partner=self.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_staff])

        response = self._do_transition(visit, 'send_report', self.tpm_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'tpm_reported')

    def test_tpm_report_reject(self):
        visit = TPMVisitFactory(status='tpm_reported')
        self.assertFalse(visit.report_reject_comments.exists())

        response = self._do_transition(visit, 'reject_report', self.pme_user, data={
            "reject_comment": 'Just because'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'tpm_report_rejected')
        self.assertEqual(visit.report_reject_comments.count(), 1)

    def test_tpm_report_after_reject(self):
        visit = TPMVisitFactory(status='tpm_report_rejected',
                                tpm_partner=self.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_staff])

        response = self._do_transition(visit, 'send_report', self.tpm_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'tpm_reported')

    def test_approve_report_success(self):
        visit = TPMVisitFactory(status='tpm_reported')

        response = self._do_transition(visit, 'approve', self.pme_user, data={
            'mark_as_programmatic_visit': []
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instance(visit)
        self.assertEqual(visit.status, 'unicef_approved')


class TPMTransitionPermissionsTestCase(TransitionPermissionsTestCaseMixin, TPMTransitionTestCase):
    abstract = True
    model = TPMVisit
    factory = TPMVisitFactory

    ALLOWED_TRANSITION = NotImplemented

    user = NotImplemented
    user_role = NotImplemented

    def create_object(self, transition, **kwargs):
        opts = {}

        if transition == 'assign':
            opts['tpm_partner_focal_points__count'] = 1
            opts['tpm_activities__count'] = 1
            opts['tpm_activities__unicef_focal_points__count'] = 1
            opts['tpm_activities__offices__count'] = 1

        if transition == 'send_report':
            opts['tpm_activities__report_attachments__count'] = 1
            opts['tpm_activities__report_attachments__file_type__name'] = 'report'

        opts.update(kwargs)
        return super().create_object(transition, **opts)

    def do_transition(self, obj, transition):
        extra_data = {}

        if transition in ['reject', 'reject_report']:
            extra_data['reject_comment'] = 'Just because.'

        if transition in ['cancel']:
            extra_data['cancel_comment'] = 'Just because.'

        if transition == 'approve':
            extra_data['mark_as_programmatic_visit'] = []

        return self._do_transition(obj, transition, self.user, extra_data)

    def check_result(self, result, obj, transition):
        allowed = (obj.status, transition) in self.ALLOWED_TRANSITION
        success = result.status_code == status.HTTP_200_OK
        forbidden = result.status_code == status.HTTP_403_FORBIDDEN

        model_name = obj._meta.verbose_name

        if allowed and not success:
            return False, 'Error on {} {} {} by {}.\n{}: {}'.format(transition, obj.status, model_name, self.user_role,
                                                                    result.status_code, result.content)

        if not allowed and success:
            return False, 'Success for not allowed transition. {} can\'t {} {} {}.'.format(self.user_role, transition,
                                                                                           obj.status, model_name)

        if not allowed and not forbidden:
            return False, 'Error on {} {} {} by {}.\n{}: {}'.format(transition, obj.status, model_name, self.user_role,
                                                                    result.status_code, result.content)

        return True, ''


class PMEPermissionsForTPMTransitionTestCase(TPMTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('draft', 'cancel'),
        ('draft', 'assign'),
        ('assigned', 'cancel'),
        ('tpm_accepted', 'cancel'),
        ('tpm_rejected', 'assign'),
        ('tpm_rejected', 'cancel'),
        ('tpm_reported', 'reject_report'),
        ('tpm_reported', 'approve'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = PMEUserFactory()
        cls.user_role = 'PME'


class FPPermissionsForTpmTransitionTestCase(TPMTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('tpm_reported', 'reject_report'),
        ('tpm_reported', 'approve'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory()
        cls.user_role = 'UNICEF Focal Point'

    def create_object(self, transition, **kwargs):
        opts = {
            'tpm_activities__unicef_focal_points': [self.user],
        }

        opts.update(kwargs)
        return super().create_object(transition, **opts)


class TPMPermissionsForTPMTransitionTestCase(TPMTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = TPMUserFactory()
        cls.user_role = 'Simple Third Party Monitor'

        cls.second_user = TPMUserFactory(tpm_partner=cls.user.profile.organization.tpmpartner)

    def create_object(self, transition, **kwargs):
        opts = {
            'tpm_partner': self.user.profile.organization.tpmpartner,
            'tpm_partner_focal_points': [self.second_user],
        }

        opts.update(kwargs)
        return super().create_object(transition, **opts)

    def check_result(self, result, obj, transition):
        draft = obj.status == TPMVisit.STATUSES.draft
        not_found = result.status_code == status.HTTP_404_NOT_FOUND

        if draft and not_found:
            return True, ''

        return super().check_result(result, obj, transition)


class TPMFocalPointPermissionsForTPMTransitionTestCase(TPMTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('assigned', 'accept'),
        ('assigned', 'reject'),
        ('tpm_accepted', 'send_report'),
        ('tpm_report_rejected', 'send_report'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = TPMUserFactory()
        cls.user_role = 'Third Party Focal Point'

    def create_object(self, transition, **kwargs):
        opts = {
            'tpm_partner': self.user.profile.organization.tpmpartner,
            'tpm_partner_focal_points': [self.user],
        }

        opts.update(kwargs)
        return super().create_object(transition, **opts)

    def check_result(self, result, obj, transition):
        draft = obj.status == TPMVisit.STATUSES.draft
        not_found = result.status_code == status.HTTP_404_NOT_FOUND

        if draft and not_found:
            return True, ''

        return super().check_result(result, obj, transition)


class UserPermissionForTPMTransitionTestCase(TPMTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory()
        cls.user_role = 'UNICEF User'
