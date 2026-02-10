from django.contrib.auth import get_user_model

from ..shared.export import CollectionExportMixin
from .models import EColiStrain


class EColiStrainExportResource(CollectionExportMixin):
    """Defines a custom export resource class for EColiStrain"""

    class Meta:
        model = EColiStrain
        fields = (
            "id",
            "name",
            "resistance",
            "genotype",
            "supplier",
            "us_e",
            "purpose",
            "note",
            "created_date_time",
            f"created_by__{get_user_model().USERNAME_FIELD}",
            "locations",
        )
        export_order = fields
