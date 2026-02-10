from djangoql.schema import StrField

from formz.models import Project as FormZProject

from ..shared.admin import (
    FieldCassettePlasmidM2M,
    FieldCreated,
    FieldEpisomalPlasmidM2M,
    FieldFormZProject,
    FieldIntegratedPlasmidM2M,
    FieldLastChanged,
    FieldParent1,
    FieldParent2,
)
from ..shared.search import CollectionQLSchema


class ScPombeStrainFieldEpisomalPlasmidFormZProject(StrField):
    """Search field for the short title of FormZ projects linked
    to episomal plasmids in a ScPombeStrain"""

    name = "episomal_plasmids_formz_projects_title"
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list("short_title", flat=True)

    def get_lookup_name(self):
        return "scpombestrainepisomalplasmid__formz_projects__short_title"


class ScPombeStrainQLSchema(CollectionQLSchema):
    """GraphQL schema for ScPombeStrain collection model"""

    fields = [
        "id",
        "box_number",
        FieldParent1(),
        FieldParent2(),
        "parental_strain",
        "mating_type",
        "auxotrophic_marker",
        "name",
        FieldIntegratedPlasmidM2M(),
        FieldCassettePlasmidM2M(),
        FieldEpisomalPlasmidM2M(),
        "phenotype",
        "received_from",
        "comment",
        "created_by",
        FieldCreated(),
        FieldLastChanged(),
        FieldFormZProject(),
        ScPombeStrainFieldEpisomalPlasmidFormZProject(),
        "locations",
    ]
