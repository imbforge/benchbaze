from django.db import models
from import_export.fields import Field

from common.models import DocFileMixin

from ..shared.models import (
    ApprovalFieldsMixin,
    BaseCollectionModel,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryDocFieldMixin,
    LocationMixin,
)


class OtherBacteriumStrainDoc(DocFileMixin):
    class Meta:
        verbose_name = "Other bacterium strain document"

    _inline_foreignkey_fieldname = "other_bacterium_strain"
    _mixin_props = {
        "destination_dir": "collection/otherbacteriumstraindoc/",
        "file_prefix": "bacDoc",
        "parent_field_name": "other_bacterium_strain",
    }

    other_bacterium_strain = models.ForeignKey(
        "OtherBacteriumStrain", on_delete=models.PROTECT
    )


class OtherBacteriumStrain(
    CommonCollectionModelPropertiesMixin,
    HistoryDocFieldMixin,
    FormZFieldsMixin,
    LocationMixin,
    ApprovalFieldsMixin,
    BaseCollectionModel,
):
    class Meta:
        verbose_name = "strain - Other Bacterium"
        verbose_name_plural = "strains - Other Bacterium"

    name = models.CharField("name", max_length=255, blank=False)
    species = models.ForeignKey(
        "formz.Species",
        verbose_name="species",
        on_delete=models.PROTECT,
        null=True,
        blank=False,
    )
    genotype = models.TextField("genotype", blank=True)
    background = models.CharField("background", max_length=255, blank=True)
    resistance = models.CharField("resistance", max_length=255, blank=True)
    supplier = models.CharField("supplier", max_length=255, blank=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    note = models.TextField("note", max_length=255, blank=True)

    formz_gentech_methods = None
    history_formz_gentech_methods = None

    # Static properties
    _model_abbreviation = "bac"
    _show_formz = True
    _is_guarded_model = True
    _show_in_frontend = "Strains - Bacterial"
    _frontend_verbose_name = "Strain - Bacterial"
    _storage_requires_species = True
    _frontend_verbose_plural = _show_in_frontend
    _history_array_fields = {
        "history_formz_projects": "formz.Project",
        "history_sequence_features": "formz.SequenceFeature",
        "history_documents": "collection.OtherBacteriumStrainDoc",
        "history_locations": "collection.LocationItem",
    }
    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + BaseCollectionModel._history_view_ignore_fields
    )
    _representation_field = "name"
    _list_display_links = ["id"]
    _search_fields = [
        "id",
        "name",
    ]
    _list_display_frozen = _search_fields
    _list_display = ["species", "us_e", "approval_formatted"]
    _autocomplete_fields = ["formz_projects", "sequence_features"]
    _export_field_names = [
        "id",
        "name",
        "species_name_custom_field",
        "genotype",
        "background",
        "resistance",
        "supplier",
        "us_e",
        "note",
        "created_date_time",
        "created_by",
        "locations",
    ]
    _export_custom_fields = {
        "fields": {"species_name_custom_field": Field(column_name="Organism name")},
        "dehydrate_methods": {
            "species_name_custom_field": lambda obj: str(obj.species)
        },
    }
    _obj_specific_fields = [
        "name",
        "species",
        "genotype",
        "background",
        "resistance",
        "supplier",
        "us_e",
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
    formz_projects_idx = _obj_specific_fields.index("formz_projects")
    _add_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields[:formz_projects_idx]},
        ],
        [
            "FormZ",
            {
                "classes": tuple(),
                "fields": _obj_specific_fields[formz_projects_idx:],
            },
        ],
    ]
    _change_view_fieldsets = [
        [
            None,
            {
                "fields": _obj_specific_fields[:formz_projects_idx]
                + _obj_unmodifiable_fields
            },
        ],
        [
            "FormZ",
            {
                "classes": (("collapse",)),
                "fields": _obj_specific_fields[formz_projects_idx:],
            },
        ],
    ]

    # Methods
    def __str__(self):
        return f"{self.id} - {self.name}"

    @property
    def formz_species(self):
        species = self.species
        species.risk_group = self.formz_risk_group
        return species
