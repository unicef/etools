from unicef_restlib.metadata import FSMTransitionActionMetadataMixin

from etools.applications.permissions2.metadata import PermissionsBasedMetadataMixin, BaseMetadata


class SimplePermissionBasedMetadata(FSMTransitionActionMetadataMixin, PermissionsBasedMetadataMixin, BaseMetadata):
    """Base metadata class handling permissions"""
    pass
