from django.contrib.auth import get_user_model
from import_export.fields import Field

from ..shared.export import CollectionExportMixin
from .models import Plasmid


class PlasmidExportResource(CollectionExportMixin):
    """Defines a custom export resource class for Plasmid"""

    additional_parent_vector_info = Field(
        attribute="old_parent_vector", column_name="additional_parent_vector_info"
    )

    class Meta:
        model = Plasmid
        fields = (
            "id",
            "name",
            "other_name",
            "parent_vector",
            "additional_parent_vector_info",
            "selection",
            "us_e",
            "construction_feature",
            "received_from",
            "note",
            "reference",
            "storage_type",
            "map",
            "created_date_time",
            f"created_by__{get_user_model().USERNAME_FIELD}",
            "locations",
        )
        export_order = fields
