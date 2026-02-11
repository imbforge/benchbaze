from django.conf import settings

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)

from ..shared.admin import (
    AddLocationInline,
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    LocationInline,
    SortAutocompleteResultsId,
)
from .models import VirusInsectDoc, VirusMammalianDoc
from .search import VirusInsectQLSchema, VirusMammalianQLSchema

DEFAULT_HELPER_ECOLI_VIRUS_INSECT_ID = getattr(
    settings, "DEFAULT_HELPER_ECOLI_VIRUS_INSECT_ID", None
)
DEFAULT_HELPER_CELLLINE_VIRUS_INSECT_ID = getattr(
    settings, "DEFAULT_HELPER_CELLLINE_VIRUS_INSECT_ID", None
)


class VirusMammalianDocInline(DocFileInlineMixin):
    """Inline to view existing virus strain documents"""

    model = VirusMammalianDoc


class VirusMammalianDocAddDocInline(AddDocFileInlineMixin):
    """Inline to add new virus strain documents"""

    model = VirusMammalianDoc


class VirusInsectDocInline(DocFileInlineMixin):
    """Inline to view existing virus strain documents"""

    model = VirusInsectDoc


class VirusInsectAddDocInline(AddDocFileInlineMixin):
    """Inline to add new virus strain documents"""

    model = VirusInsectDoc


class VirusMammalianAdmin(
    SortAutocompleteResultsId, CustomGuardedModelAdmin, CollectionUserProtectionAdmin
):
    djangoql_schema = VirusMammalianQLSchema
    inlines = [
        LocationInline,
        AddLocationInline,
        VirusMammalianDocInline,
        VirusMammalianDocAddDocInline,
    ]
    change_form_template = "admin/collection/virusmammalian/change_form.html"


class VirusInsectAdmin(
    SortAutocompleteResultsId, CustomGuardedModelAdmin, CollectionUserProtectionAdmin
):
    djangoql_schema = VirusInsectQLSchema
    inlines = [
        LocationInline,
        AddLocationInline,
        VirusInsectDocInline,
        VirusInsectAddDocInline,
    ]
    change_form_template = "admin/collection/virusinsect/change_form.html"

    def get_form(self, request, obj=None, change=False, **kwargs):
        """Override get_form to set default values for helper_ecolistrain
        and helper_cellline when creating a new VirusInsect object"""

        form = super().get_form(request, obj, change, **kwargs)
        # For new objects
        if not obj:
            # Set default E. coli strains
            if (
                DEFAULT_HELPER_ECOLI_VIRUS_INSECT_ID
                and "helper_ecolistrain" in form.base_fields
            ):
                form.base_fields[
                    "helper_ecolistrain"
                ].initial = DEFAULT_HELPER_ECOLI_VIRUS_INSECT_ID
            # Set storage type
            if (
                DEFAULT_HELPER_CELLLINE_VIRUS_INSECT_ID
                and "helper_cellline" in form.base_fields
            ):
                form.base_fields[
                    "helper_cellline"
                ].initial = DEFAULT_HELPER_CELLLINE_VIRUS_INSECT_ID
        return form
