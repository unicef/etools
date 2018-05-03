from rest_framework import serializers

from etools.applications.partners.models import FileType


class FileTypeSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = FileType
        fields = '__all__'
