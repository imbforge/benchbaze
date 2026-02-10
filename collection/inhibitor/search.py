from ..shared.search import CollectionQLSchema


class InhibitorQLSchema(CollectionQLSchema):
    """DjangoQL schema for Inhibitor collection model"""

    fields = [
        "id",
        "name",
        "other_names",
        "target",
        "received_from",
        "catalogue_number",
        "locations",
        "description_comment",
        "info_sheet",
        "locations",
    ]
