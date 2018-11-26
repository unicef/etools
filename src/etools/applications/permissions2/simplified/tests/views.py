from rest_framework.viewsets import ModelViewSet

from etools.applications.permissions2.simplified.metadata import SimplePermissionBasedMetadata
from etools.applications.permissions2.simplified.permissions import PermissionQ
from etools.applications.permissions2.simplified.tests.models import Parent, Child, ModelWithFSMField
from etools.applications.permissions2.simplified.tests.permissions import UserIsBobPermission, UserIsAlicePermission
from etools.applications.permissions2.simplified.tests.serializers import ParentSerializer, ChildSerializer, \
    ModelWithFSMFieldSerializer
from etools.applications.permissions2.simplified.views import SimplePermittedViewSetMixin, \
    SimplePermittedFSMTransitionActionMixin


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


class ModelWithFSMFieldViewSet(SimplePermittedViewSetMixin, SimplePermittedFSMTransitionActionMixin,
                               ModelViewSet):
    metadata_class = SimplePermissionBasedMetadata
    queryset = ModelWithFSMField.objects.all()
    serializer_class = ModelWithFSMFieldSerializer
    write_permission_classes = [
        PermissionQ(UserIsBobPermission) | PermissionQ(UserIsAlicePermission)
    ]
    transition_permission_classes = {
        'start': [UserIsAlicePermission],
        'finish': [UserIsBobPermission],
    }
