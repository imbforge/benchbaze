from django.contrib.auth import get_user_model
from import_export.fields import Field

from ..shared.export import CollectionExportMixin
from .models import SiRna


class SiRnaExportResource(CollectionExportMixin):
    """Defines a custom export resource class for SiRna"""

    species_name = Field()

    def dehydrate_species_name(self, si_rna):
        return str(si_rna.species)

    class Meta:
        model = SiRna
        fields = (
            "id",
            "name",
            "sequence",
            "sequence_antisense",
            "supplier",
            "supplier_part_no",
            "supplier_si_rna_id",
            "species_name",
            "target_genes",
            "locus_ids",
            "description_comment",
            "info_sheet",
            "orders",
            "created_date_time",
            f"created_by__{get_user_model().USERNAME_FIELD}",
            "locations",
        )
        export_order = fields
