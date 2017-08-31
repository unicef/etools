from django.core.management import call_command
from django.utils import six

from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from tpm.tests.base import TPMTestCaseMixin

from ..models import TPMVisit

from .factories import TPMVisitFactory, UserFactory


class TPMTransitionTestCase(TPMTestCaseMixin, APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_tpm_permissions', verbosity=0)

    def _do_transition(self, visit, action, user, data=None):
        data = data or {}
        return self.forced_auth_req(
            'post',
            '/api/tpm/visits/{0}/{1}/'.format(visit.id, action),
            user=user,
            data=data
        )

    def _refresh_tpm_visit_instace(self, visit):
        # Calling refresh_from_db will cause an exception.
        return TPMVisit.objects.get(id=visit.id)


class TestTPMTransitionConditions(TPMTransitionTestCase):
    @classmethod
    def setUpTestData(cls):
        super(TestTPMTransitionConditions, cls).setUpTestData()

        cls.pme_user = UserFactory(pme=True)
        cls.tpm_user = UserFactory(tpm=True)
        cls.tpm_staff = cls.tpm_user.tpm_tpmpartnerstaffmember
        cls.tpm_partner = cls.tpm_staff.tpm_partner

    def test_assign_without_activities(self):
        visit = TPMVisitFactory(status='draft',
                                tpm_activities__count=0,
                                unicef_focal_points__count=3)

        response = self._do_transition(visit, 'assign', self.pme_user)
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'draft')

    def test_assign_without_focal_points(self):
        visit = TPMVisitFactory(status='draft',
                                tpm_activities__count=3,
                                unicef_focal_points__count=0)

        response = self._do_transition(visit, 'assign', self.pme_user)
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'draft')

    def test_success_assign(self):
        visit = TPMVisitFactory(status='draft',
                                tpm_activities__count=3,
                                unicef_focal_points__count=3)

        response = self._do_transition(visit, 'assign', self.pme_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'assigned')

    def test_success_cancel(self):
        visit = TPMVisitFactory(status='draft')

        response = self._do_transition(visit, 'cancel', self.pme_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'cancelled')

    def test_tpm_accept_success(self):
        visit = TPMVisitFactory(status='assigned',
                                tpm_partner=self.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_staff])

        response = self._do_transition(visit, 'accept', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'tpm_accepted')

    def test_tpm_report_without_report(self):
        visit = TPMVisitFactory(status='tpm_accepted',
                                tpm_partner=self.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_staff])

        response = self._do_transition(visit, 'send_report', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'tpm_accepted')

    def test_tpm_report_success(self):
        visit = TPMVisitFactory(status='tpm_accepted',
                                report__count=1,
                                tpm_partner=self.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_staff])

        response = self._do_transition(visit, 'send_report', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'tpm_reported')

    def test_tpm_report_reject(self):
        visit = TPMVisitFactory(status='tpm_reported')
        self.assertEquals(visit.report_reject_comments.count(), 0)

        response = self._do_transition(visit, 'reject_report', self.pme_user, data={
            "reject_comment": 'Just because'
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'tpm_report_rejected')
        self.assertEquals(visit.report_reject_comments.count(), 1)

    def test_tpm_report_after_reject(self):
        visit = TPMVisitFactory(status='tpm_report_rejected',
                                tpm_partner=self.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_staff])

        response = self._do_transition(visit, 'send_report', self.tpm_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'tpm_reported')

    def test_approve_report_success(self):
        visit = TPMVisitFactory(status='tpm_reported')

        response = self._do_transition(visit, 'approve', self.pme_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        visit = self._refresh_tpm_visit_instace(visit)
        self.assertEquals(visit.status, 'unicef_approved')


class TransitionPermissionTestCaseMetaclass(type):
    @staticmethod
    def _collect_transitions(model):
        transitions = []
        for attr_name in dir(model):
            attr = getattr(model, attr_name, None)

            if hasattr(attr, '_django_fsm'):
                transitions.append(attr_name)

        return transitions

    @staticmethod
    def _annotate_test(klass, obj_status, transition):
        def test(self):
            obj = self.create_object(transition, **{
                self.status_field.name: obj_status,
            })

            result = self.do_transition(obj, transition)

            success, message = self.check_result(result, obj, transition)

            self.assertTrue(success, message)

        model = klass.model
        model_name = model._meta.model_name
        test_name = 'test_{}_for_{}_{}'.format(transition, obj_status, model_name)
        setattr(klass, test_name, test)

    def __new__(cls, name, bases, attrs):
        abstract = attrs.get('abstract', False)

        newclass = super(TransitionPermissionTestCaseMetaclass, cls).__new__(cls, name, bases, attrs)

        if abstract:
            return newclass

        newclass.transitions = cls._collect_transitions(newclass.model)
        newclass.status_field = getattr(newclass.model, newclass.transitions[0])._django_fsm.field
        newclass.statuses = zip(*newclass.status_field.choices)[0]

        for obj_status in newclass.statuses:
            for transition in newclass.transitions:
                cls._annotate_test(newclass, obj_status, transition)

        return newclass


@six.add_metaclass(TransitionPermissionTestCaseMetaclass)
class TransitionPermissionsTestCaseMixin(object):
    abstract = True
    model = NotImplemented
    factory = NotImplemented

    def create_object(self, transition, **kwargs):
        return self.factory(**kwargs)

    def do_transition(self, obj, transition):
        raise NotImplementedError

    def check_result(self, result, obj, transition):
        raise NotImplementedError

    def get_extra_obj_attrs(self, **kwargs):
        attrs = {}
        attrs.update(kwargs)
        return attrs


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
            opts['sections__count'] = 3
            opts['unicef_focal_points__count'] = 1
            opts['offices__count'] = 1
            opts['tpm_partner_focal_points__count'] = 1
            opts['tpm_activities__count'] = 1

        if transition == 'send_report':
            opts['report__count'] = 1

        opts.update(kwargs)
        return super(TPMTransitionPermissionsTestCase, self).create_object(transition, **opts)

    def do_transition(self, obj, transition):
        extra_data = {}

        if transition in ['reject', 'reject_report']:
            extra_data['reject_comment'] = 'Just because.'

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
        ('tpm_reported', 'cancel'),
        ('tpm_reported', 'reject_report'),
        ('tpm_reported', 'approve'),
        ('tpm_report_rejected', 'cancel'),
    ]

    @classmethod
    def setUpTestData(cls):
        super(PMEPermissionsForTPMTransitionTestCase, cls).setUpTestData()

        cls.user = UserFactory(pme=True)
        cls.user_role = 'PME'


class FPPermissionsForTpmTransitionTestCase(PMEPermissionsForTPMTransitionTestCase):
    @classmethod
    def setUpTestData(cls):
        super(FPPermissionsForTpmTransitionTestCase, cls).setUpTestData()

        cls.user = UserFactory(unicef_user=True)
        cls.user_role = 'UNICEF Focal Point'

        cls.ALLOWED_TRANSITION = cls.ALLOWED_TRANSITION[:]
        cls.ALLOWED_TRANSITION.remove(('draft', 'cancel'))
        cls.ALLOWED_TRANSITION.remove(('draft', 'assign'))

    def create_object(self, transition, **kwargs):
        opts = {
            'unicef_focal_points': [self.user],
        }

        opts.update(kwargs)
        return super(FPPermissionsForTpmTransitionTestCase, self).create_object(transition, **opts)


class TPMPermissionsForTPMTransitionTestCase(TPMTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('assigned', 'accept'),
        ('assigned', 'reject'),
        ('tpm_accepted', 'send_report'),
        ('tpm_report_rejected', 'send_report'),
    ]

    @classmethod
    def setUpTestData(cls):
        super(TPMPermissionsForTPMTransitionTestCase, cls).setUpTestData()

        cls.user = UserFactory(tpm=True)
        cls.user_role = 'Third Party Monitor'

    def create_object(self, transition, **kwargs):
        opts = {
            'tpm_partner': self.user.tpm_tpmpartnerstaffmember.tpm_partner,
            'tpm_partner_focal_points': [self.user.tpm_tpmpartnerstaffmember],
        }

        opts.update(kwargs)
        return super(TPMPermissionsForTPMTransitionTestCase, self).create_object(transition, **opts)

    def check_result(self, result, obj, transition):
        draft = obj.status == TPMVisit.STATUSES.draft
        not_found = result.status_code == status.HTTP_404_NOT_FOUND

        if draft and not_found:
            return True, ''

        return super(TPMPermissionsForTPMTransitionTestCase, self).check_result(result, obj, transition)


class UserPermissionForTPMTransitionTestCase(TPMTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = []

    @classmethod
    def setUpTestData(cls):
        super(UserPermissionForTPMTransitionTestCase, cls).setUpTestData()

        cls.user = UserFactory(unicef_user=True)
        cls.user_role = 'UNICEF User'
