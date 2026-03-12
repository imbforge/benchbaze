from copy import deepcopy

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.utils.encoding import force_str
from django.utils.text import capfirst
from import_export.fields import Field
from import_export.resources import ModelResource, modelresource_factory

from common.export import export_objects_tsv, export_objects_xlsx


class OwnExportResource(ModelResource):
    def get_export_headers(self, selected_fields=None):
        """Use a field verbose name as the column header"""

        model = self._meta.model
        export_fields = self.get_export_fields(selected_fields)
        headers = []
        for field in export_fields:
            try:
                headers.append(
                    capfirst(model._meta.get_field(field.column_name).verbose_name)
                )
            except FieldDoesNotExist:
                headers.append(force_str(field.column_name))
        return headers


def _get_export_model_and_field_names(
    source,
    export_field_names="_export_field_names",
):
    """Resolve source to model and export field names."""

    model = getattr(source, "model", source)
    if isinstance(export_field_names, str):
        export_field_names = getattr(model, export_field_names, ())
    field_names = tuple(export_field_names or ())
    return model, field_names


def _dehydrate_created_by(obj):
    """Style created_by field to include user's full name and USERNAME_FIELD"""
    user = getattr(obj, "created_by", None)
    if not user:
        return ""

    full_name = " ".join(part for part in [user.first_name, user.last_name] if part)
    username_field = get_user_model().USERNAME_FIELD
    username = getattr(user, username_field, "")
    return f"{full_name}, {username}" if full_name else str(username)


def _dehydrate_locations(obj):
    """Style locations field to include a nicely formatted list of locations"""
    prefetched_locations = getattr(obj, "_prefetched_objects_cache", {}).get(
        "locations"
    )
    if prefetched_locations is not None:
        ordered_locations = sorted(
            prefetched_locations,
            key=lambda location: getattr(location.location, "level", 0),
        )
    else:
        ordered_locations = obj.locations.select_related("location").order_by(
            "location__level"
        )

    return "; ".join(str(location.minimal_str) for location in ordered_locations)


def optimize_export_queryset(
    source,
    queryset,
    export_field_names="_export_field_names",
):
    """Apply query optimizations for fields that need related objects."""

    _, field_names = _get_export_model_and_field_names(source, export_field_names)

    if "locations" in field_names:
        queryset = queryset.prefetch_related("locations__location")

    return queryset


def create_export_resource(
    source,
    export_field_names="_export_field_names",
    export_custom_fields="_export_custom_fields",
):
    """Create the export resource for a model on the fly based on export
    field names defined in the model.
    export_field_names and export_custom_fields are strings that represent
    attributes on the model that define the export field names and any
    custom fields
    """

    # Depending on whether the action is used from the admin or
    # from the api, 'source' can either be a modeladmin or a model
    # so I check source here and always get the model
    model, field_names = _get_export_model_and_field_names(source, export_field_names)

    # Work on copies so we never mutate model-level configuration.
    if isinstance(export_custom_fields, str):
        export_custom_fields = getattr(model, export_custom_fields, None) or {}
    else:
        export_custom_fields = export_custom_fields or {}
    custom_fields = deepcopy(export_custom_fields.get("fields", {}))
    dehydrate_methods = deepcopy(export_custom_fields.get("dehydrate_methods", {}))

    # If created_by in list of export fields, add it as a custom
    # field that includes the user's full name and USERNAME_FIELD
    if "created_by" in field_names:
        dehydrate_methods.setdefault("created_by", _dehydrate_created_by)

    # If locations in list of export fields, add it as a custom field
    # that includes a nicely formatted list of locations
    if "locations" in field_names:
        dehydrate_methods.setdefault("locations", _dehydrate_locations)
        custom_fields.setdefault("locations", Field(column_name="Locations"))

    # Create export resource on the fly
    export_resource = modelresource_factory(
        model=model,
        resource_class=OwnExportResource,
        meta_options={
            "fields": field_names,
            "export_order": field_names,
        },
        custom_fields=custom_fields or None,
        dehydrate_methods=dehydrate_methods or None,
    )

    return export_resource


def export_action(
    source,
    queryset,
    file_format,
    export_field_names="_export_field_names",
    export_custom_fields="_export_custom_fields",
):
    """Create export resource on the fly and export in the requested format."""
    queryset = optimize_export_queryset(source, queryset, export_field_names)
    export_resource = create_export_resource(
        source, export_field_names, export_custom_fields
    )
    export_data = export_resource().export(queryset)

    if file_format == "xlsx":
        return export_objects_xlsx(queryset, export_data)
    if file_format == "tsv":
        return export_objects_tsv(queryset, export_data)
    raise ValueError(f"Unsupported export format: {file_format}")


def export_action_xlsx(source, request, queryset):
    """Create export resource on the fly and export as XLSX"""
    return export_action(source, queryset, "xlsx")


export_action_xlsx.short_description = "Export selected as XLSX"


def export_action_tsv(source, request, queryset):
    """Create export resource on the fly and export as TSV"""
    return export_action(source, queryset, "tsv")


export_action_tsv.short_description = "Export selected as TSV"
