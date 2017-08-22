from __future__ import unicode_literals

from collections import OrderedDict

from django.contrib.auth import get_user_model
from django_fsm import TransitionNotAllowed

from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from t2f.models import TransitionError


class T2FPagePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('page_count', self.page.paginator.num_pages),
            ('data', data),
            ('total_count', self.page.paginator.object_list.count()),
        ]))


def get_filtered_users(request):
    User = get_user_model()
    return User.objects.exclude(first_name='', last_name='')


def run_transition(serializer):
    transition_name = serializer.transition_name
    if transition_name:
        instance = serializer.instance
        transition = getattr(instance, transition_name)
        try:
            transition()
        except (TransitionNotAllowed, TransitionError) as exception:
            raise ValidationError({'non_field_errors': [str(exception)]})
        instance.save()
