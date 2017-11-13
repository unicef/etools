from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import serializers


class ActivitySerializer(serializers.ModelSerializer):
    def _get_implementing_partner(self):
        if self.instance:
            return self.instance.implementing_partner
        return None

    def _get_partnership(self):
        if self.instance:
            return self.instance.partnership
        return None

    def _get_cp_output(self):
        if self.instance:
            return self.instance.cp_output
        return None

    def _validate_partnership_and_partner(self, attrs):
        implementing_partner = attrs.get('implementing_partner', serializers.empty)
        partnership = attrs.get('partnership', serializers.empty)

        if implementing_partner is serializers.empty and partnership is serializers.empty:
            return attrs

        if implementing_partner is serializers.empty:
            implementing_partner = self._get_implementing_partner()

        if partnership is serializers.empty:
            partnership = self._get_partnership()

        self.meta.model._validate_partnership(implementing_partner, partnership)

        return attrs

    def _validate_cp_output_and_partnership(self, attrs):
        partnership = attrs.get('partnership', serializers.empty)
        cp_output = attrs.get('cp_output', serializers.empty)

        if partnership is serializers.empty and cp_output is serializers.empty:
            return attrs

        if partnership is serializers.empty:
            partnership = self._get_partnership()

        if cp_output is serializers.empty:
            cp_output = self._get_cp_output()

        self.meta.model._validate_cp_output(partnership, cp_output)

        return attrs

    def validate(self, attrs):
        attrs = super(ActivitySerializer, self).validate(attrs)
        attrs = self._validate_partnership_and_partner(attrs)
        attrs = self._validate_cp_output_and_partnership(attrs)
        return attrs
