from django.db import models


class BasePermissionQueryset(models.QuerySet):
    def filter(self, *args, **kwargs):
        if 'user' in kwargs:
            kwargs['user_type'] = self.model._get_user_type(kwargs.pop('user'))
            return self.filter(*args, **kwargs)

        return super(BasePermissionQueryset, self).filter(*args, **kwargs)


class StatusBasePermissionQueryset(BasePermissionQueryset):
    def filter(self, *args, **kwargs):
        if 'instance__in' in kwargs:
            instances = kwargs.pop('instance__in')
            statuses = {instance.status for instance in instances}
            kwargs['instance_status__in'] = statuses
            return self.filter(*args, **kwargs)

        if 'instance' in kwargs:
            instance = kwargs.pop('instance')
            if instance:
                kwargs['instance_status'] = instance.status
            else:
                kwargs['instance_status'] = self.model.STATUSES.new
            return self.filter(*args, **kwargs)

        return super(StatusBasePermissionQueryset, self).filter(*args, **kwargs)
