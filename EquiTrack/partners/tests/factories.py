from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import factory

from EquiTrack.factories import (
    GovernmentInterventionFactory,
    InterventionFactory,
    PartnerFactory,
    ResultFactory,
    )
from partners.models import (
    Assessment,
    FileType,
    GovernmentInterventionResult,
    InterventionAmendment,
    InterventionAttachment,
    InterventionResultLink,
    WorkspaceFileType,
    )


class AssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment

    type = Assessment.ASSESMENT_TYPES[0]
    partner = factory.SubFactory(PartnerFactory)


class FileTypeFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = FileType

    name = FileType.PROGRESS_REPORT


class GovernmentInterventionResultFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = GovernmentInterventionResult

    intervention = factory.SubFactory(GovernmentInterventionFactory)
    result = factory.SubFactory(ResultFactory)
    year = '2017'


class InterventionAmendmentFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = InterventionAmendment

    intervention = factory.SubFactory(InterventionFactory)


class InterventionAttachmentFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = InterventionAttachment

    intervention = factory.SubFactory(InterventionFactory)
    type = factory.SubFactory(FileTypeFactory)


class InterventionResultLinkFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = InterventionResultLink

    intervention = factory.SubFactory(InterventionFactory)
    cp_output = factory.SubFactory(ResultFactory)


class WorkspaceFileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkspaceFileType

    name = factory.Sequence(lambda n: 'workspace file type {}'.format(n))
