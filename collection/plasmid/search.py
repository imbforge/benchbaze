from ..shared.admin import (
    FieldCreated,
    FieldFormZProject,
    FieldLastChanged,
    FieldSequenceFeature,
    FieldUse,
)
from ..shared.search import CollectionQLSchema


class PlasmidQLSchema(CollectionQLSchema):
    """DjangoQL schema for Plasmid collection model"""

    def __init__(self, model):
        self.fields = [
            "id",
            "name",
            "other_name",
            "parent_vector",
            "selection",
            FieldUse(),
            "construction_feature",
            "received_from",
            "note",
            "reference",
            "storage_type",
            "created_by",
            FieldCreated(),
            FieldLastChanged(),
            FieldSequenceFeature(model=model),
            FieldFormZProject(),
            "locations",
        ]
        super().__init__(model)
