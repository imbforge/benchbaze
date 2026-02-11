from django.db import models

from common.actions import export_tsv_action, export_xlsx_action
from common.models import (
    DocFileMixin,
    EnhancedModelCleanMixin,
    HistoryFieldMixin,
    SaveWithoutHistoricalRecord,
)
from formz.actions import formz_as_html

from ..shared.models import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryDocFieldMixin,
    LocationMixin,
    OwnershipFieldsMixin,
)


class EColiStrainDoc(DocFileMixin):
    class Meta:
        verbose_name = "e. coli strain document"

    _inline_foreignkey_fieldname = "ecoli_strain"
    _mixin_props = {
        "destination_dir": "collection/ecolistraindoc/",
        "file_prefix": "ecDoc",
        "parent_field_name": "ecoli_strain",
    }

    ecoli_strain = models.ForeignKey("EColiStrain", on_delete=models.PROTECT)


class EColiStrain(
    EnhancedModelCleanMixin,
    SaveWithoutHistoricalRecord,
    CommonCollectionModelPropertiesMixin,
    HistoryDocFieldMixin,
    FormZFieldsMixin,
    LocationMixin,
    HistoryFieldMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "strain - E. coli"
        verbose_name_plural = "strains - E. coli"

    name = models.CharField("name", max_length=255, blank=False)
    resistance = models.CharField("resistance", max_length=255, blank=True)
    genotype = models.TextField("genotype", blank=True)
    background = models.CharField(
        "background",
        max_length=255,
        choices=(("B", "B"), ("C", "C"), ("K12", "K12"), ("W", "W")),
        blank=True,
    )
    supplier = models.CharField("supplier", max_length=255)
    us_e = models.CharField(
        "use",
        max_length=255,
        choices=(
            ("Cloning", "Cloning"),
            ("Expression", "Expression"),
            ("Other", "Other"),
        ),
    )
    purpose = models.TextField("purpose", blank=True)
    note = models.TextField("note", max_length=255, blank=True)

    formz_gentech_methods = None
    history_formz_gentech_methods = None

    # Static properties
    _model_abbreviation = "ec"
    _show_formz = True
    _show_in_frontend = "Strains - <em>E. coli</em>"
    _frontend_verbose_name = "Strain - <em>E. coli</em>"
    _storage_requires_species = "Escherichia coli"
    _frontend_verbose_plural = _show_in_frontend
    _history_array_fields = {
        "history_formz_projects": "formz.Project",
        "history_sequence_features": "formz.SequenceFeature",
        "history_documents": "collection.EColiStrainDoc",
        "history_locations": "collection.LocationItem",
    }
    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + OwnershipFieldsMixin._history_view_ignore_fields
    )
    _representation_field = "name"
    _list_display_links = ["id"]
    _search_fields = [
        "id",
        "name",
    ]
    _list_display_frozen = _search_fields
    _list_display = ["resistance", "us_e", "purpose", "approval_formatted"]
    _autocomplete_fields = ["formz_projects", "sequence_features"]
    _export_field_names = [
        "id",
        "name",
        "resistance",
        "genotype",
        "supplier",
        "us_e",
        "purpose",
        "note",
        "created_date_time",
        "created_by",
        "locations",
    ]
    _actions = [export_xlsx_action, export_tsv_action, formz_as_html]
    _obj_specific_fields = [
        "name",
        "resistance",
        "genotype",
        "background",
        "supplier",
        "us_e",
        "purpose",
        "note",
        "formz_projects",
        "formz_risk_group",
        "sequence_features",
        "destroyed_date",
    ]
    _obj_unmodifiable_fields = [
        "created_date_time",
        "created_approval_by_pi",
        "last_changed_date_time",
        "last_changed_approval_by_pi",
        "created_by",
    ]
    _add_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields[:8]},
        ],
        [
            "FormZ",
            {
                "classes": tuple(),
                "fields": _obj_specific_fields[8:],
            },
        ],
    ]
    _change_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields[:8] + _obj_unmodifiable_fields},
        ],
        [
            "FormZ",
            {
                "classes": (("collapse",)),
                "fields": _obj_specific_fields[8:],
            },
        ],
    ]

    # Methods
    def __str__(self):
        return f"{self.id} - {self.name}"
