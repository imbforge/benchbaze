from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.text import capfirst
from rest_framework import permissions, renderers, viewsets
from rest_framework.decorators import action as rest_action
from rest_framework.response import Response

from .models import LayoutFrontend
from .paginators import StandardResultsSetPagination
from .serializers import (
    ItemSerializer,
    LayoutFrontendSerializer,
    ListSerializer,
    NavigationSerializer,
    UserSerializer,
)

User = get_user_model()


class PassthroughRenderer(renderers.BaseRenderer):
    """
    Return data from a viewset action as-is.

    """

    media_type = ""
    format = ""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class UserViewSet(viewsets.ModelViewSet):
    """Show user information"""

    queryset = User.objects.all()
    pagination_class = None
    serializer_class = UserSerializer

    @rest_action(detail=False)
    def whoami(self, request):
        """Show the logged user"""
        serializer = self.serializer_class(request.user)
        return Response(serializer.data)


class LayoutFrontendViewSet(viewsets.ModelViewSet):
    """Show frontend layout information"""

    queryset = LayoutFrontend.objects.all()
    serializer_class = LayoutFrontendSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None


class NavigationViewSet(viewsets.ModelViewSet):
    """Show frontend layout information"""

    queryset = ContentType.objects.all()
    serializer_class = NavigationSerializer
    pagination_class = None

    def get_object(self, request=None):
        """
        The same as parent but accepts a request too and
        uses a queryset as a list not an actual queryset
        """
        queryset = self.filter_queryset(self.get_queryset(), request)

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly."
            % (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = next(
            (e for e in queryset if str(e.pk) == filter_kwargs.get("pk", None)), None
        )

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def filter_queryset(self, queryset, request=None):
        """
        Filter queryset of content types and return only those
        for which the logged user has add/change/view permissions
        is the model's _show_in_frontend attribute is True
        """

        filtered = []

        for ct in queryset:
            # Check whether user has any perms for the given app
            has_module_perms = request.user.has_module_perms(ct.app_label)
            if not has_module_perms:
                continue

            # Check whether user has any perms for the given model
            perms = {
                action: request.user.has_perm(
                    f"{ct.app_label}.{f'{action}_{ct.model}'}"
                )
                for action in ["add", "change", "view"]
            }
            if True not in perms.values():
                continue

            # Return model
            try:
                model = ct.model_class()

                # If model has _show_in_frontend
                if getattr(model, "_show_in_frontend", False):
                    # Set additional attributes in ct
                    ct.model_name = model._meta.object_name
                    ct.model_verbose_name = capfirst(
                        model._meta.verbose_name
                        if isinstance(model._show_in_frontend, bool)
                        else getattr(
                            model, "_frontend_verbose_name", model._meta.verbose_name
                        )
                    )
                    ct.model_verbose_plural = capfirst(
                        model._meta.verbose_name_plural
                        if isinstance(model._show_in_frontend, bool)
                        else getattr(
                            model,
                            "_frontend_verbose_plural",
                            model._meta.verbose_name_plural,
                        )
                    )
                    ct.app_verbose_name = apps.get_app_config(ct.app_label).verbose_name
                    ct.permissions = perms
                    filtered.append(ct)
            except Exception:
                continue

        return filtered

    def retrieve(self, request, *args, **kwargs):
        """The same as super but accepts a request too"""

        instance = self.get_object(request)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """The same as super but accepts a request too"""

        queryset = self.filter_queryset(self.get_queryset(), request)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @staticmethod
    def _get_field_details(model, field_names):
        """
        Given a list of field names for a model, return their details
        e.g.
        ["id", "name"]
        ->
        [
        {"name": "id",
         "verbose_name": "ID",
         "field_type": "AutoField"},
        {"name": "name",
         "verbose_name": "Name",
         "field_type": "CharField"},
        ]
        """

        ret = []
        for field_name in field_names:
            field_name_stripped = field_name
            use_api = False

            # Remove placeholder suffix that indicates formatted field
            formatted = field_name if "_formatted" in field_name else False
            if formatted:
                use_api = getattr(getattr(model, field_name, None), "use_api", False)
                field_name_stripped = field_name_stripped.replace("_formatted", "")

            try:
                # Get field details
                field = model._meta.get_field(field_name_stripped)
                field = {
                    "name": field.name if not use_api else field_name,
                    "verbose_name": capfirst(field.verbose_name),
                    # If field is formatted, get field_type from
                    # formatting function
                    "field_type": getattr(
                        getattr(model, field_name, None), "field_type", None
                    )
                    if formatted
                    else field.get_internal_type(),
                }
                ret.append(field)
            except Exception:
                continue
        return ret

    @rest_action(detail=True, methods=["get"])
    def listview_fields(self, request, pk=None):
        """
        Shows the fields to display in the list view of
        a model
        """

        model = ContentType.objects.get(pk=pk).model_class()
        return Response(
            [
                self._get_field_details(model, fields)
                for fields in (
                    getattr(model, "_list_display_frozen", []),
                    getattr(model, "_list_display", []),
                )
            ]
        )

    @rest_action(detail=True, methods=["get"])
    def addview_fields(self, request, pk=None):
        """
        Shows the fields to display in the add view of
        a model
        """

        model = ContentType.objects.get(pk=pk).model_class()
        return Response(
            self._get_field_details(
                model,
                [
                    f
                    for e in getattr(model, "_add_view_fieldsets", [])
                    for f in e[1]["fields"]
                ],
            )
        )

    @rest_action(detail=True, methods=["get"])
    def changeview_fields(self, request, pk=None):
        """
        Shows the fields to display in the change view of
        a model
        """

        model = ContentType.objects.get(pk=pk).model_class()
        fieldsets = getattr(model, "_change_view_fieldsets", list())
        return Response(
            [
                [
                    fieldset[0],
                    {"fields": self._get_field_details(model, fieldset[1]["fields"])},
                ]
                for fieldset in fieldsets
            ]
        )

    @rest_action(detail=True, methods=["get"])
    def action_list(self, request, pk=None):
        """Shows the actions for a model"""

        model = ContentType.objects.get(pk=pk).model_class()
        actions = getattr(model, "_actions", list())
        return Response(
            [
                {
                    "name": a.__name__,
                    "label": getattr(a, "short_description", None),
                    "icon": getattr(a, "icon", None),
                }
                for a in actions
            ]
        )

    @rest_action(methods=["get"], detail=True, renderer_classes=(PassthroughRenderer,))
    def action(self, request, pk=None):
        """Shows the actions for a model"""

        model = ContentType.objects.get(pk=pk).model_class()
        action_name = request.GET.getlist("action_name", [""])[0]
        item_ids = request.GET.getlist("id", [])
        action = next((a for a in model._actions if a.__name__ == action_name), None)
        if len(item_ids) == 1 and item_ids[0] == "0":
            queryset = model.objects.all()
        else:
            queryset = model.objects.filter(id__in=item_ids)

        return action(model, request, queryset)


class ModelViewSet(viewsets.ModelViewSet):
    """
    Generic viewset for a model
    """

    serializer_class = ListSerializer
    pagination_class = StandardResultsSetPagination
    serializer_list_class = ListSerializer
    serializer_item_class = ItemSerializer

    def get_queryset(self):
        # Get requested model based on the url parameters app_label and model
        # and set it in self.model and self.queryset
        self.model = ContentType.objects.get(
            app_label=self.kwargs["app_label"], model=self.kwargs["model"]
        ).model_class()
        self.queryset = self.model.objects.all()
        return super().get_queryset()

    @rest_action(detail=True, methods=["get"])
    def readonly_fields(self, request, pk=None, **kwargs):
        """
        Returns  which fields are readonly for the instance of
        of an model class
        """
        obj = self.get_object()
        return Response(obj.readonly_fields(request))

    @rest_action(detail=True, methods=["get"])
    def history(self, *args, **kwargs):
        """Returns the history of an object"""

        obj = self.get_object()
        created_history_obj = obj.history.filter(history_type="+").earliest()
        ret = [
            {
                "timestamp": created_history_obj.history_date.isoformat(),
                "activity_user": created_history_obj.history_user.id,
                "activity_user_pretty": str(created_history_obj.history_user),
                "activity_type": "created",
            }
        ] + [
            {
                "timestamp": change.timestamp.isoformat(),
                "activity_user": change.activity_user.id,
                "activity_user_pretty": str(change.activity_user),
                "activity_type": "changed",
                "changes": [
                    {
                        "field_name_verbose": field_change.field.verbose_name,
                        "field_name": field_change.field.name,
                        "new_value": field_change.new_value_prettified,
                        "old_value": field_change.old_value_prettified,
                    }
                    for field_change in change.field_changes
                ],
            }
            for change in obj.history_changes
        ]

        return Response(ret)

    def get_serializer_class(self):
        def build_model_serializer(model_obj, serializer, field_names, *args, **kwargs):
            """
            Based on https://stackoverflow.com/questions/297383
            Create a serializer on the fly where the Meta class's model
            and fields are set dynamically
            """

            class DynamicModelSerializer(serializer):
                class Meta:
                    model = model_obj
                    fields = field_names

                def __init__(self, *args_init, **kwargs_init):
                    kwargs_copy = kwargs_init.copy()
                    # if "model" in kwargs_copy:
                    #     del kwargs_copy["model"]
                    super().__init__(*args_init, **kwargs_copy)

            return DynamicModelSerializer

        serializer = None
        field_names = []

        if self.action == "list":
            field_names = [
                f
                if getattr(getattr(self.model, f, None), "use_api", False)
                else f.replace("_formatted", "")
                for f in getattr(self.model, "_list_display_frozen", [])
                + getattr(self.model, "_list_display", [])
            ]
            serializer = build_model_serializer(
                self.model, self.serializer_list_class, field_names
            )

        elif self.action == "retrieve":
            field_names = (
                ["id"]
                + getattr(self.model, "_obj_specific_fields", [])
                + getattr(self.model, "_obj_unmodifiable_fields", [])
            )
            serializer = build_model_serializer(
                self.model, self.serializer_item_class, field_names
            )

        else:
            serializer = build_model_serializer(
                self.model, self.serializer_class, field_names
            )

        return serializer
