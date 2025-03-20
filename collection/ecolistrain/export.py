from import_export import resources
from django.contrib.auth import get_user_model

from .models import EColiStrain


class EColiStrainExportResource(resources.ModelResource):
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
        )
        export_order = fields
