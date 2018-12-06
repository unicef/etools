from django.urls import reverse
from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.tests.factories import StartedMethodFactory
from etools.applications.field_monitoring.fm_settings.tests.factories import PlannedCheckListItemFactory, \
    FMMethodFactory, FMMethodTypeFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.visits.models import Visit
from etools.applications.field_monitoring.visits.tests.factories import UNICEFVisitFactory


class VisitDataCollectionViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_details(self):
        visit = UNICEFVisitFactory(status=Visit.STATUS_CHOICES.assigned)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_data_collection:visits-detail', args=[visit.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AssignedVisitMixin(object):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.assigned_visit = UNICEFVisitFactory(status=Visit.STATUS_CHOICES.draft, tasks__count=1)

        cls.assigned_method_type = FMMethodTypeFactory()
        task = cls.assigned_visit.tasks.first()

        task.cp_output_config.recommended_method_types.add(cls.assigned_method_type)
        PlannedCheckListItemFactory(
            cp_output_config=task.cp_output_config,
            methods=[cls.assigned_method_type.method, FMMethodFactory(is_types_applicable=False)]
        )

        cls.assigned_visit.assign()
        cls.assigned_visit.save()

        cls.assigned_visit_method_type = task.visit_task_links.first().cp_output_configs.first()\
            .recommended_method_types.first()


class StartedMethodsViewTestCase(FMBaseTestCaseMixin, AssignedVisitMixin, BaseTenantTestCase):
    def test_list(self):
        StartedMethodFactory(
            visit=self.assigned_visit,
            method=self.assigned_visit_method_type.method,
            method_type=self.assigned_visit_method_type,
        )

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_data_collection:started-methods-list', args=[self.assigned_visit.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def start_new_method(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_data_collection:started-methods-list', args=[self.assigned_visit.id]),
            user=self.unicef_user,
            data={
                'method': self.assigned_visit_method_type.method.id,
                'method_type': self.assigned_visit_method_type.id,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author']['id'], self.unicef_user.id)
