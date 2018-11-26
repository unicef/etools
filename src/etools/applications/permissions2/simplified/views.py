class SimplePermittedViewSetMixin(object):
    write_permission_classes = []

    def get_write_permissions(self):
        return [permission() for permission in self.write_permission_classes]

    def check_write_permissions(self, instance=None, raise_error=True):
        write_permissions = self.get_write_permissions()

        if not write_permissions:
            self.permission_denied(self.request)

        if instance:
            read_only = not all(permission.has_object_permission(self.request, self, instance)
                                for permission in write_permissions)

        else:
            read_only = not all(permission.has_permission(self.request, self)
                                for permission in write_permissions)

        if read_only and raise_error:
            self.permission_denied(self.request)

        return not read_only

    def get_serializer(self, instance=None, *args, **kwargs):
        many = kwargs.get('many')

        kwargs['read_only'] = not self.check_write_permissions(not many and instance, raise_error=False)
        serializer = super().get_serializer(instance=instance, *args, **kwargs)

        return serializer

    def perform_destroy(self, instance):
        self.check_write_permissions(instance=instance)

        super().perform_destroy(instance)
