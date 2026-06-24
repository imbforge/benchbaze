from ..shared.admin import (
    FieldCreated,
    FieldFormZProject,
    FieldFormZSpecies,
    FieldLastChanged,
    FieldUse,
)
from ..shared.search import CollectionQLSchema


class OtherBacteriumStrainQLSchema(CollectionQLSchema):
    """DjangoQL schema for OtherBacteriumStrain collection model"""

    fields = [
        "id",
        "name",
        FieldFormZSpecies("species", "show_for_other_bacterium_strain"),
        "genotype",
        "background",
        "resistance",
        "supplier",
        FieldUse(),
        "note",
        "created_by",
        FieldCreated(),
        FieldLastChanged(),
        FieldFormZProject(),
        "locations",
    ]
