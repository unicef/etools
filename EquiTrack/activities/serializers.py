from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import serializers


class ActivitySerializer(serializers.ModelSerializer):
    def _get_implementing_partner(self):
        if self.instance:
            return self.instance.implementing_partner
        return None

    def _get_intervention(self):
        if self.instance:
            return self.instance.intervention
        return None

    def _get_cp_output(self):
        if self.instance:
            return self.instance.cp_output
        return None

    def _validate_intervention_and_partner(self, attrs):
        implementing_partner = attrs.get('implementing_partner', serializers.empty)
        intervention = attrs.get('intervention', serializers.empty)

        if implementing_partner is serializers.empty and intervention is serializers.empty:
            return attrs

        if implementing_partner is serializers.empty:
            implementing_partner = self._get_implementing_partner()

        if intervention is serializers.empty:
            intervention = self._get_intervention()

        self.Meta.model._validate_intervention(implementing_partner, intervention)

        return attrs

    def _validate_cp_output_and_intervention(self, attrs):
        intervention = attrs.get('intervention', serializers.empty)
        cp_output = attrs.get('cp_output', serializers.empty)

        if intervention is serializers.empty and cp_output is serializers.empty:
            return attrs

        if intervention is serializers.empty:
            intervention = self._get_intervention()

        if cp_output is serializers.empty:
            cp_output = self._get_cp_output()

        self.Meta.model._validate_cp_output(intervention, cp_output)

        return attrs

    def validate(self, attrs):
        attrs = super(ActivitySerializer, self).validate(attrs)
        attrs = self._validate_intervention_and_partner(attrs)
        attrs = self._validate_cp_output_and_intervention(attrs)
        return attrs
