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
        # To have better naming
        permissions_qs = instance

        model_names = {p.model for p in permissions_qs}
        # Travel is the main, it's special
        model_names.remove('travel')

        models_dict = {mn: defaultdict(dict) for mn in model_names}

        matrix = defaultdict(dict)
        for user_type in UserTypes.CHOICES:
            for status in TripStatus.CHOICES:
                matrix[user_type[0]][status[0]] = models_dict.copy()

        for permission in instance:
            if permission.model == 'travel':
                field_name = permission.field.replace('_', '')

                # Related field, nothing to do
                if field_name in model_names:
                    continue

                model_dict = matrix[permission.user_type][permission.status].setdefault(permission.field, {})
                model_dict[permission.permission_type] = True
            else:
                model_dict = matrix[permission.user_type][permission.status][permission.model]
                model_dict[permission.field][permission.permission_type] = True

        return matrix