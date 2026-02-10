from ..shared.export import CollectionExportMixin
from .models import Antibody


class AntibodyExportResource(CollectionExportMixin):
    """Defines a custom export resource class for Antibody"""

    class Meta:
        model = Antibody
        fields = (
            "id",
            "name",
            "species_isotype",
            "clone",
            "received_from",
            "catalogue_number",
            "l_ocation",
            "a_pplication",
            "description_comment",
            "info_sheet",
            "availability",
            "locations",
        )
        export_order = fields
