from rest_framework import exceptions
from rest_framework.schemas import AutoSchema


class EToolsSchema(AutoSchema):
    """
    Custom view inspector, allowed api exceptions inside get_serializer method for correct permissions work.
    """

    def get_serializer_fields(self, path, method):
        view = self.view

        if method not in ('PUT', 'PATCH', 'POST'):
            return []

        if not hasattr(view, 'get_serializer'):
            return []

        try:
            view.get_serializer()
        except exceptions.APIException:
            return []

        return super().get_serializer_fields(path, method)
