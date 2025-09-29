from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import LayoutFrontend

User = get_user_model()


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class LayoutFrontendSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayoutFrontend
        fields = "__all__"


class NavigationSerializer(serializers.ModelSerializer):
    app_verbose_name = serializers.SerializerMethodField()
    model_class_name = serializers.SerializerMethodField()
    model_verbose_name = serializers.SerializerMethodField()
    model_verbose_plural = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    listview_fields_frozen = serializers.SerializerMethodField()
    listview_fields = serializers.SerializerMethodField()
    addview_fields = serializers.SerializerMethodField()
    changeview_fields = serializers.SerializerMethodField()
    readonly_fields = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        field_names_empty_list = [
            "listview_fields_frozen",
            "listview_fields",
            "addview_fields",
            "changeview_fields",
            "readonly_fields",
            "actions",
        ]

        # Create get_ methods for the dummy, empty list, fields
        for field_name in field_names_empty_list:
            # Setting an attribute dynamically for the field does not work
            # setattr(self, field_name, serializers.SerializerMethodField())
            setattr(self, f"get_{field_name}", lambda cls: list())

        # Update the Meta class fields attribute
        self.Meta.fields = self.Meta.fields + field_names_empty_list

        super().__init__(*args, **kwargs)

    class Meta:
        model = ContentType
        fields = [
            "id",
            "app_label",
            "app_verbose_name",
            "model_class_name",
            "model_verbose_name",
            "model_verbose_plural",
            "permissions",
        ]

    def get_app_verbose_name(self, obj):
        return obj.app_verbose_name

    def get_model_class_name(self, obj):
        return obj.model_name

    def get_model_verbose_name(self, obj):
        return obj.model_verbose_name

    def get_model_verbose_plural(self, obj):
        return obj.model_verbose_plural

    def get_permissions(self, obj):
        return obj.permissions


class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email")
        read_only = (
            "id",
            "first_name",
            "last_name",
            "email",
        )


class ListSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if "created_by" in representation:
            representation["created_by"] = str(instance.created_by)
        if "approval" in representation:
            representation["approval"] = instance.approval_formatted()
        return representation


class ItemSerializer(serializers.ModelSerializer):
    pass
