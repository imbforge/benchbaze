from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.actions import export_tsv_action, export_xlsx_action
from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    HistoryFieldMixin,
    SaveWithoutHistoricalRecord,
)
from formz.models import SequenceFeature

from ..shared.models import (
    ApprovalFieldsMixin,
    HistoryDocFieldMixin,
    InfoSheetMaxSizeMixin,
    OwnershipFieldsMixin,
)

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)


class OligoDoc(DocFileMixin):
    class Meta:
        verbose_name = "oligo document"

    _inline_foreignkey_fieldname = "oligo"
    _mixin_props = {
        "destination_dir": "collection/oligodoc/",
        "file_prefix": "oDoc",
        "parent_field_name": "oligo",
    }

    oligo = models.ForeignKey("Oligo", on_delete=models.PROTECT)


class Oligo(
    SaveWithoutHistoricalRecord,
    DownloadFileNameMixin,
    InfoSheetMaxSizeMixin,
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "oligo"
        verbose_name_plural = "oligos"

    _model_upload_to = "collection/oligo/"

    # Fields
    name = models.CharField("name", max_length=255, unique=True, blank=False)
    sequence = models.CharField(
        "sequence",
        max_length=2048,
        unique=True,
        db_collation="case_insensitive",
        blank=False,
    )
    length = models.SmallIntegerField("length", null=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    gene = models.CharField("gene", max_length=255, blank=True)
    restriction_site = models.CharField("restriction sites", max_length=255, blank=True)
    description = models.TextField("description", blank=True)
    comment = models.CharField("comments", max_length=255, blank=True)
    info_sheet = models.FileField(
        "info sheet",
        help_text=f"only .pdf files, max. {FILE_SIZE_LIMIT_MB} MB",
        upload_to=_model_upload_to,
        blank=True,
        null=True,
    )

    sequence_features = models.ManyToManyField(
        SequenceFeature,
        verbose_name="elements",
        related_name="%(class)s_sequence_features",
        blank=True,
    )
    history_sequence_features = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="formz elements",
        blank=True,
        null=True,
        default=list,
    )

    approval_user = None

    # Static properties
    _model_abbreviation = "o"
    _show_in_frontend = True
    _is_guarded_model = False
    _show_formz = False
    _history_array_fields = {
        "history_sequence_features": SequenceFeature,
        "history_documents": OligoDoc,
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
    _list_display = [
        "sequence_formatted",
        "restriction_site",
        "created_by",
        "approval_formatted",
    ]
    _export_field_names = [
        "id",
        "name",
        "sequence",
        "us_e",
        "gene",
        "restriction_site",
        "description",
        "comment",
        "created_date_time",
        "created_by",
    ]
    _actions = [
        export_xlsx_action,
        export_tsv_action,
    ]

    _autocomplete_fields = ["sequence_features"]
    _clone_ignore_fields = [
        "info_sheet",
    ]
    _obj_specific_fields = [
        "name",
        "sequence",
        "us_e",
        "gene",
        "restriction_site",
        "description",
        "comment",
        "info_sheet",
        "sequence_features",
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
            {"fields": _obj_specific_fields},
        ],
    ]
    _change_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields},
        ],
        [
            "Metadata",
            {"fields": _obj_unmodifiable_fields},
        ],
    ]

    # Methods
    def __str__(self):
        return f"{self.id} - {self.name}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # Remove all white spaces from sequence and set its length
        self.sequence = "".join(self.sequence.split())
        self.length = len(self.sequence)

        super().save(force_insert, force_update, using, update_fields)

    def sequence_formatted(self):
        if self.sequence:
            if len(self.sequence) <= 75:
                return self.sequence
            else:
                return self.sequence[0:75] + "..."

    sequence_formatted.short_description = sequence.name
    sequence_formatted.field_type = sequence.get_internal_type()
