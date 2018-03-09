from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import factory

from partners.models import WorkspaceFileType


class WorkspaceFileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkspaceFileType

    name = factory.Sequence(lambda n: 'workspace file type {}'.format(n))
