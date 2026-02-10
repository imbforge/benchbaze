from django.contrib.auth import get_user_model

from ..shared.export import CollectionExportMixin
from .models import Oligo


class OligoExportResource(CollectionExportMixin):
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
            "locations",
        )
        export_order = fields
