from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase

from utils.common.tests.models import CodedGenericChild, Parent


class CodedGenericTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # We disable synchronisation of test models. So we need to create it manually.
        with connection.schema_editor() as editor:
            editor.create_model(Parent)
            editor.create_model(CodedGenericChild)

        cls.parent = Parent.objects.create(field=0)
        cls.parent_content_type = ContentType.objects.get_for_model(Parent)

        cls.children1 = [
            CodedGenericChild.objects.create(code='children1', id=1, field=1, content_type=cls.parent_content_type,
                                             object_id=cls.parent.id),
            CodedGenericChild.objects.create(code='children1', id=2, field=2, content_type=cls.parent_content_type,
                                             object_id=cls.parent.id),
        ]

        cls.children2 = [
            CodedGenericChild.objects.create(code='children2', id=3, field=3, content_type=cls.parent_content_type,
                                             object_id=cls.parent.id),
            CodedGenericChild.objects.create(code='children2', id=4, field=4, content_type=cls.parent_content_type,
                                             object_id=cls.parent.id),
        ]

    def test_separation(self):
        self.assertSequenceEqual(self.parent.children1.all().values_list('id', flat=True), [1, 2])
        self.assertSequenceEqual(self.parent.children2.all().values_list('id', flat=True), [3, 4])
