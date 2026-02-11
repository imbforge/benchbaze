from common.admin import AddDocFileInlineMixin, DocFileInlineMixin

from ..shared.admin import (
    AddLocationInline,
    CollectionSimpleAdmin,
    LocationInline,
)
from .models import InhibitorDoc
from .search import InhibitorQLSchema


class InhibitorDocInline(DocFileInlineMixin):
    """Inline to view existing Inhibitor documents"""

    model = InhibitorDoc


class InhibitorAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Inhibitor documents"""

    model = InhibitorDoc


class InhibitorAdmin(CollectionSimpleAdmin):
    djangoql_schema = InhibitorQLSchema
    inlines = [
        LocationInline,
        AddLocationInline,
        InhibitorDocInline,
        InhibitorAddDocInline,
    ]
