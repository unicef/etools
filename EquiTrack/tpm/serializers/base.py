# todo: move this to staff members app
class SetStaffMemberCountryMixin(object):
    def create(self, validated_data):
        instance = super(SetStaffMemberCountryMixin, self).create(validated_data)
        request = self.context.get('request', None)

        profile = instance.user.profile
        if request and request.user and request.user.is_authenticated():
            profile.country = request.user.profile.country
            profile.save()
        return instance
