__author__ = 'achamseddine'

from django.contrib.sites.models import Site

from rest_framework import serializers

from .models import (
    TPMVisit
)


class TPMVisitSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = TPMVisit
        fields = (
            'id',
            'status',
            'cycle_number',
            'tentative_date',
            'completed_date',
            'comments',
            'created_date',
            'pca',
            'pca_location',
            'assigned_by'
        )
