from __future__ import unicode_literals

from collections import defaultdict

from rest_framework import serializers

from t2f.models import UserTypes, Travel


class PermissionMatrixSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """
        So here comes some hack. This serializer should be called with many=False always since we want to do some
        data manipulation before we render it as json. With many=True it would not be possible
        :param instance: queryset of TravelPermission objects
        :type instance: QuerySet
        :return: permission matrix dict
        :rtype: dict
        """
        # To have better naming
        permissions_qs = instance

        matrix = defaultdict(dict)
        for user_type in UserTypes.CHOICES:
            for status in Travel.CHOICES:
                matrix[user_type[0]][status[0]] = defaultdict(dict)

        for permission in permissions_qs:
            if permission.model == 'travel':
                matrix[permission.user_type][permission.status][permission.field][permission.permission_type] = permission.value
            else:
                model_dict = matrix[permission.user_type][permission.status][permission.model]
                model_dict.setdefault(permission.field, {})[permission.permission_type] = permission.value
        return matrix
