from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

from django.contrib.contenttypes.models import ContentType
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser

from snapshot.models import Activity
from snapshot.serializers import ActivitySerializer


class ActivityListView(ListAPIView):
    serializer_class = ActivitySerializer
    permission_claasses = (IsAdminUser, )

    def get_queryset(self):
        queryset = Activity.objects.all()

        # filter on user
        user = self.request.query_params.get('user', None)
        if user is not None:
            queryset = queryset.filter(by_user__email=user)

        # filter on target
        target = self.request.query_params.get('target', None)
        if target is not None:
            content_types = ContentType.objects.filter(model=target.lower())
            queryset = queryset.filter(target_content_type__in=content_types)

        # filter on action
        action = self.request.query_params.get('action', None)
        if action is not None:
            queryset = queryset.filter(action=action)

        # filter on date_from (yyyy-mm-dd)
        date_from = self.request.query_params.get('date_from', None)
        if date_from is not None:
            try:
                date_from = datetime.datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                # return a blank queryset
                queryset = queryset.none()
            else:
                queryset = queryset.filter(created__gte=date_from)

        # filter on date_to (yyyy-mm-dd)
        date_to = self.request.query_params.get('date_to', None)
        if date_to is not None:
            try:
                date_to = datetime.datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                # return a blank queryset
                queryset = queryset.none()
            else:
                queryset = queryset.filter(created__lte=date_to)

        return queryset
