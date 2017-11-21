from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import factory

from EquiTrack.factories import (
    GovernmentInterventionFactory,
    ResultFactory,
    )
from partners.models import (
    GovernmentInterventionResult,
    WorkspaceFileType,
    )


class GovernmentInterventionResultFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = GovernmentInterventionResult

    intervention = factory.SubFactory(GovernmentInterventionFactory)
    result = factory.SubFactory(ResultFactory)
    year = '2017'


class WorkspaceFileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkspaceFileType

    name = factory.Sequence(lambda n: 'workspace file type {}'.format(n))
