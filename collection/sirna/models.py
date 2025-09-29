from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_better_admin_arrayfield.models.fields import ArrayField as BetterArrayField
from import_export.fields import Field
from common.actions import export_tsv_action, export_xlsx_action

from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    HistoryFieldMixin,
    SaveWithoutHistoricalRecord,
)
from formz.models import Species
from purchasing.models import Order

from ..shared.models import (
    InfoSheetMaxSizeMixin,
    OwnershipFieldsMixin,
)

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)


class SiRnaDoc(DocFileMixin):
    class Meta:
        verbose_name = "siRNA document"

    _inline_foreignkey_fieldname = "si_rna"
    _mixin_props = {
        "destination_dir": "collection/sirnadoc/",
        "file_prefix": "sirnaDoc",
        "parent_field_name": "si_rna",
    }

    si_rna = models.ForeignKey("SiRna", on_delete=models.PROTECT)


class SiRna(
    SaveWithoutHistoricalRecord,
    DownloadFileNameMixin,
    InfoSheetMaxSizeMixin,
    HistoryFieldMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "siRNA"
        verbose_name_plural = "siRNAs"

    _model_upload_to = "collection/sirna/"

    # Fields
    name = models.CharField("name", max_length=255, blank=False)
    sequence = models.CharField("sequence - Sense", max_length=50, blank=False)
    sequence_antisense = models.CharField(
        "sequence - Antisense", max_length=50, blank=False
    )

    supplier = models.CharField("supplier", max_length=255, blank=False)
    supplier_part_no = models.CharField("supplier Part-No", max_length=255, blank=False)
    supplier_si_rna_id = models.CharField(
        "supplier siRNA ID", max_length=255, blank=False
    )
    species = models.ForeignKey(
        Species,
        verbose_name="organism",
        on_delete=models.PROTECT,
        null=True,
        blank=False,
    )
    target_genes = BetterArrayField(
        models.CharField(max_length=15), blank=False, null=True, default=list
    )
    locus_ids = BetterArrayField(
        models.CharField(max_length=15),
        verbose_name="locus IDs",
        blank=True,
        null=True,
        default=list,
    )
    description_comment = models.TextField(
        "description/comments",
        help_text="Include transfection conditions, etc. here",
        blank=True,
    )
    info_sheet = models.FileField(
        "info sheet",
        help_text=f"only .pdf files, max. {FILE_SIZE_LIMIT_MB} MB",
        upload_to=_model_upload_to,
        blank=True,
        null=True,
    )
    orders = models.ManyToManyField(
        Order, verbose_name="orders", related_name="%(class)s_order", blank=True
    )

    history_orders = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="order",
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
    _model_abbreviation = "siRNA"
    _show_in_frontend = True
    _history_array_fields = {"history_orders": Order, "history_documents": SiRnaDoc}
    _history_view_ignore_fields = OwnershipFieldsMixin._history_view_ignore_fields
    _search_fields = [
        "id",
        "name",
    ]
    _list_display_frozen = _search_fields
    _list_display = [
        "sequence",
        "supplier",
        "supplier_part_no",
        "target_genes",
        "info_sheet_formatted",
        "created_by",
    ]
    _export_field_names = [
        "id",
        "name",
        "sequence",
        "sequence_antisense",
        "supplier",
        "supplier_part_no",
        "supplier_si_rna_id",
        "species_name",
        "target_genes",
        "locus_ids",
        "description_comment",
        "info_sheet",
        "orders",
        "created_date_time",
        "created_by",
    ]
    _export_custom_fields = {
        "fields": {
            "species_name": Field(column_name="Species"),
        },
        "dehydrate_methods": {"species_name": lambda obj: str(obj.species)},
    }
    _actions = [
        export_xlsx_action,
        export_tsv_action,
    ]

    _autocomplete_fields = ["created_by", "orders"]
    _clone_ignore_fields = ["info_sheet"]
    _obj_specific_fields = [
        "name",
        "sequence",
        "sequence_antisense",
        "species",
        "target_genes",
        "locus_ids",
        "description_comment",
        "info_sheet",
        "supplier",
        "supplier_part_no",
        "supplier_si_rna_id",
        "orders",
    ]
    _obj_unmodifiable_fields = [
        "created_date_time",
        "last_changed_date_time",
        "created_by",
    ]
    _add_view_fieldsets = [
        [
            None,
            {
                "fields": _obj_specific_fields[:8]
                + [
                    "created_by",
                ]
            },
        ],
        ["Supplier information", {"fields": _obj_specific_fields[8:]}],
    ]
    _change_view_fieldsets = [
        [None, {"fields": _obj_specific_fields[:8] + _obj_unmodifiable_fields}],
        ["Supplier information", {"fields": _obj_specific_fields[8:]}],
    ]

    # Methods
    def __str__(self):
        return f"{self.id} - {self.name}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # Remove all white spaces from sequence
        self.sequence = "".join(self.sequence.split())
        super().save(force_insert, force_update, using, update_fields)
