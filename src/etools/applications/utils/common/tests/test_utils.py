
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from etools.applications.utils.common.utils import get_all_field_names


class CommonUtilsTest(TestCase):
    '''Tests for utils.common.utils'''

    def test_get_all_field_names(self):
        '''Exercise get_all_field_names() which is Django-provided code to replace Model._meta.get_all_field_names()'''
        class Useless:
            pass

        class Dummy(models.Model):
            '''Model to contain the many different types of fields I want to test.

            The list of fields in the model is not exhaustive, but it covers a variety of Django field types.
            '''
            # CHOICES should not be in the list of field names
            CHOICES = (('to be'), ('not to be'))

            # fields 1 - 9 inclusive should be in the list of field names
            field01 = models.CharField(max_length=50)
            field02 = models.IntegerField(primary_key=True)
            field03 = models.IntegerField(db_index=True)
            field04 = models.IntegerField(editable=False)
            field05 = models.IntegerField()
            field06 = models.DateField()
            field07 = models.TextField(blank=True)
            field08 = models.IntegerField(unique=True)
            field09 = models.IntegerField(default=42)
            # fields 10 and 11 should be in the list of field names, along with the automatically-created fields
            # 'field10_id' and 'field11_id'
            field10 = models.ForeignKey(Group)
            field11 = models.OneToOneField(Group)
            # field 12 should be in the list of field names, but it doesn't get a 'field12_id' because it's M2M
            field12 = models.ManyToManyField(Group)
            # field 13 shouldn't be in the list of field names. Generic FKs are excluded according to the Django doc.
            # https://docs.djangoproject.com/en/1.10/ref/models/meta/#migrating-from-the-old-api
            field13 = GenericForeignKey()
            # fields 14 and 15 shouldn't be in the list of field names because they're not Django fields.
            field14 = {}
            field15 = Useless()

            class Meta:
                verbose_name_plural = _('Dummies')
                app_label = 'tests'

        expected_field_names = ['field{:02}'.format(i + 1) for i in range(12)]
        expected_field_names += ['field10_id', 'field11_id']
        expected_field_names.sort()

        actual_field_names = sorted(get_all_field_names(Dummy))

        self.assertEqual(expected_field_names, actual_field_names)

        # Bonus -- if we're still under Django < 1.10 where Model._meta.get_all_field_names() still exists,
        # ensure our function produces the same results as that one.
        if hasattr(Dummy._meta, 'get_all_field_names'):
            actual_field_names = sorted(Dummy._meta.get_all_field_names())
            self.assertEqual(expected_field_names, actual_field_names)
