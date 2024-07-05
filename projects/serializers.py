from collections import defaultdict
from typing import Any

from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from projects.models import Project, ProjectUserPermission
from users.serializers import UserPublicSerializer


class ProjectBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("type", "id", "name", "slug")


class TagSerializer(ProjectBaseSerializer):
    class Meta:
        model = Project
        fields = ProjectBaseSerializer.Meta.fields


class CategorySerializer(ProjectBaseSerializer):
    class Meta:
        model = Project
        fields = ProjectBaseSerializer.Meta.fields + ("description", )


class TopicSerializer(ProjectBaseSerializer):
    class Meta:
        model = Project
        fields = ProjectBaseSerializer.Meta.fields + ("emoji", "section")


class MiniTournamentSerializer(ProjectBaseSerializer):
    class Meta:
        model = Project
        fields = ProjectBaseSerializer.Meta.fields + (
            "prize_pool",
            "start_date",
            "close_date",
            "meta_description",
            "is_ongoing",
            "user_permission",
            "created_at",
            "edited_at",
        )


class TournamentSerializer(ProjectBaseSerializer):
    class Meta:
        model = Project
        fields = ProjectBaseSerializer.Meta.fields + (
            "subtitle",
            "description",
            "header_image",
            "header_logo",
            "prize_pool",
            "start_date",
            "close_date",
            "meta_description",
            "is_ongoing",
            "user_permission",
            "created_at",
            "edited_at",
        )


def serialize_project(project: Project) -> dict:
    match project.type:
        case Project.ProjectTypes.TAG:
            serializer = TagSerializer
        case Project.ProjectTypes.TOPIC:
            serializer = TopicSerializer
        case Project.ProjectTypes.CATEGORY:
            serializer = CategorySerializer
        case Project.ProjectTypes.TOURNAMENT:
            serializer = MiniTournamentSerializer
        case Project.ProjectTypes.QUESTION_SERIES:
            serializer = MiniTournamentSerializer
        case _:
            serializer = ProjectBaseSerializer

    return serializer(project).data


def serialize_projects(projects: list[Project]) -> defaultdict[Any, list]:
    data = defaultdict(list)

    for obj in projects:
        data[obj.type].append(serialize_project(obj))

    return data


def validate_categories(lookup_field: str, lookup_values: list):
    categories = (
        Project.objects.filter_category()
        .filter_active()
        .filter(**{f"{lookup_field}__in": lookup_values})
    )
    lookup_values_fetched = {getattr(obj, lookup_field) for obj in categories}

    for value in lookup_values:
        if value not in lookup_values_fetched:
            raise ValidationError(f"Category {value} does not exist")

    return categories


def validate_tournaments(lookup_values: list):
    slug_values = []
    id_values = []

    for value in lookup_values:
        if value.isdigit():
            id_values.append(int(value))
        else:
            slug_values.append(value)

    tournaments = (
        Project.objects.filter_tournament()
        .filter_active()
        .filter(Q(**{f"slug__in": slug_values}) | Q(pk__in=id_values))
    )

    lookup_values_fetched = {obj.slug for obj in tournaments}
    lookup_values_fetched_id = {obj.pk for obj in tournaments}

    for value in slug_values:
        if value not in lookup_values_fetched:
            raise ValidationError(f"Tournament with slug `{value}` does not exist")

    for value in id_values:
        if value not in lookup_values_fetched_id:
            raise ValidationError(f"Tournament with id `{value}` does not exist")

    return tournaments


class PostProjectWriteSerializer(serializers.Serializer):
    categories = serializers.ListField(child=serializers.IntegerField(), required=False)
    tournaments = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )

    def validate_categories(self, values: list[int]) -> list[Project]:
        return validate_categories(lookup_field="id", lookup_values=values)

    def validate_tournaments(self, values: list[int]) -> list[Project]:
        return validate_tournaments(lookup_values=values)


class ProjectUserSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer()

    class Meta:
        model = ProjectUserPermission
        fields = (
            "user",
            "permission",
        )


class ProjectFilterSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    types = serializers.MultipleChoiceField(
        choices=Project.ProjectTypes.choices, required=False
    )
