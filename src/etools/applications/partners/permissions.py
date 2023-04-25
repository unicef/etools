import datetime
from functools import lru_cache

from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext as _

from etools_validator.utils import check_rigid_related
from rest_framework import permissions
from rest_framework.permissions import BasePermission

from etools.applications.environment.helpers import tenant_switch_is_active
from etools.libraries.djangolib.utils import get_all_field_names, is_user_in_groups
from etools.libraries.pythonlib.collections import HashableDict

# READ_ONLY_API_GROUP_NAME is the name of the permissions group that provides read-only access to some list views.
# Initially, this is only being used for PRP-related endpoints.


UNICEF_USER = 'UNICEF User'
READ_ONLY_API_GROUP_NAME = 'Read-Only API'
SENIOR_MANAGEMENT_GROUP = 'Senior Management Team'
PARTNERSHIP_MANAGER_GROUP = 'Partnership Manager'
REPRESENTATIVE_OFFICE_GROUP = 'Representative Office'
PRC_SECRETARY = 'PRC Secretary'


class PMPPermissions:
    # this property specifies an array of model properties in order to check against the permission matrix. The fields
    # declared under this property need to be both property on the model and delcared in the permission matrix
    EXTRA_FIELDS = []
    actions_default_permissions = {
        'edit': True,
        'view': True,
        'required': False
    }
    possible_actions = ['edit', 'required', 'view']

    def __init__(self, user, instance, permission_structure, **kwargs):
        self.MODEL = apps.get_model(self.MODEL_NAME)
        self.user = user
        self.user_groups = list(self.user.groups.values_list('name', flat=True))
        self.instance = instance
        self.condition_group_valid = lru_cache(maxsize=16)(self.condition_group_valid)
        self.permission_structure = permission_structure
        self.all_model_fields = get_all_field_names(self.MODEL)
        self.all_model_fields += self.EXTRA_FIELDS

    def condition_group_valid(self, condition_group):
        if condition_group['status'] and condition_group['status'] != '*':
            if self.instance.status != condition_group['status']:
                return False
        if condition_group['group'] and condition_group['group'] != '*':
            groups = condition_group['group'].split("|")

            # If none of the groups defined match any of the groups in the user groups
            if not set(groups).intersection(set(self.user_groups)):
                return False
        if condition_group['condition'] and condition_group['condition'] != '*':
            # use the following commented line in case we want to not use a condition mapper and interpret the
            # condition directly from the sheet (not recommended)
            # if not eval(condition_group['condition'], globals=globals(), locals=locals()):
            if not self.condition_map[condition_group['condition']]:
                return False
        return True

    def get_field_permissions(self, action, field):
        condition_groups = field[action]

        # For a field and one action (start_date, can_view) you can't define both true conditions and false conditions
        # because if both groups fail, we can't know what to default to
        # this assertion should be in the ingestion script

        # if the "false" conditions were defined that means that by default allowed will be "true"
        # otherwise it means that the "true" conditions were defined and therefore default will be "false"
        default_return = bool(len(condition_groups['false']))

        for allowed in ['true', 'false']:
            for condition_group in condition_groups[allowed]:
                if self.condition_group_valid(HashableDict(condition_group)):
                    return True if allowed == 'true' else False

        return default_return

    def get_permissions(self):
        ps = self.permission_structure

        my_permissions = {}
        for action in self.possible_actions:
            my_permissions[action] = {}
            for field in self.all_model_fields:
                if field not in ps:
                    my_permissions[action][field] = self.actions_default_permissions[action]
                else:
                    my_permissions[action][field] = self.get_field_permissions(action, ps[field])
        return my_permissions


class InterventionPermissions(PMPPermissions):

    MODEL_NAME = 'partners.Intervention'
    EXTRA_FIELDS = ['sections_present', 'pd_outputs', 'final_partnership_review', 'prc_reviews', 'document_currency']

    def __init__(self, **kwargs):
        """
        :param kwargs: user, instance, permission_structure
        # FIXME: This documentation is out of date as the flag check has been commented out.
        if 'inbound_check' key, is sent in, that means that instance now contains all of the fields available in the
        validation: old_instance, old.instance.property_old in case of related fields.
        the reason for this is so that we can check the more complex permissions that can only be checked on save.
        for example: in this case certain field are editable only when user adds an amendment. that means that we would
        need access to the old amendments, new amendments in order to check this.
        """
        super().__init__(**kwargs)

        # Inbound check flag is available here:
        # inbound_check = kwargs.get('inbound_check', False)

        def user_added_amendment(instance):
            return instance.in_amendment is True

        # TODO: remove this as sooon as it expires on July first. Technical Debt - hard coded exception
        def post_epd_temp_conditions(i):
            # quick fix for offices that have not added their amendments in the system before the release date.
            today = datetime.date.today()
            available_til = datetime.date(2023, 7, 1)
            begin_date = datetime.date(2022, 12, 1)
            release_date = datetime.date(2023, 4, 30)
            if i.end and begin_date <= i.end < release_date \
                    and today < available_til \
                    and i.document_type != "SSFA":
                return True
            return False

        def prp_mode_off():
            return tenant_switch_is_active("prp_mode_off")

        def prp_server_on():
            return tenant_switch_is_active("prp_server_on")

        def unlocked(instance):
            return not instance.locked

        def unicef_not_accepted(instance):
            return not instance.unicef_accepted

        def unicef_not_accepted_contingency(instance):
            """ field not required to accept if contingency is on"""
            return instance.contingency_pd or not instance.unicef_accepted

        def unlocked_or_contingency(instance):
            """ field not required to accept if contingency is on"""
            return instance.contingency_pd or not instance.locked

        def is_spd_non_hum(instance):
            # TODO: in the future we might want to add a money condition here (100k is the current limit)
            return instance.document_type == instance.SPD and not instance.humanitarian_flag

        def unicef_not_accepted_spd_non_hum(instance):
            """ field not required to accept if pd is not non-humanitarian spd"""
            # TODO: in the future we might want to add a money condition here (100k is the current limit)
            return is_spd_non_hum(instance) or not instance.unicef_accepted

        def not_spd(instance):
            return not instance.document_type == instance.SPD

        def not_ssfa(instance):
            return not is_spd_non_hum(instance)

        staff_member = self.user

        # focal points are prefetched, so just cast to array to collect ids
        partner_focal_points = [fp.id for fp in self.instance.partner_focal_points.all()]

        if staff_member and staff_member.id == self.instance.partner_authorized_officer_signatory_id:
            self.user_groups.extend(['Partner User', 'Partner Signer'])

        if staff_member and staff_member.id in partner_focal_points:
            self.user_groups.extend(['Partner User', 'Partner Focal Point'])

        if self.user.is_staff and self.user in self.instance.unicef_focal_points.all():
            self.user_groups.append("Unicef Focal Point")
        if self.user.is_staff and self.instance.budget_owner and self.user == self.instance.budget_owner:
            self.user_groups.append("Unicef Budget Owner")
        if self.user.is_staff and self.user in self.instance.unicef_users_involved:
            self.user_groups.append("Unicef Users Involved")

        if self.user.is_staff and self.instance.budget_owner and self.user == self.instance.budget_owner:
            self.user_groups.append("Unicef Budget Owner")

        review = self.instance.review
        if review:
            if self.user.id == review.overall_approver_id:
                self.user_groups.append('Overall Approver')

            if review.prc_reviews.filter(overall_review=review, user=self.user).exists():
                self.user_groups.append('PRC Officer')

        self.user_groups = list(set(self.user_groups))

        self.condition_map = {
            'contingency_on': self.instance.contingency_pd is True,
            'in_amendment_mode': user_added_amendment(self.instance),
            'not_in_amendment_mode': not user_added_amendment(self.instance),
            'not_ssfa': not_ssfa(self.instance),
            'user_adds_amendment': user_added_amendment(self.instance),
            'prp_mode_on': not prp_mode_off(),
            'prp_mode_on+contingency_on': not prp_mode_off() and self.instance.contingency_pd,
            'prp_mode_on+unicef_court': not prp_mode_off() and self.instance.unicef_court,
            'prp_mode_on+partner_court': not prp_mode_off() and not self.instance.unicef_court,
            'prp_mode_off': prp_mode_off(),
            'prp_server_on': prp_server_on(),
            'user_adds_amendment+prp_mode_on': user_added_amendment(self.instance) and not prp_mode_off(),
            'termination_doc_attached': self.instance.termination_doc_attachment.exists(),
            'not_ended': self.instance.end >= datetime.datetime.now().date() if self.instance.end else False,
            'unicef_court': self.instance.unicef_court and unlocked(self.instance),
            'partner_court': not self.instance.unicef_court and unlocked(self.instance),
            'unlocked': unlocked(self.instance),
            'is_spd': self.instance.document_type == self.instance.SPD,
            'is_spd_non_hum': is_spd_non_hum(self.instance),
            'is_pd_unlocked': self.instance.document_type == self.instance.PD and not self.instance.locked,
            'unicef_not_accepted': unicef_not_accepted(self.instance),
            'unicef_not_accepted_contingency': unicef_not_accepted_contingency(self.instance),
            'unlocked_or_contingency': unlocked_or_contingency(self.instance),
            'unicef_not_accepted_spd': not_spd(self.instance) or unicef_not_accepted(self.instance),
            'unlocked_or_spd': not not_spd(self.instance) or unlocked(self.instance),
            'unicef_not_accepted_spd_non_hum': unicef_not_accepted_spd_non_hum(self.instance),
            'not_ssfa+unicef_not_accepted': not_ssfa(self.instance) and unicef_not_accepted(self.instance),
            'post_epd_temp_conditions': post_epd_temp_conditions(self.instance),
        }

    # override get_permissions to enable us to prevent old interventions from being blocked on transitions
    def get_permissions(self):
        def intervention_is_v1():
            if self.instance.status in [self.instance.DRAFT]:
                return False
            return self.instance.start < settings.PMP_V2_RELEASE_DATE if self.instance.start else False

        # TODO: Remove this method when there are no active legacy programme documents
        list_of_new_fields = ["budget_owner",
                              "humanitarian_flag",
                              "unicef_court",
                              "date_sent_to_partner",
                              "unicef_accepted",
                              "partner_accepted",
                              "context",
                              "implementation_strategy",
                              "gender_rating",
                              "gender_narrative",
                              "equity_rating",
                              "equity_narrative",
                              "sustainability_rating",
                              "sustainability_narrative",
                              "ip_program_contribution",
                              "budget_owner",
                              "hq_support_cost",
                              "cash_transfer_modalities",
                              "unicef_review_type",
                              "capacity_development",
                              "other_info",
                              "other_partners_involved",
                              "technical_guidance",
                              "cancel_justification",
                              "population_focus",
                              "risks",
                              "sites",
                              "reporting_requirements",  # these last two fields avoids errors on existing SSFA valid
                              "reference_number_year",
                              "other_details"]
        ps = self.permission_structure
        my_permissions = {}
        for action in self.possible_actions:
            my_permissions[action] = {}
            for field in self.all_model_fields:
                if action == "required" and field in list_of_new_fields and intervention_is_v1():
                    my_permissions[action][field] = False
                elif field in ps:
                    if not ps[field][action]['true'] and not ps[field][action]['false']:
                        my_permissions[action][field] = self.actions_default_permissions[action]
                    else:
                        my_permissions[action][field] = self.get_field_permissions(action, ps[field])
                else:
                    my_permissions[action][field] = self.actions_default_permissions[action]
        return my_permissions


class AgreementPermissions(PMPPermissions):

    MODEL_NAME = 'partners.Agreement'

    def __init__(self, **kwargs):
        """
        :param kwargs: user, instance, permission_structure
        if 'inbound_check' key, is sent in, that means that instance now contains all of the fields available in the
        validation: old_instance, old.instance.property_old in case of related fields.
        the reason for this is so that we can check the more complex permissions that can only be checked on save.
        for example: in this case certain field are editable only when user adds an amendment. that means that we would
        need access to the old amendments, new amendments in order to check this.
        """
        super().__init__(**kwargs)
        inbound_check = kwargs.get('inbound_check', False)

        def termination_doc_attached():
            if self.instance.agreement_type != self.instance.PCA:
                return True
            if self.instance.termination_doc.exists():
                return True
            return False

        def user_added_amendment(instance):
            assert inbound_check, 'this function cannot be called unless instantiated with inbound_check=True'
            # check_rigid_related checks if there were any changes from the previous
            # amendments if there were changes it returns False
            return not check_rigid_related(instance, 'amendments')

        self.condition_map = {
            'is type PCA or MOU': self.instance.agreement_type in [self.instance.PCA, self.instance.MOU],
            'is type PCA or SSFA': self.instance.agreement_type in [self.instance.PCA, self.instance.SSFA],
            'is type SSFA': self.instance.agreement_type == self.instance.SSFA,
            'is type MOU': self.instance.agreement_type == self.instance.MOU,
            # this condition can only be checked on data save
            'user adds amendment': False if not inbound_check else user_added_amendment(self.instance),
            'termination_doc_attached': termination_doc_attached(),
        }


class PartnershipManagerPermission(permissions.BasePermission):
    """Applies general and object-based permissions.

    - For list views --
      - user must be staff or in 'Partnership Manager' group

    - For create views --
      - user must be in 'Partnership Manager' group

    - For retrieve views --
      - user must be (staff or in 'Partnership Manager' group) OR
                     (staff or listed as a partner staff member on the object)

    - For update/delete views --
      - user must be (in 'Partnership Manager' group) OR
                     (listed as a partner staff member on the object)
    """
    message = _('Accessing this item is not allowed.')

    def _has_access_permissions(self, user, obj):
        """True if --
              - user is staff OR
              - user is 'Partnership Manager' group member OR
              - user is listed as a partner staff member on the object, assuming the object has a partner attribute
        """
        has_access = user.is_staff or is_user_in_groups(user, [PARTNERSHIP_MANAGER_GROUP])
        if has_access:
            return True

        has_access = hasattr(obj, 'partner') and obj.partner.user_is_staff_member(user)
        return has_access

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return request.user.is_staff or is_user_in_groups(request.user, [PARTNERSHIP_MANAGER_GROUP])
        else:
            return is_user_in_groups(request.user, [PARTNERSHIP_MANAGER_GROUP])

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and \
                is_user_in_groups(request.user, [PARTNERSHIP_MANAGER_GROUP])


class PartnershipManagerRepPermission(permissions.BasePermission):
    message = _('Accessing this item is not allowed.')

    def _has_access_permissions(self, user, object):
        if user.is_staff or object.partner.user_is_staff_member(user):
            return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and is_user_in_groups(
                request.user,
                [
                    PARTNERSHIP_MANAGER_GROUP,
                    SENIOR_MANAGEMENT_GROUP,
                    REPRESENTATIVE_OFFICE_GROUP,
                ]
            )


class PartnershipSeniorManagerPermission(permissions.BasePermission):
    message = _('Accessing this item is not allowed.')

    def _has_access_permissions(self, user, object):
        if user.is_staff or object.partner.user_is_staff_member(user):
            return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and is_user_in_groups(
                request.user,
                [PARTNERSHIP_MANAGER_GROUP, SENIOR_MANAGEMENT_GROUP]
            )


class ListCreateAPIMixedPermission(permissions.BasePermission):
    """Permission class for ListCreate views that want to allow read-only access to some groups and read-write
    to others.

    GET users must be either (a) staff or (b) in the Limited API group.

    POST users must be staff.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_authenticated:
                if request.user.is_staff or is_user_in_groups(request.user, [READ_ONLY_API_GROUP_NAME]):
                    return True
            return False
        elif request.method == 'POST':
            # user must have have admin access
            return request.user.is_authenticated and request.user.is_staff
        else:
            # This class shouldn't see methods other than GET and POST, but regardless the answer is 'no you may not'.
            return False


class AllowSafeAuthenticated(permissions.BasePermission):
    """"only read permissions if authenticated, no write"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_authenticated:
                return True
        return False


class ReadOnlyAPIUser(permissions.BasePermission):
    """Permission class for Views that only allow read and only for backend api users or superusers
        GET users must be either (a) superusers or (b) in the Limited API group.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_authenticated:
                if request.user.is_superuser or is_user_in_groups(request.user, [READ_ONLY_API_GROUP_NAME]):
                    return True
            return False
        else:
            # This class shouldn't see methods other than GET, but regardless the answer is 'no you may not'.
            return False


def intervention_field_is_editable_permission(field):
    """
    Check the user is able to edit selected monitoring activity field.
    View should either implement get_root_object to return instance of Intervention (if view is nested),
    or return Intervention instance via get_object (can be used for detail actions).
    """

    from etools.applications.partners.models import Intervention

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

            ps = Intervention.permission_structure()
            permissions = InterventionPermissions(
                user=request.user, instance=instance, permission_structure=ps
            )
            return permissions.get_permissions()['edit'].get(field)

    return FieldPermission


def view_action_permission(*actions):
    class ViewActionPermission(BasePermission):
        def has_permission(self, request, view):
            return request.method.upper() in actions

    return ViewActionPermission


def user_group_permission(*groups):
    class UserGroupPermission(BasePermission):
        def has_permission(self, request, view):
            return request.user.is_authenticated and is_user_in_groups(request.user, groups)

    return UserGroupPermission


class UserIsPartnerStaffMemberPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.get_partner()


class UserIsNotPartnerStaffMemberPermission(BasePermission):
    def has_permission(self, request, view):
        return not request.user.get_partner()


class UserIsObjectPartnerStaffMember(UserIsPartnerStaffMemberPermission):
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'partner'):
            return False

        return obj.partner.user_is_staff_member(request.user)


class UserIsStaffPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff


class IsSafeMethodPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsUnsafeMethodPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method not in permissions.SAFE_METHODS


"""
PartnershipManagerPermission is too broad, so we can't just add partners and be sure it wouldn't have side effects.
Rewritten using smaller permissions from comment describing how it should work.

Applies general and object-based permissions.

- For list views --
  - user must be staff or in 'Partnership Manager' group

- For create views --
  - user must be in 'Partnership Manager' group

- For retrieve views --
  - user must be (staff or in 'Partnership Manager' group) OR
                 (staff or listed as a partner staff member on the object)
    # equals to: staff or in 'Partnership Manager' group or listed as a partner staff member on the object

- For update/delete views --
  - user must be (in 'Partnership Manager' group) OR
                 (listed as a partner staff member on the object)
"""
PartnershipManagerRefinedPermission = (
    view_action_permission('OPTIONS') |
    (view_action_permission('GET') & (UserIsStaffPermission | user_group_permission(PARTNERSHIP_MANAGER_GROUP))) |
    (view_action_permission('POST') & user_group_permission(PARTNERSHIP_MANAGER_GROUP)) |
    (
        view_action_permission('GET') &
        (UserIsStaffPermission | user_group_permission(PARTNERSHIP_MANAGER_GROUP) | UserIsObjectPartnerStaffMember)
    ) |
    (
        view_action_permission('PUT', 'PATCH', 'DELETE') &
        (user_group_permission(PARTNERSHIP_MANAGER_GROUP) | UserIsObjectPartnerStaffMember)
    )
)

# allow partners to load list ONLY for interventions to keep everything
# else working right as before; at least for now
PMPInterventionPermission = (
    PartnershipManagerRefinedPermission | (view_action_permission('GET') & UserIsPartnerStaffMemberPermission)
)

# allow partners to load list ONLY for agreements to keep everything
# else working right as before; at least for now
PMPAgreementPermission = (
    (view_action_permission('POST') & (
        UserIsStaffPermission | user_group_permission('Partnership Manager')
    )) |
    (view_action_permission('GET') & (
        UserIsPartnerStaffMemberPermission | (
            UserIsStaffPermission | user_group_permission('Partnership Manager')
        )
    ))
)


class UserBelongsToObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'user'):
            return False

        return obj.user == request.user


class IsInterventionBudgetOwnerPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(view, 'get_root_object'):
            obj = view.get_root_object()
        return obj.budget_owner and obj.budget_owner == request.user


class AmendmentSessionOnlyDeletePermission(BasePermission):
    """
    Lock activities created before current amendment
    """
    def has_object_permission(self, request, view, obj):
        if request.method.upper() != 'DELETE':
            return True

        intervention = view.get_root_object()
        if not hasattr(intervention, 'amendment'):
            return True

        amendment = intervention.amendment
        return obj.created > amendment.created


class InterventionIsDraftPermission(BasePermission):
    def has_permission(self, request, view):
        intervention = view.get_root_object()
        return intervention.status == 'draft'


class InterventionAmendmentIsNotCompleted(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.is_active


class UserIsUnicefFocalPoint(BasePermission):
    def has_permission(self, request, view):
        intervention = view.get_root_object()
        return request.user in intervention.unicef_focal_points.all()
