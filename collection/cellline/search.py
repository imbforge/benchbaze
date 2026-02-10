from djangoql.schema import IntField, StrField

from formz.models import Project as FormZProject

from ..shared.admin import (
    FieldCreated,
    FieldEpisomalPlasmidM2M,
    FieldFormZProject,
    FieldIntegratedPlasmidM2M,
    FieldLastChanged,
)
from ..shared.search import CollectionQLSchema


class CellLineSearchFieldParentalCellLineId(IntField):
    """Search field for the id of the parental cell line of a cell line"""

    name = "parental_line_id"

    def get_lookup_name(self):
        return "parental_line__id"


class CellLineSearchFieldEpisomalPlasmidFormZProject(StrField):
    """Search field for the short title of FormZ projects linked
    to episomal plasmids in a cell line"""

    name = "episomal_plasmids_formz_projects_title"
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list("short_title", flat=True)

    def get_lookup_name(self):
        return "celllineepisomalplasmid__formz_projects__short_title"


class CellLineSearchFieldMammalianVirusId(IntField):
    """Search field for the short title of FormZ projects linked
    to episomal plasmids in a cell line"""

    name = "virus_transient_mammalian_id"

    def get_lookup_name(self):
        return "viruses_transient__virus_mammalian__id"

    def get_lookup(self, path, operator, value):
        return super().get_lookup(path, operator, value)


class CellLineSearchFieldInsectVirusId(IntField):
    """Search field for the short title of FormZ projects linked
    to episomal plasmids in a cell line"""

    name = "virus_transient_insect_id"

    def get_lookup_name(self):
        return "viruses_transient__virus_insect__id"


class CellLineQLSchema(CollectionQLSchema):
    """GraphQL schema for CellLine collection model"""

    fields = [
        "id",
        "name",
        "box_name",
        "alternative_name",
        CellLineSearchFieldParentalCellLineId(),
        "organism",
        "cell_type_tissue",
        "culture_type",
        "growth_condition",
        "freezing_medium",
        "received_from",
        FieldIntegratedPlasmidM2M(),
        FieldEpisomalPlasmidM2M(),
        "description_comment",
        "created_by",
        FieldCreated(),
        FieldLastChanged(),
        FieldFormZProject(),
        CellLineSearchFieldEpisomalPlasmidFormZProject(),
        CellLineSearchFieldMammalianVirusId(),
        CellLineSearchFieldInsectVirusId(),
        "locations",
    ]
