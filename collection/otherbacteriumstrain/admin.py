from common.admin import AddDocFileInlineMixin, DocFileInlineMixin
from formz.models import Species

from ..shared.admin import (
    AddLocationInline,
    CollectionUserProtectionAdmin,
    LocationInline,
)
from .models import OtherBacteriumStrainDoc
from .search import OtherBacteriumStrainQLSchema


class OtherBacteriumStrainDocInline(DocFileInlineMixin):
    """Inline to view existing bacterial strain documents"""

    model = OtherBacteriumStrainDoc


class OtherBacteriumStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new bacterial strain documents"""

    model = OtherBacteriumStrainDoc


class OtherBacteriumStrainAdmin(CollectionUserProtectionAdmin):
    djangoql_schema = OtherBacteriumStrainQLSchema
    inlines = [
        LocationInline,
        AddLocationInline,
        OtherBacteriumStrainDocInline,
        OtherBacteriumStrainAddDocInline,
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # For species field, only show those species for
        # which show_for_other_bacterium_strain was ticked
        if db_field.name == "species":
            kwargs["queryset"] = Species.objects.filter(
                show_for_other_bacterium_strain=True
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
