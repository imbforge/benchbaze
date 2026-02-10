from django.contrib import admin
from django.utils.safestring import mark_safe

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
    GetParentObjectInlineMixin,
)
from formz.actions import formz_as_html
from formz.models import Species

from ..shared.actions import create_label
from ..shared.admin import (
    AddLocationInline,
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    LocationInline,
    SortAutocompleteResultsId,
)
from .actions import export_cellline
from .models import (
    CellLineDoc,
    CellLineEpisomalPlasmid,
    CellLineVirusTransient,
)
from .search import CellLineQLSchema


class CellLineDocAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
    list_display_links = (
        "id",
        "name",
    )
    list_per_page = 25
    ordering = ["id"]

    def has_module_permission(self, request):
        """Hide module from Admin"""
        return False

    def get_readonly_fields(self, request, obj=None):
        """Override default get_readonly_fields"""

        if obj:
            return [
                "name",
                "description",
                "date_of_test",
                "cell_line",
                "created_date_time",
            ]

    def add_view(self, request, extra_context=None):
        """Override default add_view to show only desired fields"""

        self.fields = ["name", "description", "cell_line", "comment", "date_of_test"]
        return super().add_view(request)

    def change_view(self, request, object_id, extra_context=None):
        """Override default change_view to show only desired fields"""

        self.fields = [
            "name",
            "description",
            "date_of_test",
            "cell_line",
            "comment",
            "created_date_time",
        ]
        return super().change_view(request, object_id)


class CellLineDocInline(DocFileInlineMixin):
    """Inline to view existing cell line documents"""

    model = CellLineDoc
    fields = ["description", "date_of_test", "get_doc_short_name", "comment"]
    readonly_fields = fields[:-1]


class AddCellLineDocInline(AddDocFileInlineMixin):
    """Inline to add new cell line documents"""

    model = CellLineDoc
    fields = ["description", "date_of_test", "name", "comment"]


class CellLineEpisomalPlasmidInline(GetParentObjectInlineMixin):
    autocomplete_fields = ["plasmid", "formz_projects"]
    model = CellLineEpisomalPlasmid
    verbose_name_plural = mark_safe(
        'Transiently transfected plasmids <span style="text-transform:lowercase;">'
        '(virus packaging plasmids are highlighted in <span style="color:var(--accent)">'
        "yellow</span>)</span>"
    )
    verbose_name = "Episomal Plasmid"
    extra = 0
    template = "admin/tabular.html"

    def get_queryset(self, request):
        """Do not show as collapsed in add view"""

        parent_object = self.get_parent_object(request)
        self.classes = ["collapse"]

        if parent_object:
            parent_obj_episomal_plasmids = parent_object.episomal_plasmids.all()
            if parent_obj_episomal_plasmids.filter(
                celllineepisomalplasmid__s2_work_episomal_plasmid=True
            ):
                self.classes = None
        else:
            self.classes = None
        return super().get_queryset(request)


class CellLineVirusTransientInline(GetParentObjectInlineMixin):
    extra = 0
    template = "admin/tabular.html"
    model = CellLineVirusTransient
    autocomplete_fields = ["virus_mammalian", "virus_insect", "formz_projects"]
    fields = [
        ["virus_mammalian", "virus_insect"],
        "formz_projects",
        "created_date",
        "destroyed_date",
    ]
    verbose_name_plural = "Viruses (transient)"
    verbose_name = "Virus (transient)"

    def get_queryset(self, request):
        """Do not show as collapsed in add view if there are safety level 2 viruses"""
        parent_object = self.get_parent_object(request)
        self.classes = ["collapse"]

        if (
            parent_object
            and parent_object.viruses_transient.filter(
                formz_projects__safety_level__gt=1
            ).exists()
        ):
            self.classes = None

        return super().get_queryset(request)


class CellLineAdmin(
    SortAutocompleteResultsId, CustomGuardedModelAdmin, CollectionUserProtectionAdmin
):
    list_display = ("id", "name", "box_name", "created_by", "approval")
    list_display_links = ("id",)
    djangoql_schema = CellLineQLSchema
    inlines = [
        CellLineEpisomalPlasmidInline,
        CellLineVirusTransientInline,
        LocationInline,
        AddLocationInline,
        CellLineDocInline,
        AddCellLineDocInline,
    ]
    actions = [export_cellline, formz_as_html, create_label]
    search_fields = ["id", "name"]
    show_plasmids_in_model = True
    autocomplete_fields = [
        "parental_line",
        "integrated_plasmids",
        "viruses_mammalian_integrated",
        "formz_projects",
        "zkbs_cell_line",
        "formz_gentech_methods",
        "sequence_features",
    ]
    obj_specific_fields = [
        "name",
        "box_name",
        "alternative_name",
        "parental_line",
        "organism",
        "cell_type_tissue",
        "culture_type",
        "growth_condition",
        "freezing_medium",
        "received_from",
        "integrated_plasmids",
        "viruses_mammalian_integrated",
        "description_comment",
        "s2_work",
        "formz_projects",
        "formz_risk_group",
        "zkbs_cell_line",
        "formz_gentech_methods",
        "sequence_features",
        "destroyed_date",
    ]
    obj_unmodifiable_fields = [
        "created_date_time",
        "created_approval_by_pi",
        "last_changed_date_time",
        "last_changed_approval_by_pi",
        "created_by",
    ]
    add_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:14]},
        ],
        [
            "FormZ",
            {"classes": tuple(), "fields": obj_specific_fields[14:]},
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:14] + obj_unmodifiable_fields},
        ],
        [
            "FormZ",
            {"classes": (("collapse",)), "fields": obj_specific_fields[14:]},
        ],
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # For organism field, only show those species for
        # which show_in_cell_line_collect was ticked
        if db_field.name == "organism":
            kwargs["queryset"] = Species.objects.filter(
                show_in_cell_line_collection=True
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
