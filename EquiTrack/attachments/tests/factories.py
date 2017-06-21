import factory
import factory.django

from attachments.models import FileType, Attachment


class FileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileType

    name = factory.Sequence(lambda n: 'file_type_%d' % n)


class AttachmentFactory(factory.django.DjangoModelFactory):
    file_type = factory.SubFactory(FileTypeFactory)

    class Meta:
        model = Attachment
