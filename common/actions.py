from django.contrib.auth import get_user_model
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
            except:
                headers.append(force_str(field.column_name))
        return headers


def create_export_resource(this):
    """Export action"""

    # Depending on whether the action is used from the admin or
    # from the api, 'this' can either be a modeladmin or a model
    # so I check this here and always get the model
    model = getattr(this, "model", this)
    field_names = getattr(model, "_export_field_names", [])
    custom_fields = getattr(
        model,
        "_export_custom_fields",
        dict(fields=dict(), dehydrate_methods=dict()),
    )

    # If created_by in list of export fields, add it as a custom
    # field that includes the user's full name and USERNAME_FIELD
    if "created_by" in field_names:
        custom_fields["dehydrate_methods"]["created_by"] = lambda obj: (
            f"{obj.created_by.first_name} {obj.created_by.last_name}, "
            f"{getattr(obj.created_by, get_user_model().USERNAME_FIELD)}"
        )

    # If locations in list of export fields, add it as a custom field
    # that includes a nicely formatted list of locations
    if "locations" in field_names:
        custom_fields["dehydrate_methods"]["locations"] = lambda obj: "; ".join(
            str(location.minimal_str)
            for location in obj.locations.all().order_by("location__level")
        )
        custom_fields["fields"]["locations"] = Field(column_name="Locations")

    # Create export resource on the fly
    export_resource = modelresource_factory(
        model=model,
        resource_class=OwnExportResource,
        meta_options={
            "fields": field_names,
            "export_order": field_names,
        },
        custom_fields=custom_fields["fields"] if custom_fields else None,
        dehydrate_methods=custom_fields["dehydrate_methods"] if custom_fields else None,
    )

    return export_resource


def export_xlsx_action(this, request, queryset):
    """Create export resource on the fly and export as XLSX"""
    export_resource = create_export_resource(this)
    export_data = export_resource().export(queryset)
    return export_objects_xlsx(queryset, export_data)


export_xlsx_action.short_description = "Export selected as XLSX"


def export_tsv_action(this, request, queryset):
    """Create export resource on the fly and export as TSV"""
    export_resource = create_export_resource(this)
    export_data = export_resource().export(queryset)
    return export_objects_tsv(queryset, export_data)


export_tsv_action.short_description = "Export selected as TSV"
