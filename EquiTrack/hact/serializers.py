from __future__ import absolute_import, division, print_function, unicode_literals

import json

from hact.models import HactHistory
from rest_framework import serializers


class HactHistorySerializer(serializers.ModelSerializer):
    partner_values = serializers.SerializerMethodField()

    def get_partner_values(self, obj):
        return json.loads(obj.partner_values) if isinstance(obj.partner_values, unicode) else obj.partner_values

    class Meta:
        model = HactHistory
        fields = (
            "id",
            "year",
            "created",
            "modified",
            "partner_values",
        )


class HactHistoryExportSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="partner.name")
    partner_type = serializers.CharField(source="partner.partner_type")
    shared = serializers.CharField(source="partner.shared_partner")
    shared_with = serializers.SerializerMethodField()
    total_ct_cp = serializers.CharField(source="partner.total_ct_cp")
    planned_cash_transfer = serializers.SerializerMethodField()
    total_ct_cy = serializers.CharField(source="partner.total_ct_cy")
    micro_assessment_needed = serializers.SerializerMethodField()
    rating = serializers.CharField(source="partner.rating")
    planned_visits = serializers.SerializerMethodField()
    programmatic_visits_required = serializers.SerializerMethodField()
    programmatic_visits_done = serializers.SerializerMethodField()
    spot_checks_required = serializers.SerializerMethodField()
    spot_checks_done = serializers.SerializerMethodField()
    audits_required = serializers.SerializerMethodField()
    audits_done = serializers.SerializerMethodField()
    follow_up_flags = serializers.SerializerMethodField()

    class Meta:
        model = HactHistory
        fields = (
            "name",
            "partner_type",
            "shared",
            "shared_with",
            "total_ct_cp",
            "planned_cash_transfer",
            "total_ct_cy",
            "micro_assessment_needed",
            "rating",
            "planned_visits",
            "programmatic_visits_required",
            "programmatic_visits_done",
            "spot_checks_required",
            "spot_checks_done",
            "audits_required",
            "audits_done",
            "follow_up_flags",
        )

    def _get_hact(self, obj):
        return json.loads(obj.partner_values) if isinstance(obj.partner_values, unicode) else obj.partner_values

    def get_shared_with(self, obj):
        return ", ".join(obj.partner.shared_with)

    def get_planned_cash_transfer(self, obj):
        vals = self._get_hact(obj)
        val = vals.get("planned_cash_transfer", None)
        try:
            val = "{:.2f}".format(val)
        except ValueError:
            pass
        return val

    def get_micro_assessment_needed(self, obj):
        vals = self._get_hact(obj)
        return vals.get("micro_assessment_needed", None)

    def get_planned_visits(self, obj):
        vals = self._get_hact(obj)
        try:
            return vals["programmatic_visits"]["planned"]["total"]
        except KeyError:
            return None

    def get_programmatic_visits_required(self, obj):
        vals = self._get_hact(obj)
        try:
            return vals["programmatic_visits"]["required"]["total"]
        except KeyError:
            return None

    def get_programmatic_visits_done(self, obj):
        vals = self._get_hact(obj)
        try:
            return vals["programmatic_visits"]["completed"]["total"]
        except KeyError:
            return None

    def get_spot_checks_required(self, obj):
        vals = self._get_hact(obj)
        try:
            return vals["spot_checks"]["required"]["total"]
        except KeyError:
            return None

    def get_spot_checks_done(self, obj):
        vals = self._get_hact(obj)
        try:
            return vals["spot_checks"]["completed"]["total"]
        except KeyError:
            return None

    def get_audits_required(self, obj):
        vals = self._get_hact(obj)
        try:
            return vals["audits"]["required"]
        except KeyError:
            return None

    def get_audits_done(self, obj):
        vals = self._get_hact(obj)
        try:
            return vals["audits"]["completed"]
        except KeyError:
            return None

    def get_follow_up_flags(self, obj):
        vals = self._get_hact(obj)
        return vals.get("follow_up_flags", None)
