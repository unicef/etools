
from rest_framework import serializers
from .models import Comment, Workplan


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment


class WorkplanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workplan