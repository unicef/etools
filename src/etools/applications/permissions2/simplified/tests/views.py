from rest_framework.viewsets import ModelViewSet

from etools.applications.permissions2.simplified.metadata import SimplePermissionBasedMetadata
from etools.applications.permissions2.simplified.tests.models import Parent, Child
from etools.applications.permissions2.simplified.tests.permissions import UserIsBobPermission
from etools.applications.permissions2.simplified.tests.serializers import ParentSerializer, ChildSerializer
from etools.applications.permissions2.simplified.views import SimplePermittedViewSetMixin


class NotConfiguredParentViewSet(SimplePermittedViewSetMixin, ModelViewSet):
    queryset = Parent.objects.all()
    serializer_class = ParentSerializer


class ParentViewSet(SimplePermittedViewSetMixin, ModelViewSet):
    metadata_class = SimplePermissionBasedMetadata
    queryset = Parent.objects.all()
    serializer_class = ParentSerializer
    write_permission_classes = [UserIsBobPermission]


class ChildViewSet(SimplePermittedViewSetMixin, ModelViewSet):
    metadata_class = SimplePermissionBasedMetadata
    queryset = Child.objects.all()
    serializer_class = ChildSerializer
