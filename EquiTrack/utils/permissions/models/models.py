from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from model_utils import Choices

from utils.permissions.models.query import BasePermissionQueryset, StatusBasePermissionQueryset


@python_2_unicode_compatible
class BasePermission(models.Model):
    """
    Base model for store field level permissions.

    Target store in `model_name.field_name` format. Also it support pattern like `model_name.*`.
    """
    # User type's ordering is weighted. It determine user type's priority (See `_get_user_type` method).
    USER_TYPES = None

    PERMISSIONS = Choices(
        ('view', 'View'),
        ('edit', 'Edit'),
        ('action', 'Action'),
    )

    TYPES = Choices(
        ('allow', 'Allow'),
        ('disallow', 'Disallow'),
    )

    user_type = models.CharField(max_length=30)
    permission = models.CharField(max_length=10, choices=PERMISSIONS)
    permission_type = models.CharField(max_length=10, choices=TYPES, default=TYPES.allow)
    target = models.CharField(max_length=100)

    objects = BasePermissionQueryset.as_manager()

    class Meta:
        abstract = True
        unique_together = ('user_type', 'target', 'permission_type')

    def __str__(self):
        return '{} {} to {} {}'.format(self.user_type, self.permission_type, self.permission, self.target)

    @classmethod
    def _get_user_type(cls, user):
        """
        Return user type based on user's groups.
        :param user:
        :return:
        """
        ordered_user_types = zip(*cls.USER_TYPES)[1]

        when_mapping = [
            models.When(name=name, then=models.Value(i))
            for i, name in enumerate(reversed(ordered_user_types))
        ]
        group = user.groups.annotate(
            order=models.Case(*when_mapping, default=models.Value(-1), output_field=models.IntegerField())
        ).order_by('-order').first()

        if not group:
            return None

        for choice in cls.USER_TYPES:
            if group.name == choice[1]:
                return choice[0]


@python_2_unicode_compatible
class StatusBasePermission(BasePermission):
    STATUSES = Choices(
        ('new', 'New instance'),
    )

    instance_status = models.CharField(max_length=32)

    objects = StatusBasePermissionQueryset.as_manager()

    def __str__(self):
        return '{} can {} {} in {} instance'.format(self.user_type, self.permission, self.target, self.instance_status)

    class Meta:
        abstract = True
        unique_together = ('user_type', 'instance_status', 'target', 'permission_type')
