from django.urls import reverse
from django.utils import timezone

import factory.fuzzy
from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.tests.factories import (
    CPOutputConfigFactory,
    FMMethodFactory,
    FMMethodTypeFactory,
    LocationSiteFactory,
    PlannedCheckListItemFactory,
)
from etools.applications.field_monitoring.planning.tests.factories import TaskFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.field_monitoring.visits.models import Visit
from etools.applications.field_monitoring.visits.tests.factories import (
    VisitFactory,
    VisitMethodTypeFactory,
    VisitTaskLinkFactory,
)
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.permissions2.tests.mixins import TransitionPermissionsTestCaseMixin


class VisitsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        for status_code, status_display in Visit.STATUS_CHOICES:
            VisitFactory(status=status_code)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), len(Visit.STATUS_CHOICES))

    def test_detail(self):
        visit = VisitFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-detail', args=[visit.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_totals(self):
        config = CPOutputConfigFactory()
        location_site = LocationSiteFactory()

        self.assertEqual(Visit.objects.count(), 0)

        first_task = TaskFactory(location_site=location_site)
        second_task = TaskFactory(location_site=location_site, cp_output_config=config)
        third_task = TaskFactory(cp_output_config=config)

        unused_task = TaskFactory(year_plan__year=timezone.now().year - 1)  # shouldn't appear as it's for prev year
        unused_visit = VisitFactory(status=Visit.STATUS_CHOICES.completed, tasks__count=0)
        VisitTaskLinkFactory(visit=unused_visit, task=unused_task)

        VisitFactory(status=Visit.STATUS_CHOICES.draft, tasks__count=0)
        VisitFactory(status=Visit.STATUS_CHOICES.cancelled, tasks__count=0)
        VisitFactory(status=Visit.STATUS_CHOICES.assigned, tasks__count=0)
        VisitFactory(status=Visit.STATUS_CHOICES.assigned, tasks=[first_task, second_task])
        VisitFactory(status=Visit.STATUS_CHOICES.completed, tasks=[second_task, third_task])

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-totals'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(
            response.data,
            {
                'visits': 2,
                'outputs': 2,
                'sites': 2,
            }
        )

    def test_team_members_filter(self):
        VisitFactory()
        visit = VisitFactory(team_members__count=3)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-list'),
            user=self.unicef_user,
            data={
                'team_members__in': ','.join(str(u.id) for u in visit.team_members.all()[:2])
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], visit.id)

    def test_tasks_count_ordering(self):
        visits = reversed([VisitFactory(tasks__count=i) for i in range(3)])

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-list'),
            user=self.unicef_user,
            data={
                'ordering': '-tasks__count'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            [v['id'] for v in response.data['results']],
            [v.id for v in visits]
        )

    def test_create(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_visits:visits-list'),
            user=self.fm_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_tasks(self):
        visit = VisitFactory(tasks__count=2)
        tasks = [visit.tasks.first().id, TaskFactory().id]

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_visits:visits-detail', args=[visit.id]),
            user=self.fm_user,
            data={
                'tasks': tasks
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(sorted(map(lambda t: t['id'], response.data['tasks'])), sorted(tasks))

    def test_scope_by_methods(self):
        visit = VisitFactory(status=Visit.STATUS_CHOICES.draft, tasks__count=1)

        method_type = FMMethodTypeFactory()
        task = visit.tasks.first()
        self.assertIsNotNone(task)

        task.cp_output_config.recommended_method_types.add(method_type)
        PlannedCheckListItemFactory(
            cp_output_config=task.cp_output_config,
            methods=[method_type.method, FMMethodFactory(is_types_applicable=False)]
        )

        visit.assign()
        visit.save()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-detail', args=[visit.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        scope_by_methods = response.data['scope_by_methods']
        self.assertNotEqual(scope_by_methods, [])
        self.assertNotEqual(scope_by_methods[0]['cp_output_configs'], [])
        self.assertEqual(scope_by_methods[1]['cp_output_configs'], [])


class VisitMethodTypesVIewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_create(self):
        visit = VisitFactory(status=Visit.STATUS_CHOICES.draft)

        response = self.forced_auth_req(
            'post', reverse('field_monitoring_visits:visit-method-types-list', args=[visit.id]),
            user=self.fm_user,
            data={
                'method': FMMethodFactory(is_types_applicable=True).id,
                'name': factory.fuzzy.FuzzyText().fuzz(),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(visit.method_types.count(), 1)
        self.assertFalse(visit.method_types.first().is_recommended)

    def test_update_recommended(self):
        method_type = VisitMethodTypeFactory(is_recommended=True)

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_visits:visit-method-types-detail',
                             args=[method_type.visit.id, method_type.id]),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        method_type = VisitMethodTypeFactory(is_recommended=False)

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_visits:visit-method-types-detail',
                             args=[method_type.visit.id, method_type.id]),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class VisitPartnersViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        PartnerFactory()
        visit = VisitFactory(tasks__count=1)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-partners-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], visit.tasks.first().partner.id)


class VisitCPOutputConfigsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        CPOutputConfigFactory()
        visit = VisitFactory(tasks__count=1)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-cp-output-configs-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], visit.tasks.first().cp_output_config.id)


class VisitLocationsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        LocationFactory()
        visit = VisitFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-locations-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(int(response.data['results'][0]['id']), visit.location.id)


class VisitLocationSitesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        LocationSiteFactory()
        visit = VisitFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-location-sites-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(int(response.data['results'][0]['id']), visit.location_site.id)


class VisitTeamMembersViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        UserFactory()
        visit = VisitFactory(team_members__count=1)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_visits:visits-team-members-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], visit.team_members.first().id)


class VisitTransitionPermissionsTestCase(TransitionPermissionsTestCaseMixin, FMBaseTestCaseMixin, BaseTenantTestCase):
    abstract = True
    model = Visit
    factory = VisitFactory

    ALLOWED_TRANSITION = NotImplemented

    user = NotImplemented
    user_role = NotImplemented

    def do_transition(self, obj, transition):
        extra_data = {}

        if transition == 'reject':
            extra_data['reject_comment'] = 'Just because.'

        if transition == 'cancel':
            extra_data['cancel_comment'] = 'Just because.'

        if transition == 'reject_report':
            extra_data['report_reject_comment'] = 'Just because.'

        return self.forced_auth_req(
            'post',
            reverse('field_monitoring_visits:visits-transition', args=(obj.id, transition)),
            user=self.user,
            data=extra_data,
        )


class PMEPermissionsForVisitTransitionTestCase(VisitTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('draft', 'cancel'),
        ('draft', 'assign'),
        ('assigned', 'cancel'),
        ('rejected', 'cancel'),
        ('rejected', 'assign'),
        ('accepted', 'cancel'),
        ('reported', 'reject_report'),
        ('reported', 'complete'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(pme=True)
        cls.user_role = 'PME'


class FMPermissionsForVisitTransitionTestCase(VisitTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('draft', 'cancel'),
        ('draft', 'assign'),
        ('assigned', 'cancel'),
        ('rejected', 'cancel'),
        ('rejected', 'assign'),
        ('accepted', 'cancel'),
        ('reported', 'reject_report'),
        ('reported', 'complete'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(fm_user=True)
        cls.user_role = 'FM User'


class PrimaryFieldMonitorPermissionsForVisitTransitionTestCase(VisitTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('assigned', 'accept'),
        ('assigned', 'reject'),
        ('accepted', 'mark_ready'),
        ('ready', 'send_report'),
        ('report_rejected', 'send_report'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(unicef_user=True)
        cls.user_role = 'Primary Field Monitor'

    def create_object(self, transition, **kwargs):
        opts = {
            'primary_field_monitor': self.user
        }

        opts.update(kwargs)
        return super().create_object(transition, **opts)


class DataCollectorPermissionsForVisitTransitionTestCase(VisitTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(unicef_user=True)
        cls.user_role = 'Data Collector'

    def create_object(self, transition, **kwargs):
        opts = {
            'team_members': [self.user]
        }

        opts.update(kwargs)
        return super().create_object(transition, **opts)


class VisitTransitionsMetaTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_pme_assign_draft(self):
        user = UserFactory(pme=True)
        visit = VisitFactory(status='draft')

        response = self.forced_auth_req(
            'options',
            reverse('field_monitoring_visits:visits-detail', args=[visit.pk]),
            user=user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            ['assign', 'cancel'],
            [t['code'] for t in response.data['actions']['allowed_FSM_transitions']]
        )
