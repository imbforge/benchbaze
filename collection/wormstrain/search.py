from django.db.models import Q
from djangoql.schema import IntField, RelationField, StrField

from ..shared.admin import (
    FieldCreated,
    FieldFormZProject,
    FieldLastChanged,
    FieldParent1,
    FieldParent2,
    FieldSequenceFeature,
    FieldType,
    FieldUse,
)
from ..shared.search import CollectionQLSchema
from .models import WormStrainAllele


class WormStrainAlleleField(RelationField):
    name = "allele"
    related_model = WormStrainAllele

    def __init__(self, model):
        super().__init__(model, self.name, self.related_model)

    def get_lookup_name(self):
        return "alleles"


class WormStrainSearchFieldAlleleId(IntField):
    name = "id"

    def get_lookup(self, path, operator, value):
        """Override parent's method to replace 'allele' with 'alleles' in path"""

        path = [p if p != "allele" else "alleles" for p in path]
        return super().get_lookup(path, operator, value)


class WormStrainSearchFieldAlleleName(StrField):
    name = "name"
    suggest_options = True

    def get_options(self, search):
        """Suggest allele names based on the search input, looking in both
        transgene and mutation fields of WormStrainAllele"""

        if len(search) < 3:
            return ["Type 3 or more characters to see suggestions"]

        qs = self.model.objects.filter(
            Q(transgene__icontains=search) | Q(mutation__icontains=search)
        )
        return [a.name for a in qs]

    def get_lookup(self, path, operator, value):
        """Override parent's method to search for the input value in both
        transgene and mutation fields of WormStrainAllele"""

        op, invert = self.get_operator(operator)
        value = self.get_lookup_value(value)

        q = Q(**{f"alleles__transgene{op}": value}) | Q(
            **{f"alleles__mutation{op}": value}
        )

        return ~q if invert else q


class WormStrainQLSchema(CollectionQLSchema):
    """DjangoQL schema for WormStrain collection model"""

    def __init__(self, model):
        self.fields = [
            "id",
            "name",
            "chromosomal_genotype",
            FieldParent1(),
            FieldParent2(),
            "construction",
            "outcrossed",
            "growth_conditions",
            "organism",
            "selection",
            "phenotype",
            "received_from",
            FieldUse(),
            "note",
            "reference",
            "at_cgc",
            "location_freezer1",
            "location_freezer2",
            "location_backup",
            WormStrainAlleleField(model=model),
            "created_by",
            FieldCreated(),
            FieldLastChanged(),
            FieldFormZProject(),
            "locations",
        ]
        super().__init__(model)

    def get_fields(self, model):
        if model.__name__ == "WormStrainAllele":
            return [
                WormStrainSearchFieldAlleleId(model=model),
                WormStrainSearchFieldAlleleName(model=model),
            ]

        return super().get_fields(model)


class WormStrainAlleleSearchFieldSequenceFeature(FieldSequenceFeature):
    model = WormStrainAllele


class WormStrainAlleleFieldTransgenePlasmids(IntField):
    name = "transgene_plasmids_id"

    def get_lookup_name(self):
        return "transgene_plasmids__id"


class WormStrainAlleleFieldMadeWithPlasmids(IntField):
    name = "made_with_plasmids_id"

    def get_lookup_name(self):
        return "made_with_plasmids__id"


class WormStrainAlleleQLSchema(CollectionQLSchema):
    """DjangoQL schema for WormStrainAllele model"""

    def __init__(self, model):
        self.fields = [
            "id",
            "lab_identifier",
            FieldType(model=model),
            "transgene",
            "transgene_position",
            WormStrainAlleleFieldTransgenePlasmids(),
            "mutation",
            "mutation_type",
            "mutation_position",
            "reference_strain",
            "made_by_method",
            "made_by_person",
            WormStrainAlleleFieldMadeWithPlasmids(),
            "notes",
            "created_by",
            FieldCreated(),
            FieldLastChanged(),
            FieldSequenceFeature(model=model),
        ]
        super().__init__(model)
