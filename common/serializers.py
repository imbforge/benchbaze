from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import LayoutFrontend

User = get_user_model()


def build_model_serializer(model_obj, serializer, field_names, *args, **kwargs):
    """
    Based on https://stackoverflow.com/questions/297383
    Create a serializer on the fly where the Meta class's model
    and fields are set dynamically
    """

    class DynamicModelSerializer(serializer):
        representation = serializers.SerializerMethodField()

        class Meta:
            model = model_obj
            fields = field_names + ["representation"]

        def __init__(self, *args_init, **kwargs_init):
            kwargs_copy = kwargs_init.copy()
            # if "model" in kwargs_copy:
            #     del kwargs_copy["model"]
            super().__init__(*args_init, **kwargs_copy)

        def get_representation(self, obj):
            return str(obj)

    return DynamicModelSerializer


class UserSerializer(serializers.HyperlinkedModelSerializer):
    representation = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "representation",
        )

    def get_representation(self, obj):
        return str(obj)


class LogEntrySerializer(serializers.ModelSerializer):
    representation = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = LogEntry
        fields = [
            "id",
            "representation",
            "action_flag",
            "user",
            "content_type",
            "action_time",
        ]

    def get_representation(self, obj):
        try:
            edited_object = obj.get_edited_object()
            return getattr(
                edited_object,
                getattr(edited_object, "_representation_field", ""),
                obj.object_repr,
            )
        except:
            return obj.object_repr

    def get_id(self, obj):
        return obj.object_id


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
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
        )
        read_only = (
            "id",
            "first_name",
            "last_name",
            "email",
        )


class ListSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if "approval" in representation:
            representation["approval"] = instance.approval_formatted()
        return representation


class ItemSerializer(serializers.ModelSerializer):
    pass
