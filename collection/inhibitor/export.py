from ..shared.export import CollectionExportMixin
from .models import Inhibitor


class InhibitorExportResource(CollectionExportMixin):
    """Custom export resource class for Inhibitor"""

    class Meta:
        model = Inhibitor
        fields = (
            "id",
            "name",
            "other_names",
            "target",
            "received_from",
            "catalogue_number",
            "l_ocation",
            "ic50",
            "amount",
            "stock_solution",
            "description_comment",
            "info_sheet",
            "locations",
        )
        export_order = fields
