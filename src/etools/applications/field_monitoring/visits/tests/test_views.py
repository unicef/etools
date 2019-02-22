from django.urls import reverse
from django.utils import timezone

from rest_framework import status

import factory.fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.action_points.tests.factories import UserFactory
from etools.applications.field_monitoring.fm_settings.tests.factories import FMMethodFactory, FMMethodTypeFactory, \
    PlannedCheckListItemFactory, LocationSiteFactory, CPOutputConfigFactory
from etools.applications.field_monitoring.planning.tests.factories import TaskFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.visits.models import Visit
from etools.applications.field_monitoring.visits.tests.factories import VisitFactory, VisitMethodTypeFactory, \
    VisitTaskLinkFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.tpm.tests.factories import UserFactory as TPMUserFactory, SimpleTPMPartnerFactory


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
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_tasks(self):
        visit = VisitFactory(tasks__count=2)
        tasks = [visit.tasks.first().id, TaskFactory().id]

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_visits:visits-detail', args=[visit.id]),
            user=self.unicef_user,
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
            user=self.unicef_user,
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


class FMUsersViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_user = UserFactory(unicef_user=True, is_staff=True)
        cls.usual_user = UserFactory(is_staff=False)
        cls.tpm_user = TPMUserFactory(tpm=True, tpm_partner=SimpleTPMPartnerFactory())
        cls.another_tpm_user = TPMUserFactory(tpm=True, tpm_partner=SimpleTPMPartnerFactory())

    def _test_filter(self, filter_data, expected_users):
        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_visits:users-list'),
            data=filter_data,
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(expected_users), len(response.data['results']))
        self.assertListEqual(
            sorted([u.id for u in expected_users]),
            sorted([u['id'] for u in response.data['results']])
        )

        return response

    def test_filter_unicef(self):
        response = self._test_filter({'user_type': 'unicef'}, [self.unicef_user])
        self.assertEqual(response.data['results'][0]['user_type'], 'unicef')

    def test_filter_default(self):
        response = self._test_filter({}, [self.unicef_user])
        self.assertEqual(response.data['results'][0]['user_type'], 'unicef')

    def test_filter_tpm(self):
        response = self._test_filter({'user_type': 'tpm'}, [self.tpm_user, self.another_tpm_user])
        self.assertEqual(response.data['results'][0]['user_type'], 'tpm')
        self.assertEqual(response.data['results'][1]['user_type'], 'tpm')

    def test_filter_tpm_partner(self):
        tpm_partner = self.tpm_user.tpmpartners_tpmpartnerstaffmember.tpm_partner.id

        response = self._test_filter(
            {'user_type': 'tpm', 'tpm_partner': tpm_partner},
            [self.tpm_user]
        )
        self.assertEqual(response.data['results'][0]['user_type'], 'tpm')
        self.assertEqual(response.data['results'][0]['tpm_partner'], tpm_partner)
