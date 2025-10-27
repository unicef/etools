from django.contrib.auth import get_user_model
from django.utils import timezone

from etools.applications.last_mile import models


class LMProfileStatusUpdater:

    def __init__(self, admin_validator):
        self.admin_validator = admin_validator

    def bulk_update(self, validated_data, approver_user):
        status = validated_data.get('status', None)
        review_notes = validated_data.get('review_notes', None)
        users = validated_data.get('user_ids', None)
        list_profile_bulk_update = []
        list_user_bulk_update = []
        for user in users:
            self.admin_validator.validate_last_mile_profile(user)
            user.is_active = status == models.Profile.ApprovalStatus.APPROVED
            user.realms.update(is_active=status == models.Profile.ApprovalStatus.APPROVED)
            last_mile_profile = user.last_mile_profile
            if last_mile_profile.created_by:
                self.admin_validator.validate_user_can_approve(last_mile_profile.created_by.id, approver_user.id)
            last_mile_profile.status = status
            last_mile_profile.review_notes = review_notes
            last_mile_profile.approved_by = approver_user
            last_mile_profile.approved_on = timezone.now()
            list_profile_bulk_update.append(last_mile_profile)
            list_user_bulk_update.append(user)
        models.Profile.objects.bulk_update(list_profile_bulk_update, ['status', 'review_notes', 'approved_by', 'approved_on'])
        get_user_model().objects.bulk_update(list_user_bulk_update, ['is_active'])
        return validated_data

    def update(self, instance, validated_data, approver_user):
        self.admin_validator.validate_last_mile_profile(instance)
        last_mile_profile = instance.last_mile_profile
        if last_mile_profile.created_by:
            self.admin_validator.validate_user_can_approve(last_mile_profile.created_by.id, approver_user.id)
        status = validated_data.pop('status', None)
        self.admin_validator.validate_status(status)
        review_notes = validated_data.pop('review_notes', None)
        if status == models.Profile.ApprovalStatus.APPROVED:
            last_mile_profile.approve(approver_user, review_notes)
            instance.is_active = True
            instance.realms.update(is_active=True)
            instance.save(update_fields=['is_active'])
        elif status == models.Profile.ApprovalStatus.REJECTED:
            last_mile_profile.reject(approver_user, review_notes)
            instance.is_active = False
            instance.realms.update(is_active=False)
            instance.save(update_fields=['is_active'])
        return last_mile_profile
