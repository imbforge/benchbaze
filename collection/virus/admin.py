from django.conf import settings
from django.db.models import CharField
from django.forms import TextInput

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)
from formz.actions import formz_as_html

from ..shared.admin import (
    AddLocationInline,
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    LocationInline,
    SortAutocompleteResultsId,
)
from .actions import export_virus_insect, export_virus_mammalian
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


class VirusBaseAdmin(
    SortAutocompleteResultsId, CustomGuardedModelAdmin, CollectionUserProtectionAdmin
):
    helper_field_name = "_helper"
    list_display = (
        "id",
        "name",
        "resistance",
        "typ_e",
        "resistance",
        "created_by",
        "approval",
    )
    list_display_links = ("id",)
    list_per_page = 25
    formfield_overrides = {
        CharField: {"widget": TextInput(attrs={"size": "93"})},
    }
    djangoql_completion_enabled_by_default = False
    search_fields = ["id", "name"]

    obj_unmodifiable_fields = [
        "created_date_time",
        "created_approval_by_pi",
        "last_changed_date_time",
        "last_changed_approval_by_pi",
        "created_by",
    ]
    obj_specific_fields = [
        "name",
        "typ_e",
        "resistance",
        "us_e",
        "helper_plasmids",
        "helper_cellline",
        "construction",
        "note",
        "formz_projects",
        "formz_risk_group",
        "formz_gentech_methods",
        "sequence_features",
        "destroyed_date",
    ]
    autocomplete_fields = [
        "formz_projects",
        "sequence_features",
        "helper_plasmids",
        "helper_cellline",
        "formz_gentech_methods",
    ]

    def __init__(self, model, admin_site):
        formz_field_index = self.obj_specific_fields.index("formz_projects") - 1
        self.add_view_fieldsets = [
            [
                None,
                {"fields": self.obj_specific_fields[:formz_field_index]},
            ],
            [
                "FormZ",
                {
                    "classes": tuple(),
                    "fields": self.obj_specific_fields[formz_field_index:],
                },
            ],
        ]
        self.change_view_fieldsets = [
            [
                None,
                {
                    "fields": self.obj_specific_fields[:formz_field_index]
                    + self.obj_unmodifiable_fields
                },
            ],
            [
                "FormZ",
                {
                    "classes": (("collapse",)),
                    "fields": self.obj_specific_fields[formz_field_index:],
                },
            ],
        ]

        super().__init__(model, admin_site)


class VirusMammalianAdmin(VirusBaseAdmin):
    djangoql_schema = VirusMammalianQLSchema
    inlines = [
        LocationInline,
        AddLocationInline,
        VirusMammalianDocInline,
        VirusMammalianDocAddDocInline,
    ]
    actions = [export_virus_mammalian, formz_as_html]
    change_form_template = "admin/collection/virusmammalian/change_form.html"


class VirusInsectAdmin(VirusBaseAdmin):
    djangoql_schema = VirusInsectQLSchema
    inlines = [
        LocationInline,
        AddLocationInline,
        VirusInsectDocInline,
        VirusInsectAddDocInline,
    ]
    actions = [export_virus_insect, formz_as_html]
    change_form_template = "admin/collection/virusinsect/change_form.html"

    def __init__(self, model, admin_site):
        # Add helper_ecolistrain field in the list of fields to display in the add
        # and change form, and in the autocomplete fields for the change form
        obj_specific_fields = self.obj_specific_fields.copy()
        autocomplete_fields = self.autocomplete_fields.copy()
        obj_specific_fields.insert(
            obj_specific_fields.index("helper_cellline"), "helper_ecolistrain"
        )
        autocomplete_fields.append("helper_ecolistrain")
        self.obj_specific_fields = obj_specific_fields
        self.autocomplete_fields = autocomplete_fields

        super().__init__(model, admin_site)

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
