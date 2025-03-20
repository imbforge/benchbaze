from import_export import resources
from django.contrib.auth import get_user_model

from .models import Oligo


class OligoExportResource(resources.ModelResource):
    """Defines a custom export resource class for Oligo"""

    class Meta:
        model = Oligo
        fields = (
            "id",
            "name",
            "sequence",
            "us_e",
            "gene",
            "restriction_site",
            "description",
            "comment",
            "created_date_time",
            f"created_by__{get_user_model().USERNAME_FIELD}",
        )
        export_order = fields
