from django.conf import settings
from django.db import models

from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    HistoryFieldMixin,
    SaveWithoutHistoricalRecord,
)

from ..shared.models import (
    HistoryDocFieldMixin,
    InfoSheetMaxSizeMixin,
    OwnershipFieldsMixin,
)

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)


class InhibitorDoc(DocFileMixin):
    class Meta:
        verbose_name = "inhibitor document"

    _inline_foreignkey_fieldname = "inhibitor"
    _mixin_props = {
        "destination_dir": "collection/inhibitordoc/",
        "file_prefix": "ibDoc",
        "parent_field_name": "inhibitor",
    }

    inhibitor = models.ForeignKey("Inhibitor", on_delete=models.PROTECT)


class Inhibitor(
    SaveWithoutHistoricalRecord,
    DownloadFileNameMixin,
    InfoSheetMaxSizeMixin,
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "inhibitor"
        verbose_name_plural = "inhibitors"

    _model_abbreviation = "ib"
    _model_upload_to = "collection/inhibitor/"
    _history_array_fields = {"history_documents": InhibitorDoc}

    name = models.CharField("name", max_length=255, blank=False)
    other_names = models.CharField("other names", max_length=255, blank=False)
    target = models.CharField("target", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    catalogue_number = models.CharField("catalogue number", max_length=255, blank=True)
    l_ocation = models.CharField("location", max_length=255, blank=True)
    ic50 = models.CharField("IC50", max_length=255, blank=True)
    amount = models.CharField("amount", max_length=255, blank=True)
    stock_solution = models.CharField("stock solution", max_length=255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    info_sheet = models.FileField(
        "info sheet",
        help_text=f"only .pdf files, max. {FILE_SIZE_LIMIT_MB} MB",
        upload_to=_model_upload_to,
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.id} - {self.name}"
