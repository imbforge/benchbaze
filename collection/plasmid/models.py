import random
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from import_export.fields import Field

from common.actions import export_tsv_action, export_xlsx_action
from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    HistoryFieldMixin,
    SaveWithoutHistoricalRecord,
)
from formz.actions import formz_as_html
from formz.models import GenTechMethod, SequenceFeature, ZkbsPlasmid
from formz.models import Project as FormZProject

from ..ecolistrain.models import EColiStrain
from ..shared.models import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    DnaMapMixin,
    FormZFieldsMixin,
    OwnershipFieldsMixin,
)

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)


PLASMID_AS_ECOLI_STOCK = getattr(settings, "PLASMID_AS_ECOLI_STOCK", False)


class PlasmidDoc(DocFileMixin):
    class Meta:
        verbose_name = "plasmid document"

    _inline_foreignkey_fieldname = "plasmid"
    _mixin_props = {
        "destination_dir": "collection/plasmiddoc/",
        "file_prefix": "pDoc",
        "parent_field_name": "plasmid",
    }

    plasmid = models.ForeignKey("Plasmid", on_delete=models.PROTECT)


class Plasmid(
    SaveWithoutHistoricalRecord,
    DownloadFileNameMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryFieldMixin,
    DnaMapMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "plasmid"
        verbose_name_plural = "plasmids"

    _model_upload_to = "collection/plasmid/"

    # Fields
    name = models.CharField("name", max_length=255, unique=True, blank=False)
    other_name = models.CharField("other name", max_length=255, blank=True)
    parent_vector = models.ForeignKey(
        "self",
        verbose_name="parent vector",
        related_name="%(class)s_parent_vector",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    old_parent_vector = models.CharField(
        "orig. parent vector field",
        help_text="Use only when strictly necessary",
        max_length=255,
        blank=True,
    )
    selection = models.CharField("selection", max_length=50, blank=False)
    us_e = models.CharField("use", max_length=255, blank=True)
    construction_feature = models.TextField("construction/features", blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    note = models.CharField("note", max_length=300, blank=True)
    reference = models.CharField("reference", max_length=255, blank=True)
    map = models.FileField(
        "Map (.dna)",
        help_text=f"only SnapGene .dna files, max. {FILE_SIZE_LIMIT_MB} MB",
        upload_to=_model_upload_to + "dna/",
        blank=True,
    )
    map_png = models.ImageField(
        "Map image", upload_to=_model_upload_to + "png/", blank=True
    )
    map_gbk = models.FileField(
        "Map (.gbk)",
        upload_to=_model_upload_to + "gbk/",
        help_text=f"only .gbk or .gb files, max. {FILE_SIZE_LIMIT_MB} MB",
        blank=True,
    )
    vector_zkbs = models.ForeignKey(
        ZkbsPlasmid,
        verbose_name="ZKBS database vector",
        on_delete=models.PROTECT,
        blank=False,
        null=True,
        help_text="The backbone of the plasmid, from the ZKBS database. If not applicable, "
        'choose none. <a href="/formz/zkbsplasmid/" target="_blank">View all</a>',
    )
    formz_ecoli_strains = models.ManyToManyField(
        "EColiStrain",
        verbose_name="e. coli strains",
        related_name="%(class)s_ecoli_strains",
        blank=False,
    )

    history_formz_ecoli_strains = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="e. coli strains",
        blank=True,
        null=True,
        default=list,
    )
    history_documents = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="documents",
        blank=True,
        null=True,
        default=list,
    )

    # Static properties
    _model_abbreviation = "p"
    _show_in_frontend = True
    _history_array_fields = {
        "history_formz_projects": FormZProject,
        "history_formz_gentech_methods": GenTechMethod,
        "history_sequence_features": SequenceFeature,
        "history_formz_ecoli_strains": EColiStrain,
        "history_documents": PlasmidDoc,
    }
    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + OwnershipFieldsMixin._history_view_ignore_fields
        + ["map_png", "map_gbk"]
    )
    _unified_map_field = True
    _show_formz = True
    german_name = "Plasmid"
    _representation_field = "name"
    _list_display_links = ["id"]
    _search_fields = [
        "id",
        "name",
    ]
    _list_display_frozen = _search_fields
    _list_display = [
        "selection",
        "map_formatted",
        "created_by",
        "approval_formatted",
    ]
    _autocomplete_fields = [
        "parent_vector",
        "formz_projects",
        "sequence_features",
        "vector_zkbs",
        "formz_ecoli_strains",
        "formz_gentech_methods",
    ]
    _export_field_names = [
        "id",
        "name",
        "other_name",
        "parent_vector",
        "additional_parent_vector_info",
        "selection",
        "us_e",
        "construction_feature",
        "received_from",
        "note",
        "reference",
        "map",
        "created_date_time",
        "created_by",
    ]
    _export_custom_fields = {
        "fields": {
            "additional_parent_vector_info": Field(
                column_name="Extra parent vector info", attribute="old_parent_vector"
            )
        },
        "dehydrate_methods": dict(),
    }
    _actions = [export_xlsx_action, export_tsv_action, formz_as_html]
    _clone_ignore_fields = ["map", "map_gbk", "map_png", "destroyed_date"]
    _obj_unmodifiable_fields = [
        "created_date_time",
        "created_approval_by_pi",
        "last_changed_date_time",
        "last_changed_approval_by_pi",
        "created_by",
    ]
    _obj_specific_fields = [
        "name",
        "other_name",
        "parent_vector",
        "selection",
        "us_e",
        "construction_feature",
        "received_from",
        "note",
        "reference",
        "map",
        "map_png",
        "map_gbk",
        "formz_projects",
        "formz_risk_group",
        "vector_zkbs",
        "formz_gentech_methods",
        "sequence_features",
        "formz_ecoli_strains",
        "destroyed_date",
    ]
    _set_readonly_fields = [
        "map_png",
    ]
    _add_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields[:10] + _obj_specific_fields[11:12]},
        ],
        [
            "FormZ",
            {
                "classes": tuple(),
                "fields": _obj_specific_fields[12:],
            },
        ],
    ]
    _change_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields[:12] + _obj_unmodifiable_fields},
        ],
        [
            "FormZ",
            {
                "classes": (("collapse",)),
                "fields": _obj_specific_fields[12:],
            },
        ],
    ]

    # Methods
    def __str__(self):
        return f"{self.id} - {self.name}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # If destroyed date not present, automatically set it if a plasmid is
        # not kept as E. coli stock
        if not PLASMID_AS_ECOLI_STOCK and not self.destroyed_date:
            self.destroyed_date = datetime.now().date() + timedelta(
                days=random.randint(7, 21)
            )

        super().save(force_insert, force_update, using, update_fields)

    @property
    def all_plasmids_with_maps(self):
        if self.map:
            return [self]
        else:
            return []
