from __future__ import unicode_literals

from collections import defaultdict

from rest_framework import serializers

from et2f import UserTypes, TripStatus


class PermissionMatrixSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """
        So here comes some hack. This serializer should be called with many=False always since we want to do some
        data manipulation before we render it as json. With many=True it would not be possible
        :param instance: list of TravelPermission objects
        :type instance: list
        :return: permission matrix dict
        :rtype: dict
        """
        matrix = defaultdict(dict)
        for user_type in UserTypes.CHOICES:
            for status in TripStatus.CHOICES:
                matrix[user_type[0]][status[0]] = defaultdict(dict)

        for permission in instance:
            if permission.model == 'travel':
                model_dict = matrix[permission.user_type][permission.status][permission.field]
                model_dict[permission.permission_type] = True
            else:
                model_dict = matrix[permission.user_type][permission.status][permission.model]
                field_dict = model_dict.setdefault(permission.field, {})
                field_dict[permission.permission_type] = True

        return matrix