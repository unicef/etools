from rest_framework import serializers

from reports.models import Result


class ResultListSerializer(serializers.ModelSerializer):

    result_type = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Result
        fields = '__all__'
