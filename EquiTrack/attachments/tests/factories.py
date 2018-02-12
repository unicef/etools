from __future__ import absolute_import, division, print_function, unicode_literals

import factory
from factory import fuzzy
import factory.django

from attachments.models import Attachment, FileType


class FileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileType

    name = factory.Sequence(lambda n: 'file_type_%d' % n)


class AttachmentFactory(factory.django.DjangoModelFactory):
    file_type = factory.SubFactory(FileTypeFactory)
    code = fuzzy.FuzzyText(length=64)

    class Meta:
        model = Attachment
