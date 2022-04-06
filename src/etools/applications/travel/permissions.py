from rest_framework.permissions import BasePermission

from etools.applications.partners.permissions import PMPPermissions


class UserIsStaffPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff


class TripPermissions(PMPPermissions):
    MODEL_NAME = 'travel.Trip'
    EXTRA_FIELDS = []

    def __init__(self, user, instance, permission_structure, **kwargs):
        """
        :param kwargs: user, instance, permission_structure
        if 'inbound_check' key, is sent in, that means that instance now
        contains all of the fields available in the validation:
        old_instance, old.instance.property_old in case of related fields.
        the reason for this is so that we can check the more complex
        permissions that can only be checked on save.
        for example: in this case certain field are editable only when user
        adds an amendment. that means that we would need access to the old
        amendments, new amendments in order to check this.
        """
        super().__init__(user, instance, permission_structure, **kwargs)

        self.condition_map = {}
        # TODO: remove after epd branch is merged in:
        self.user_groups = list(self.user_groups)

        if self.user == self.instance.traveller:
            self.user_groups.extend(['Traveller'])


def trip_field_is_editable_permission(field):
    """
    Check the user is able to edit selected monitoring activity field.
    View should either implement get_root_object to return instance of Intervention (if view is nested),
    or return Intervention instance via get_object (can be used for detail actions).
    """

    from etools.applications.travel.models import Trip

    class FieldPermission(BasePermission):
        def has_permission(self, request, view):
            if not view.kwargs:
                # This is needed for swagger to be able to build the correct structure
                # https://github.com/unicef/etools/pull/2540/files#r356446025
                return True

            if hasattr(view, 'get_root_object'):
                instance = view.get_root_object()
            else:
                instance = view.get_object()

            ps = Trip.permission_structure()
            permissions = TripPermissions(
                user=request.user, instance=instance, permission_structure=ps
            )
            return permissions.get_permissions()['edit'].get(field)

    return FieldPermission
