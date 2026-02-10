from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.models import (
    DocFileMixin,
    EnhancedModelCleanMixin,
    HistoryFieldMixin,
    SaveWithoutHistoricalRecord,
)

from ..shared.models import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryDocFieldMixin,
    LocationMixin,
    OwnershipFieldsMixin,
)


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

    _model_abbreviation = "v"
    _history_array_fields = {
        "history_formz_projects": "formz.Project",
        "history_formz_gentech_methods": "formz.GenTechMethod",
        "history_sequence_features": "formz.SequenceFeature",
        "history_helper_plasmids": "collection.Plasmid",
        "history_locations": "collection.LocationItem",
    }

    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + OwnershipFieldsMixin._history_view_ignore_fields
    )

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

    _history_array_fields = VirusBase._history_array_fields.copy()
    _history_array_fields["history_documents"] = "collection.VirusMammalianDoc"

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

    _history_array_fields = VirusBase._history_array_fields.copy()
    _history_array_fields["history_documents"] = "collection.VirusInsectDoc"

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

    @property
    def all_sequence_features(self):
        """Returns all features in an insect virus"""

        elements = (
            super().all_sequence_features
            | self.helper_ecolistrain.all_sequence_features.all().distinct()
        )
        return elements.distinct().order_by("name")
