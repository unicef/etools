from __future__ import absolute_import, division, print_function, unicode_literals

import factory.django
from factory import fuzzy

from attachments.models import Attachment, FileType


class AttachmentFileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileType
        django_get_or_create = ('code', )

    code = fuzzy.FuzzyText()
    name = factory.Sequence(lambda n: 'file_type_%d' % n)


class AttachmentFactory(factory.django.DjangoModelFactory):
    file_type = factory.SubFactory(AttachmentFileTypeFactory)
    code = fuzzy.FuzzyText(length=64)

    class Meta:
        model = Attachment
