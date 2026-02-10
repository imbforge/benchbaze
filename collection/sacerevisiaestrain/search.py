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
    FieldUse,
)
from ..shared.search import CollectionQLSchema


class SaCerevisiaeStrainSearchFieldEpisomalPlasmidFormZProject(StrField):
    """Search field for the short title of FormZ projects linked
    to episomal plasmids in a SaCerevisiaeStrain"""

    name = "episomal_plasmids_formz_projects_title"
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list("short_title", flat=True)

    def get_lookup_name(self):
        return "sacerevisiaestrainepisomalplasmid__formz_projects__short_title"


class SaCerevisiaeStrainQLSchema(CollectionQLSchema):
    """GraphQL schema for SaCerevisiaeStrain collection model"""

    fields = [
        "id",
        "name",
        "relevant_genotype",
        "mating_type",
        "chromosomal_genotype",
        FieldParent1(),
        FieldParent2(),
        "parental_strain",
        "construction",
        "modification",
        FieldIntegratedPlasmidM2M(),
        FieldCassettePlasmidM2M(),
        FieldEpisomalPlasmidM2M(),
        "plasmids",
        "selection",
        "phenotype",
        "background",
        "received_from",
        FieldUse(),
        "note",
        "reference",
        "created_by",
        FieldCreated(),
        FieldLastChanged(),
        FieldFormZProject(),
        SaCerevisiaeStrainSearchFieldEpisomalPlasmidFormZProject(),
        "locations",
    ]
