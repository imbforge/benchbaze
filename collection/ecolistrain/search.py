from ..shared.admin import (
    FieldCreated,
    FieldFormZProject,
    FieldLastChanged,
    FieldUse,
)
from ..shared.search import CollectionQLSchema


class EColiStrainQLSchema(CollectionQLSchema):
    """DjangoQL schema for EColiStrain collection model"""

    fields = [
        "id",
        "name",
        "resistance",
        "genotype",
        "supplier",
        FieldUse(),
        "purpose",
        "note",
        "created_by",
        FieldCreated(),
        FieldLastChanged(),
        FieldFormZProject(),
        "locations",
    ]
