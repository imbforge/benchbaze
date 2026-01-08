from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import EmptyPage, Paginator
from django.core.validators import validate_slug
from django.db.models import F, Q
from django.db.models.expressions import Window
from django.db.models.functions import DenseRank
from django.utils.text import capfirst
from djangoql.queryset import apply_search as apply_djangoql_search
from djangoql.serializers import SuggestionsAPISerializer
from rest_framework import mixins, permissions, renderers, status, viewsets
from rest_framework.decorators import action as rest_action
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.viewsets import GenericViewSet

from .models import LayoutFrontend
from .paginators import StandardResultsSetPagination
from .serializers import (
    ItemSerializer,
    LayoutFrontendSerializer,
    ListSerializer,
    LogEntrySerializer,
    NavigationSerializer,
    UserSerializer,
    build_model_serializer,
)

User = get_user_model()


DOCS_URL = getattr(settings, "DOCS_URL", "")
IMPRESSUM_URL = getattr(settings, "IMPRESSUM_URL", "")
DATA_PROTECTION_URL = getattr(settings, "DATA_PROTECTION_URL", "")


def get_query_schema(model):
    return getattr(
        import_module(f"{model._meta.label_lower}.search"),
        f"{model.__name__}QLSchema",
        None,
    )


class PassthroughRenderer(renderers.BaseRenderer):
    """
    Return data from a viewset action as is returned by the viewset,
    without serialization

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

    def list(self, request, *args, **kwargs):
        """The same as super but accepts a request too"""

        filters = {}
        user_ids = request.GET.getlist("user_id", [])
        if user_ids:
            validate_slug("".join(user_ids))
            filters["id__in"] = user_ids
        queryset = self.get_queryset().filter(**filters)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @rest_action(methods=["get"], detail=False)
    def logged(self, request):
        """Show the logged user"""
        serializer = self.serializer_class(request.user)
        return Response(serializer.data)

    @rest_action(methods=["get"], detail=False, url_path="logged/recent_events")
    def recent_events(self, request):
        """Get the latest num_latest_events events for each
        available content_type_id for the logged user"""

        num_latest_events = 5
        filters = {}
        user_ids = request.GET.getlist("user_id", [])
        if user_ids:
            validate_slug("".join(user_ids))
            filters["user_id__in"] = user_ids
        content_type_ids = request.GET.getlist("content_type_id", [])
        if content_type_ids:
            validate_slug("".join(content_type_ids))
            filters["content_type_id__in"] = content_type_ids

        # https://stackoverflow.com/questions/74705929
        queryset = (
            LogEntry.objects.filter(**filters)
            .annotate(
                rank=Window(
                    expression=DenseRank(),
                    partition_by=[
                        F("content_type_id"),
                    ],
                    order_by=F("action_time").desc(),
                ),
            )
            .filter(rank__lte=num_latest_events)
            .order_by(
                "content_type__app_label",
                "content_type__model",
                "object_id",
                "-action_time",
            )
        )

        data = LogEntrySerializer(queryset, many=True).data
        return Response(data)


class LayoutFrontendViewSet(viewsets.ModelViewSet):
    """Show frontend layout information"""

    queryset = LayoutFrontend.objects.all()
    serializer_class = LayoutFrontendSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None


class NavigationBaseViewSet(GenericViewSet):
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

        # Disabled this because it was raising an error for the advanced_search_introspection
        # view, it

        # assert lookup_url_kwarg in self.kwargs, (
        #     "Expected view %s to be called with a URL keyword argument "
        #     'named "%s". Fix your URL conf, or set the `.lookup_field` '
        #     "attribute on the view correctly."
        #     % (self.__class__.__name__, lookup_url_kwarg)
        # )

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

        Also sort result by app_label and model, it is nicer here

        """

        queryset = queryset.order_by("app_label", "model")
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
                    ct.model_verbose_name = (
                        capfirst(model._meta.verbose_name)
                        if isinstance(model._show_in_frontend, bool)
                        else getattr(
                            model, "_frontend_verbose_name", model._meta.verbose_name
                        )
                    )
                    ct.model_verbose_plural = (
                        capfirst(model._meta.verbose_name_plural)
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

    def get_related_model(self, kwargs):
        return ContentType.objects.get(**kwargs).model_class()


class NavigationListViewSet(mixins.ListModelMixin, NavigationBaseViewSet):
    def list(self, request, **kwargs):
        """The same as super but accepts a request too"""

        queryset = self.filter_queryset(self.get_queryset(), request)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class NavigationViewSet(NavigationBaseViewSet):
    """Show frontend layout information"""

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
            field_info = {}
            field_name_stripped = field_name
            use_api = False

            # For (admin)formatted field names, remove _formatted placeholder suffix
            formatted = field_name if "_formatted" in field_name else False
            if formatted:
                use_api = getattr(getattr(model, field_name, None), "use_api", False)
                field_name_stripped = field_name_stripped.replace("_formatted", "")
            try:
                # Get field details
                field = model._meta.get_field(field_name_stripped)
                # If field is formatted, get field_type from
                # formatting function
                field_type = (
                    getattr(getattr(model, field_name, None), "field_type", None)
                    if formatted
                    else field.get_internal_type()
                )
                # Add related model
                if related_model := getattr(field, "related_model", None):
                    field_info["related_model"] = {
                        "app_label": getattr(related_model._meta, "app_label", ""),
                        "model_name": getattr(related_model._meta, "model_name", ""),
                    }
                else:
                    field_name = field.name if not use_api else field_name
                field_info.update(
                    {
                        "name": field_name,
                        "verbose_name": capfirst(field.verbose_name),
                        "type": field_type,
                    }
                )
                ret.append(field_info)
            except Exception:
                continue
        return ret

    @rest_action(detail=False, methods=["get"])
    def listview_fields(self, request, **kwargs):
        """
        Shows the fields to display in the list view of
        a model
        """

        model = self.get_related_model(kwargs)
        fields = self._get_field_details(
            model,
            getattr(model, "_list_display_frozen", [])
            + getattr(model, "_list_display", []),
        )

        list_display_links = getattr(model, "_list_display_links", list())
        list_display_frozen = getattr(model, "_list_display_frozen", list())
        search_fields = getattr(model, "_search_fields", list())
        for field in fields:
            field["link"] = field["name"] in list_display_links
            field["frozen"] = field["name"] in list_display_frozen
            field["search"] = field["name"] in search_fields

        return Response(fields)

    @rest_action(detail=False, methods=["get"])
    def addview_fields(self, request, **kwargs):
        """
        Shows the fields to display in the add view of
        a model
        """

        model = self.get_related_model(kwargs)
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

    @rest_action(detail=False, methods=["get"])
    def changeview_fields(self, request, **kwargs):
        """
        Shows the fields to display in the change view of
        a model
        """

        model = self.get_related_model(kwargs)
        fieldsets = getattr(model, "_change_view_fieldsets", list())
        return Response(
            [
                {
                    "name": fieldset[0],
                    "fields": self._get_field_details(model, fieldset[1]["fields"]),
                }
                for fieldset in fieldsets
            ]
        )

    @rest_action(detail=False, methods=["get"])
    def action_list(self, request, **kwargs):
        """Shows the actions for a model"""

        model = self.get_related_model(kwargs)
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

    @rest_action(methods=["get"], detail=False, renderer_classes=(PassthroughRenderer,))
    def action(self, request, **kwargs):
        """Run an ction for a model"""

        model = self.get_related_model(kwargs)
        action_name = request.GET.getlist("name", [""])[0]
        if action_name:
            validate_slug(action_name)
        item_ids = request.GET.getlist("id", [])
        if item_ids:
            validate_slug("".join(item_ids))
        action = next((a for a in model._actions if a.__name__ == action_name), None)
        if len(item_ids) == 1 and item_ids[0] == "0":
            queryset = model.objects.all()
            if request and (search_params := request.GET.getlist("search", [""])[0]):
                if schema := get_query_schema(model):
                    queryset = apply_djangoql_search(
                        queryset, search_params, schema=schema
                    )
        else:
            queryset = model.objects.filter(id__in=item_ids)

        return action(model, request, queryset)

    @rest_action(detail=False, methods=["get"])
    def advanced_search_introspection(self, request, **kwargs):
        model = self.get_related_model(kwargs)
        suggestions_url = reverse(
            "navigation-advanced-search-suggestions",
            args=[kwargs.get("app_label"), kwargs.get("model")],
        )
        serializer = SuggestionsAPISerializer(suggestions_url)
        schema = get_query_schema(model)
        response = serializer.serialize(schema(model))
        return Response(response)

    @rest_action(detail=False, methods=["get"])
    def advanced_search_suggestions(self, request, **kwargs):
        """djangoql.view.SuggestionsAPIView repurposed to work with
        Django REST Framework"""

        def get_field(field_name, schema):
            if not schema:
                raise ValueError("DjangoQL schema is undefined")
            if not field_name:
                raise ValueError('"field" parameter is required')
            parts = field_name.split(".")
            field_name = parts.pop()
            if parts:
                model_name = parts[-1]
                app_label = ".".join(parts[:-1])
                if not app_label:
                    app_label = schema.current_model._meta.app_label
                model_label = ".".join([app_label, model_name])
            else:
                model_label = schema.model_label(schema.current_model)
            schema_model = schema.models.get(model_label)
            if not schema_model:
                raise ValueError("Unknown model: %s" % model_label)
            field_instance = schema_model.get(field_name)
            if not field_instance:
                raise ValueError("Unknown field: %s" % field_name)
            return field_instance

        def get_suggestions(field, search):
            if not field.suggest_options:
                raise ValueError(
                    "%s.%s doesn't support suggestions"
                    % (
                        field.model._meta.object_name,
                        field.name,
                    )
                )
            return field.get_options(search)

        model = self.get_related_model(kwargs)
        schema = get_query_schema(model)

        search = request.GET.get("search", "")

        try:
            field_name = request.GET.get("field", "")
            field = get_field(field_name, schema(model))
            page_number = int(request.GET.get("page", 1))
            if page_number < 1:
                raise ValueError("page must be an integer starting from 1")
            suggestions = get_suggestions(field=field, search=search)
        except ValueError as e:
            error = str(e) or e.__class__.__name__
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        paginator = Paginator(suggestions, getattr(self, "suggestions_per_page", 100))
        try:
            page = paginator.page(page_number)
        except EmptyPage:
            items = []
            has_next = False
        else:
            items = list(page.object_list)
            has_next = page.has_next()

        response = {
            "items": items,
            "page": page_number,
            "has_next": has_next,
        }
        return Response(response)


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
        self.queryset = self.model.objects.all().order_by("-id")
        return super().get_queryset()

    def order_queryset(self, queryset, request=None, **kwargs):
        ordering = request.GET.getlist("ordering")
        if ordering:
            validate_slug("".join(ordering))
            return queryset.order_by(*ordering)
        return queryset

    def filter_queryset(self, queryset, request=None, **kwargs):
        queryset = super().filter_queryset(queryset)
        view_name = kwargs.get("view_name")

        if (
            request
            and view_name == "list"
            and request.GET.get("q") == ""
            and (search_params := request.GET.getlist("search", [""])[0])
        ):
            if schema := get_query_schema(self.model):
                queryset = apply_djangoql_search(queryset, search_params, schema=schema)

        elif (
            request
            and view_name in ["autocomplete", "list"]
            and (search_value := request.GET.getlist("search", [""])[0])
        ):
            q_filter_ = Q()
            for field_name in getattr(queryset.model, "_search_fields", []):
                q_filter_ |= Q(**{f"{field_name}__icontains": search_value})
            queryset = queryset.filter(q_filter_)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(
            self.get_queryset(), request=request, view_name="list"
        )

        queryset = self.order_queryset(queryset, request)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @rest_action(detail=False, methods=["get"])
    def autocomplete(self, request, pk=None, **kwargs):
        """
        Autocompletion view
        """
        queryset = self.filter_queryset(
            self.get_queryset(), request=request, view_name="autocomplete"
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @rest_action(detail=True, methods=["get"])
    def readonly_fields(self, request, pk=None, **kwargs):
        """
        Returns which fields are readonly for the instance of
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
        field_names = []
        serializer_class = None

        if self.action == "list":
            field_names = [
                f
                if getattr(getattr(self.model, f, None), "use_api", False)
                else f.replace("_formatted", "")
                for f in getattr(self.model, "_list_display_frozen", [])
                + getattr(self.model, "_list_display", [])
            ]
            serializer_class = self.serializer_list_class
        elif self.action == "retrieve":
            field_names = (
                ["id"]
                + getattr(self.model, "_obj_specific_fields", [])
                + getattr(self.model, "_obj_unmodifiable_fields", [])
            )
            serializer_class = self.serializer_item_class
        elif self.action == "autocomplete":
            field_names = ["id"]
            serializer_class = self.serializer_list_class
        else:
            serializer_class = self.serializer_class

        return build_model_serializer(self.model, serializer_class, field_names)
