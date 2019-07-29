from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from django_comments.models import Comment, CommentFlag
from unicef_attachments.models import Attachment

from etools.applications.action_points.models import ActionPoint
from etools.applications.audit.purchase_order.models import AuditorStaffMember
from etools.applications.management.handlers.base import GlobalHandler
from etools.applications.partners.models import Agreement, Assessment, Intervention
from etools.applications.t2f.models import Travel, TravelActivity
from etools.applications.tpm.models import TPMActivity, TPMVisit
from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember
from etools.applications.users.models import Office, UserProfile


class UserHandler(GlobalHandler):

    model = get_user_model()

    global_queryset_migration_mapping = (
        (Group.objects.all(), 'user'),
        (Office.objects.all(), 'zonal_chief'),
        (UserProfile.objects.all(), 'supervisor'),
        (AuditorStaffMember.objects.all(), 'user'),
        (TPMPartnerStaffMember.objects.all(), 'user'),
    )

    queryset_migration_mapping = (
        (Assessment.objects.all(), 'requesting_officer'),
        (Assessment.objects.all(), 'approving_officer'),
        (Agreement.objects.all(), 'signed_by'),
        (Intervention.objects.all(), 'unicef_signatory'),
        (Intervention.objects.all(), 'unicef_focal_points'),
        (Travel.objects.all(), 'traveler'),
        (Travel.objects.all(), 'supervisor'),
        (TravelActivity.objects.all(), 'primary_traveler'),
        (ActionPoint.objects.all(), 'author'),
        (ActionPoint.objects.all(), 'assigned_by'),
        (ActionPoint.objects.all(), 'assigned_to'),
        (Comment.objects.all(), 'user'),
        (CommentFlag.objects.all(), 'user'),
        (Attachment.objects.all(), 'uploaded_by'),
        (TPMVisit.objects.all(), 'author'),
        (TPMActivity.objects.all(), 'unicef_focal_points'),
    )
