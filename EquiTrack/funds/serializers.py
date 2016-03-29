__author__ = 'achamseddine'

from rest_framework import serializers

from .models import Donor, Grant


class DonorSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Donor
        fields = (
            'id',
            'name'
        )


class GrantSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Grant
        fields = (
            'id',
            'name',
            'donor'
        )


