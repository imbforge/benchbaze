from django.contrib.auth import get_user_model
from import_export.fields import Field
from ..shared.export import CollectionExportMixin

from .models import CellLine


class CellLineExportResource(CollectionExportMixin):
    """Defines a custom export resource class for CellLine"""

    organism_name = Field()

    def dehydrate_organism_name(self, strain):
        return str(strain.organism)

    class Meta:
        model = CellLine
        fields = (
            "id",
            "name",
            "box_name",
            "alternative_name",
            "parental_line",
            "organism_name",
            "cell_type_tissue",
            "culture_type",
            "growth_condition",
            "freezing_medium",
            "received_from",
            "description_comment",
            "integrated_plasmids",
            "created_date_time",
            f"created_by__{get_user_model().USERNAME_FIELD}",
            "locations",
        )
        export_order = fields
