from rest_framework import serializers

from etools.applications.field_monitoring.fm_settings.models import CheckListItem, CheckListCategory


class CheckListCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckListCategory
        fields = ('id', 'name')


class CheckListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckListItem
        fields = ('id', 'category', 'question_number', 'question_text', 'is_required')
