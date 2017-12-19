"""
Model factories used for generating models dynamically for tests
"""
from django.contrib.auth.models import Group

import factory


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "Partnership Manager"


class UnicefUserGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "UNICEF User"
