from djangoql.schema import IntField

from collection.models import CellLine, EColiStrain

from ..shared.admin import (
    FieldCreated,
    FieldFormZProject,
    FieldLastChanged,
    FieldType,
    FieldUse,
)
from ..shared.search import CollectionQLSchema

# Common fields


class FieldHelperPlasmidM2M(IntField):
    """Search field for the id of helper plasmids linked to a virus"""

    name = "helper_plasmid_id"

    def get_lookup_name(self):
        return "plasmids__id"


# Virus Mammalian


class VirusSearchFieldHelperCellLine(IntField):
    model = CellLine
    name = "helper_cellline_id"
    suggest_options = False

    def get_lookup_name(self):
        return "helper_cellline__id"


class VirusMammalianQLSchema(CollectionQLSchema):
    """DjangoQL schema for VirusMammalian collection model"""

    def __init__(self, model):
        self.fields = [
            "id",
            "name",
            FieldType(model=model),
            "resistance",
            FieldUse(),
            FieldHelperPlasmidM2M(),
            VirusSearchFieldHelperCellLine(),
            "construction",
            "note",
            "created_by",
            FieldCreated(),
            FieldLastChanged(),
            FieldFormZProject(),
            "locations",
        ]
        super().__init__(model)


# Virus Insect


class VirusInsectSearchFieldHelperEcoliStrain(IntField):
    """Search field for the id of the helper EColiStrain of a VirusInsect"""

    model = EColiStrain
    name = "helper_ecolistrain_id"
    suggest_options = False

    def get_lookup_name(self):
        return "helper_ecolistrain__id"


class VirusInsectQLSchema(CollectionQLSchema):
    """DjangoQL schema for VirusInsect collection model"""

    def __init__(self, model):
        self.fields = [
            "id",
            "name",
            FieldType(model=model),
            "resistance",
            FieldUse(),
            FieldHelperPlasmidM2M(),
            VirusInsectSearchFieldHelperEcoliStrain(),
            VirusSearchFieldHelperCellLine(),
            "construction",
            "note",
            "created_by",
            FieldCreated(),
            FieldLastChanged(),
            FieldFormZProject(),
            "locations",
        ]
        super().__init__(model)
