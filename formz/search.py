from djangoql.schema import DjangoQLSchema

from common.search import SearchFieldWithOptions
from formz.models import NucleicAcidPurity, NucleicAcidRisk


class SequenceFeatureSearchFieldNucleicAcidPurity(SearchFieldWithOptions):
    """Search field for the english name of a nucleic acid purity object"""

    model = NucleicAcidPurity
    name = "nucleic_acid_purity"
    model_fieldname = "english_name"

    def get_lookup_name(self):
        return "nuc_acid_purity__english_name"


class SequenceFeatureSearchFieldNucleicAcidRisk(SearchFieldWithOptions):
    """Search field for the english name of a nucleic acid risk object"""

    model = NucleicAcidRisk
    name = "nucleic_acid_risk"
    model_fieldname = "english_name"

    def get_lookup_name(self):
        return "nuc_acid_risk__english_name"


class SequenceFeatureQLSchema(DjangoQLSchema):
    """DjangoQL schema for Plasmid collection model"""

    fields = [
        "id",
        "name",
        "donor_organism",
        SequenceFeatureSearchFieldNucleicAcidPurity(),
        SequenceFeatureSearchFieldNucleicAcidRisk(),
        "zkbs_oncogene",
        "common_feature",
    ]

    def get_fields(self, model):
        if model == self.current_model:
            return self.fields

        if model.__name__ == "Species":
            return ["common_name", "latin_name"]

        if model.__name__ == "ZkbsOncogene":
            return ["name", "synonym", "risk_potential", "species"]

        return super().get_fields(model)
