from django.contrib.auth.models import User
from rest_framework import serializers


from users.models import Section
from partners.models import PartnerOrganization
from locations.models import Location

from .models import Comment, Workplan, ResultWorkplanProperty, WorkplanProject, CoverPage, CoverPageBudget, Label



class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id', 'author', 'tagged_users', 'text', 'timestamp', 'workplan')


class WorkplanSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True)

    class Meta:
        model = Workplan
        fields = ('id', 'status', 'result_structure', 'workplan_projects', 'comments')


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


class CoverPageBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoverPageBudget


class CoverPageSerializer(serializers.ModelSerializer):
    budgets = CoverPageBudgetSerializer(many=True)

    class Meta:
        model = CoverPage
        fields = ('id', 'workplan_project', 'national_priority', 'responsible_government_entity', 'planning_assumptions',
                  'budgets', 'logo')


class WorkplanProjectSerializer(serializers.ModelSerializer):
    cover_page = CoverPageSerializer()

    class Meta:
        model = WorkplanProject