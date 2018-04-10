from rest_framework import exceptions, renderers
from rest_framework.renderers import CoreJSONRenderer
from rest_framework.response import Response
from rest_framework.schemas import SchemaGenerator
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework_swagger.renderers import OpenAPIRenderer, SwaggerUIRenderer


class CustomSchemaGenerator(SchemaGenerator):
    def get_serializer_fields(self, *args):
        try:
            return super(CustomSchemaGenerator, self).get_serializer_fields(*args)
        except exceptions.PermissionDenied:
            return []


def get_schema_view(title=None, url=None, renderer_classes=None):
    """
    Return a schema view.
    """
    generator = CustomSchemaGenerator(title=title, url=url)
    if renderer_classes is None:
        if renderers.BrowsableAPIRenderer in api_settings.DEFAULT_RENDERER_CLASSES:
            rclasses = [renderers.CoreJSONRenderer, renderers.BrowsableAPIRenderer]
        else:
            rclasses = [renderers.CoreJSONRenderer]
    else:
        rclasses = renderer_classes

    class SchemaView(APIView):
        _ignore_model_permissions = True
        exclude_from_schema = True
        renderer_classes = rclasses

        def get(self, request, *args, **kwargs):
            schema = generator.get_schema(request)
            if schema is None:
                raise exceptions.PermissionDenied()
            return Response(schema)

    return SchemaView.as_view()


def get_swagger_view(title=None, url=None):
    """
    Returns schema view which renders Swagger/OpenAPI.
    """
    return get_schema_view(
        title=title,
        url=url,
        renderer_classes=[
            CoreJSONRenderer,
            OpenAPIRenderer,
            SwaggerUIRenderer
        ]
    )
