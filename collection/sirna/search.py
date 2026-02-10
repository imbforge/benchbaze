from ..shared.admin import (
    FieldCreated,
    FieldLastChanged,
)
from ..shared.search import CollectionQLSchema


class SiRnaQLSchema(CollectionQLSchema):
    """DjangoQL schema for SiRna collection model"""

    fields = [
        "id",
        "name",
        "sequence",
        "sequence_antisense",
        "supplier",
        "supplier_part_no",
        "supplier_si_rna_id",
        "species",
        "target_genes",
        "locus_ids",
        "description_comment",
        "info_sheet",
        "created_by",
        FieldCreated(),
        FieldLastChanged(),
        "locations",
    ]
