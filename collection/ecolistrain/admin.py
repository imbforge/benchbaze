from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)

from ..shared.admin import (
    CollectionUserProtectionAdmin,
)
from .models import EColiStrainDoc
from .search import EColiStrainQLSchema


class EcoliStrainDocInline(DocFileInlineMixin):
    """Inline to view existing E. coli strain documents"""

    model = EColiStrainDoc


class EColiStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new E. coli strain documents"""

    model = EColiStrainDoc


class EColiStrainAdmin(CollectionUserProtectionAdmin):
    djangoql_schema = EColiStrainQLSchema
    inlines = [EcoliStrainDocInline, EColiStrainAddDocInline]
