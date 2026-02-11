from django.contrib.postgres.fields import ArrayField
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

# Static properties
VIRUS_BASE_LIST_DISPLAY = [
    "typ_e",
    "resistance",
    "created_by",
    "approval_formatted",
]
VIRUS_BASE_EXPORT_FIELD_NAMES = [
    "id",
    "name",
    "typ_e",
    "resistance",
    "us_e",
    "helper_plasmids",
    "helper_cellline",
    "construction",
    "note",
    "locations",
    "created_date_time",
    "created_by",
    "locations",
]
VIRUS_BASE_AUTOCOMPLETE_FIELDS = [
    "formz_projects",
    "sequence_features",
    "helper_plasmids",
    "helper_cellline",
    "formz_gentech_methods",
]
VIRUS_BASE_SPECIFIC_FIELDS = [
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
VIRUS_BASE_HISTORY_ARRAY_FIELDS = {
    "history_formz_projects": "formz.Project",
    "history_formz_gentech_methods": "formz.GenTechMethod",
    "history_sequence_features": "formz.SequenceFeature",
    "history_helper_plasmids": "collection.Plasmid",
    "history_locations": "collection.LocationItem",
}
VIRUS_BASE_UNMODIFIABLE_FIELDS = [
    "created_date_time",
    "created_approval_by_pi",
    "last_changed_date_time",
    "last_changed_approval_by_pi",
    "created_by",
]


class VirusBase(
    EnhancedModelCleanMixin,
    SaveWithoutHistoricalRecord,
    CommonCollectionModelPropertiesMixin,
    HistoryDocFieldMixin,
    FormZFieldsMixin,
    HistoryFieldMixin,
    LocationMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        abstract = True

    # Fields
    name = models.CharField("name", max_length=255, blank=False, unique=True)
    typ_e = models.CharField(
        "type",
        max_length=15,
        blank=False,
    )
    helper_cellline = models.ForeignKey(
        "CellLine",
        verbose_name="helper cell line",
        on_delete=models.PROTECT,
        related_name="%(class)s_helper_cellline",
        blank=False,
        null=True,
    )
    resistance = models.CharField("resistance", max_length=255, blank=False)
    us_e = models.CharField("use", max_length=255, blank=True)
    helper_plasmids = models.ManyToManyField(
        "Plasmid",
        verbose_name="helper plasmids",
        help_text="Add both helper/packaging and specific plasmids",
        related_name="%(class)s_helper_plasmids",
        blank=False,
    )
    construction = models.TextField("construction", blank=True)
    note = models.CharField("note", max_length=255, blank=True)

    history_helper_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="plasmids",
        blank=True,
        null=True,
        default=list,
    )

    # Static properties
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
    _actions = [
        export_xlsx_action,
        export_tsv_action,
        formz_as_html,
    ]

    def __str__(self):
        return f"{self.id} - {self.name}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.name = self.name.strip()

        super().save(force_insert, force_update, using, update_fields)

    @property
    def all_instock_plasmids(self):
        """Returns all helper plasmids that have been used to create the organism"""
        return self.helper_plasmids.all().distinct().order_by("id")

    @property
    def all_sequence_features(self):
        """Returns all features in a virus"""

        elements = self.sequence_features.all()
        all_plasmids = self.helper_plasmids.all()
        for pl in all_plasmids:
            elements = elements | pl.sequence_features.all()

        elements = (
            elements.distinct()
            | self.helper_cellline.all_sequence_features.all().distinct()
        )
        return elements.distinct().order_by("name")

    @property
    def formz_species(self):
        species = self.helper_cellline.organism
        species.virus_helper = self.helper_cellline
        return species


# Virus Mammalian


class VirusMammalianDoc(DocFileMixin):
    class Meta:
        verbose_name = "virus doc - Mammalian"
        verbose_name_plural = "virus docs - Mammalian"

    _inline_foreignkey_fieldname = "virus"
    _mixin_props = {
        "destination_dir": "collection/virusmammaliandoc/",
        "file_prefix": "vmDoc",
        "parent_field_name": "virus",
    }

    virus = models.ForeignKey("VirusMammalian", on_delete=models.PROTECT)


class VirusMammalian(VirusBase):
    class Meta:
        verbose_name = "virus - Mammalian"
        verbose_name_plural = "viruses - Mammalian"

    typ_e = models.CharField(
        "type",
        choices=(
            ("lenti", "Lentivirus"),
            ("retro", "Retrovirus"),
            ("adenoassociated", "Adeno-associated virus"),
        ),
        max_length=15,
        blank=False,
    )

    # Static properties
    _model_abbreviation = "vm"
    _show_in_frontend = True
    _frontend_verbose_name = "virus - Mammalian"
    _frontend_verbose_plural = "viruses - Mammalian"
    _history_array_fields = VIRUS_BASE_HISTORY_ARRAY_FIELDS.copy()
    _history_array_fields["history_documents"] = "collection.VirusMammalianDoc"
    _list_display = VIRUS_BASE_LIST_DISPLAY.copy()
    _export_field_names = VIRUS_BASE_EXPORT_FIELD_NAMES.copy()
    _autocomplete_fields = VIRUS_BASE_AUTOCOMPLETE_FIELDS.copy()
    _obj_specific_fields = VIRUS_BASE_SPECIFIC_FIELDS.copy()
    _obj_unmodifiable_fields = VIRUS_BASE_UNMODIFIABLE_FIELDS
    formz_field_index = _obj_specific_fields.index("formz_projects") - 1
    _add_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields[:formz_field_index]},
        ],
        [
            "FormZ",
            {
                "classes": tuple(),
                "fields": _obj_specific_fields[formz_field_index:],
            },
        ],
    ]
    _change_view_fieldsets = [
        [
            None,
            {
                "fields": _obj_specific_fields[:formz_field_index]
                + _obj_unmodifiable_fields
            },
        ],
        [
            "FormZ",
            {
                "classes": (("collapse",)),
                "fields": _obj_specific_fields[formz_field_index:],
            },
        ],
    ]


# Virus insect


class VirusInsectDoc(DocFileMixin):
    class Meta:
        verbose_name = "virus doc - Insect"
        verbose_name_plural = "virus docs - Insect"

    _inline_foreignkey_fieldname = "virus"
    _mixin_props = {
        "destination_dir": "collection/virusinsectdoc/",
        "file_prefix": "viDoc",
        "parent_field_name": "virus",
    }

    virus = models.ForeignKey("VirusInsect", on_delete=models.PROTECT)


class VirusInsect(VirusBase):
    class Meta:
        verbose_name = "virus - Insect"
        verbose_name_plural = "viruses - Insect"

    # Fields
    typ_e = models.CharField(
        "type",
        choices=(("baculo", "Baculovirus"),),
        default="baculo",
        max_length=15,
        blank=False,
    )
    helper_ecolistrain = models.ForeignKey(
        "EColiStrain",
        verbose_name="helper E. coli",
        help_text="The strain used for bacmid generation",
        on_delete=models.PROTECT,
        related_name="%(class)s_helper_ecolistrain",
        blank=False,
        null=True,
    )

    # Static properties
    _model_abbreviation = "vi"
    _show_in_frontend = True
    _frontend_verbose_name = "virus - Insect"
    _frontend_verbose_plural = "viruses - Insect"
    _history_array_fields = VIRUS_BASE_HISTORY_ARRAY_FIELDS.copy()
    _history_array_fields["history_documents"] = "collection.VirusInsectDoc"
    _list_display = VIRUS_BASE_LIST_DISPLAY.copy()
    _export_field_names = VIRUS_BASE_EXPORT_FIELD_NAMES.copy()
    _autocomplete_fields = VIRUS_BASE_AUTOCOMPLETE_FIELDS.copy()
    _obj_specific_fields = VIRUS_BASE_SPECIFIC_FIELDS.copy()
    _obj_unmodifiable_fields = VIRUS_BASE_UNMODIFIABLE_FIELDS
    _autocomplete_fields.append("helper_ecolistrain")
    _obj_specific_fields.insert(
        _obj_specific_fields.index("helper_cellline"),
        "helper_ecolistrain",
    )
    _export_field_names.insert(
        _export_field_names.index("helper_cellline"),
        "helper_ecolistrain",
    )
    formz_field_index = _obj_specific_fields.index("formz_projects") - 1
    _add_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields[:formz_field_index]},
        ],
        [
            "FormZ",
            {
                "classes": tuple(),
                "fields": _obj_specific_fields[formz_field_index:],
            },
        ],
    ]
    _change_view_fieldsets = [
        [
            None,
            {
                "fields": _obj_specific_fields[:formz_field_index]
                + _obj_unmodifiable_fields
            },
        ],
        [
            "FormZ",
            {
                "classes": (("collapse",)),
                "fields": _obj_specific_fields[formz_field_index:],
            },
        ],
    ]

    @property
    def all_sequence_features(self):
        """Returns all features in an insect virus"""

        elements = (
            super().all_sequence_features
            | self.helper_ecolistrain.all_sequence_features.all().distinct()
        )
        return elements.distinct().order_by("name")
