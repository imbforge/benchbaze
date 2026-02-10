from django.contrib.auth import get_user_model

from ..shared.export import CollectionExportMixin
from .models import VirusInsect, VirusMammalian

EXPORT_FIELDS = [
    "id",
    "name",
    "typ_e",
    "resistance",
    "us_e",
    "helper_plasmids",
    "helper_cellline",
    "construction",
    "note",
    "locations",
    "created_date_time",
    f"created_by__{get_user_model().USERNAME_FIELD}",
    "locations",
]


class VirusMammalianExportResource(CollectionExportMixin):
    class Meta:
        model = VirusMammalian
        fields = EXPORT_FIELDS.copy()
        export_order = fields


class VirusInsectExportResource(CollectionExportMixin):
    class Meta:
        model = VirusInsect
        fields = EXPORT_FIELDS.copy()
        fields.insert(fields.index("helper_plasmids"), "helper_ecolistrain")
        export_order = fields
