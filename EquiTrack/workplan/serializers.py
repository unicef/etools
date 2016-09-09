from django.contrib.auth.models import User
from rest_framework import serializers

from users.models import Section
from partners.models import PartnerOrganization
from locations.models import Location

from .models import Comment, Workplan, ResultWorkplanProperty, Label


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment


class WorkplanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workplan


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label


class ResultWorkplanPropertySerializer(serializers.ModelSerializer):

    sections = serializers.PrimaryKeyRelatedField(
                many=True,
                read_only=False,
                queryset=Section.objects.all()
            )
    geotag = serializers.PrimaryKeyRelatedField(
                many=True,
                read_only=False,
                queryset=Location.objects.all()
            )
    partners = serializers.PrimaryKeyRelatedField(
                many=True,
                read_only=False,
                queryset=PartnerOrganization.objects.all()
            )
    responsible_persons = serializers.PrimaryKeyRelatedField(
                many=True,
                read_only=False,
                queryset=User.objects.all()
            )

    class Meta:
        model = ResultWorkplanProperty
