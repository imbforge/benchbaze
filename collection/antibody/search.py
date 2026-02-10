from ..shared.admin import (
    FieldApplication,
)
from ..shared.search import CollectionQLSchema


class AntibodyQLSchema(CollectionQLSchema):
    """DjangoQL schema for Antibody collection model"""

    fields = [
        "id",
        "name",
        "species_isotype",
        "clone",
        "received_from",
        "catalogue_number",
        "info_sheet",
        FieldApplication(),
        "description_comment",
        "info_sheet",
        "availability",
        "locations",
    ]
