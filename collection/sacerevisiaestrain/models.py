import random
from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.forms import ValidationError
from import_export.fields import Field

from common.actions import export_tsv_action, export_xlsx_action
from common.models import DocFileMixin, HistoryFieldMixin, SaveWithoutHistoricalRecord
from formz.actions import formz_as_html
from formz.models import GenTechMethod, SequenceFeature
from formz.models import Project as FormZProject

from common.models import (
    DocFileMixin,
    EnhancedModelCleanMixin,
    HistoryFieldMixin,
    SaveWithoutHistoricalRecord,
    ZebraLabelFieldsMixin,
)

from ..plasmid.models import Plasmid
from ..shared.models import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryPlasmidsFieldsMixin,
    LocationMixin,
    OwnershipFieldsMixin,
)


class SaCerevisiaeStrainDoc(DocFileMixin):
    _inline_foreignkey_fieldname = "sacerevisiae_strain"
    _mixin_props = {
        "destination_dir": "collection/sacerevisiaestraindoc/",
        "file_prefix": "scDoc",
        "parent_field_name": "sacerevisiae_strain",
    }

    sacerevisiae_strain = models.ForeignKey(
        "SaCerevisiaeStrain", on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = "sa. cerevisiae strain document"


CEREVISIAE_MATING_TYPE_CHOICES = (
    ("a", "a"),
    ("alpha", "alpha"),
    ("unknown", "unknown"),
    ("a/a", "a/a"),
    ("alpha/alpha", "alpha/alpha"),
    ("a/alpha", "a/alpha"),
    ("other", "other"),
)


class SaCerevisiaeStrain(
    EnhancedModelCleanMixin,
    ZebraLabelFieldsMixin,
    SaveWithoutHistoricalRecord,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryPlasmidsFieldsMixin,
    HistoryFieldMixin,
    LocationMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "strain - Sa. cerevisiae"
        verbose_name_plural = "strains - Sa. cerevisiae"

    _model_abbreviation = "sc"
    _history_array_fields = {
        "history_integrated_plasmids": Plasmid,
        "history_cassette_plasmids": Plasmid,
        "history_episomal_plasmids": Plasmid,
        "history_all_plasmids_in_stocked_strain": Plasmid,
        "history_formz_projects": FormZProject,
        "history_formz_gentech_methods": GenTechMethod,
        "history_sequence_features": SequenceFeature,
        "history_documents": SaCerevisiaeStrainDoc,
    }
    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + OwnershipFieldsMixin._history_view_ignore_fields
    )
    _m2m_save_ignore_fields = ["history_all_plasmids_in_stocked_strain"]

    name = models.CharField("name", max_length=255, blank=False)
    relevant_genotype = models.CharField(
        "relevant genotype", max_length=255, blank=False
    )
    mating_type = models.CharField(
        "mating type", choices=CEREVISIAE_MATING_TYPE_CHOICES, max_length=20, blank=True
    )
    chromosomal_genotype = models.TextField("chromosomal genotype", blank=True)
    parent_1 = models.ForeignKey(
        "self",
        verbose_name="Parent 1",
        on_delete=models.PROTECT,
        related_name="%(class)s_parent_1",
        help_text="Main parental strain",
        blank=True,
        null=True,
    )
    parent_2 = models.ForeignKey(
        "self",
        verbose_name="Parent 2",
        on_delete=models.PROTECT,
        related_name="%(class)s_parent_2",
        help_text="Only for crosses",
        blank=True,
        null=True,
    )
    parental_strain = models.CharField(
        "parental strain",
        help_text="Use only when 'Parent 1' does not apply",
        max_length=255,
        blank=True,
    )
    construction = models.TextField("construction", blank=True)
    modification = models.CharField("modification", max_length=255, blank=True)
    integrated_plasmids = models.ManyToManyField(
        "Plasmid", related_name="%(class)s_integrated_plasmids", blank=True
    )
    cassette_plasmids = models.ManyToManyField(
        "Plasmid",
        related_name="%(class)s_cassette_plasmids",
        help_text="Tagging and knock out plasmids",
        blank=True,
    )
    episomal_plasmids = models.ManyToManyField(
        "Plasmid",
        related_name="%(class)s_episomal_plasmids",
        blank=True,
        through="SaCerevisiaeStrainEpisomalPlasmid",
    )
    plasmids = models.CharField(
        "plasmids",
        max_length=255,
        help_text="Use only when the other plasmid fields do not apply",
        blank=True,
    )
    selection = models.CharField("selection", max_length=255, blank=True)
    phenotype = models.CharField("phenotype", max_length=255, blank=True)
    background = models.CharField("background", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    note = models.CharField("note", max_length=255, blank=True)
    reference = models.CharField("reference", max_length=255, blank=True)

    history_documents = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="documents",
        blank=True,
        null=True,
        default=list,
    )

    # Static properties
    _model_abbreviation = "sc"
    _show_in_frontend = "Strains - <em>Sa. cerevisiae</em>"
    _frontend_verbose_name = "Strain - <em>Sa. cerevisiae</em>"
    _frontend_verbose_plural = _show_in_frontend
    _history_array_fields = {
        "history_integrated_plasmids": Plasmid,
        "history_cassette_plasmids": Plasmid,
        "history_episomal_plasmids": Plasmid,
        "history_all_plasmids_in_stocked_strain": Plasmid,
        "history_formz_projects": FormZProject,
        "history_formz_gentech_methods": GenTechMethod,
        "history_sequence_features": SequenceFeature,
        "history_documents": SaCerevisiaeStrainDoc,
    }
    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + OwnershipFieldsMixin._history_view_ignore_fields
    )
    _m2m_save_ignore_fields = ["history_all_plasmids_in_stocked_strain"]
    _representation_field = "name"
    _list_display_links = ["id"]
    _search_fields = [
        "id",
        "name",
    ]
    _list_display_frozen = _search_fields
    _list_display = [
        "mating_type",
        "background",
        "created_by",
        "approval_formatted",
    ]
    _export_field_names = [
        "id",
        "name",
        "relevant_genotype",
        "mating_type",
        "chromosomal_genotype",
        "parent_1",
        "parent_2",
        "additional_parental_strain_info",
        "construction",
        "modification",
        "integrated_plasmids",
        "cassette_plasmids",
        "episomal_plasmids_in_stock",
        "other_plasmids",
        "selection",
        "phenotype",
        "background",
        "received_from",
        "us_e",
        "note",
        "reference",
        "created_date_time",
        "created_by",
    ]
    _export_custom_fields = {
        "fields": {
            "episomal_plasmids_in_stock": Field(
                column_name="Episomal plasmids in stock"
            ),
            "other_plasmids": Field(
                attribute="plasmids", column_name="Other plasmid info"
            ),
            "additional_parental_strain_info": Field(
                attribute="parental_strain",
                column_name="Extra parental strain info",
            ),
        },
        "dehydrate_methods": {
            "episomal_plasmids_in_stock": lambda obj: (
                ",".join(
                    [
                        str(i)
                        for i in obj.episomal_plasmids.filter(
                            sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True
                        ).values_list("id", flat=True)
                    ]
                )
            )
        },
    }
    _actions = [export_xlsx_action, export_tsv_action, formz_as_html]

    _show_formz = True
    _show_plasmids_in_model = True
    _autocomplete_fields = [
        "parent_1",
        "parent_2",
        "integrated_plasmids",
        "cassette_plasmids",
        "formz_projects",
        "formz_gentech_methods",
        "sequence_features",
    ]
    _obj_specific_fields = [
        "name",
        "relevant_genotype",
        "mating_type",
        "chromosomal_genotype",
        "parent_1",
        "parent_2",
        "parental_strain",
        "construction",
        "modification",
        "integrated_plasmids",
        "cassette_plasmids",
        "plasmids",
        "selection",
        "phenotype",
        "background",
        "received_from",
        "us_e",
        "note",
        "reference",
        "formz_projects",
        "formz_risk_group",
        "formz_gentech_methods",
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
            {"fields": _obj_specific_fields[:19]},
        ],
        [
            "FormZ",
            {
                "classes": tuple(),
                "fields": _obj_specific_fields[19:],
            },
        ],
    ]
    _change_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields[:19] + _obj_unmodifiable_fields},
        ],
        [
            "FormZ",
            {"classes": (("collapse",)), "fields": _obj_specific_fields[19:]},
        ],
    ]

    # Methods
    def __str__(self):
        return f"{self.id} - {self.name}"

    @property
    def all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        all_plasmids = (
            (
                self.integrated_plasmids.all()
                | self.cassette_plasmids.all()
                | self.episomal_plasmids.filter(
                    sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True
                )
            )
            .distinct()
            .order_by("id")
        )
        return all_plasmids

    @property
    def all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        all_plasmids = (
            self.sacerevisiaestrainepisomalplasmid_set.filter(
                present_in_stocked_strain=False
            )
            .distinct()
            .order_by("plasmid__id")
        )
        return all_plasmids

    @property
    def all_plasmids_with_maps(self):
        """Returns all plasmids"""
        return (
            (
                self.integrated_plasmids.all()
                | self.episomal_plasmids.all()
                | self.cassette_plasmids.all()
            )
            .distinct()
            .exclude(map="")
            .order_by("id")
        )

    @property
    def all_sequence_features(self):
        elements = super().all_sequence_features
        all_plasmids = self.all_instock_plasmids
        for pl in all_plasmids:
            elements = elements | pl.sequence_features.all()
        return elements.distinct().order_by("name")

    @property
    def plasmids_in_model(self):
        return self.all_instock_plasmids.order_by("id").values_list("id", flat=True)

    @property
    def formz_genotype(self):
        return self.relevant_genotype

    @property
    def zebra_n0jtt_label_content(self):
        labels = super().zebra_n0jtt_label_content
        labels[2] = f"MT: {self.mating_type}"
        return labels


class SaCerevisiaeStrainEpisomalPlasmid(models.Model):
    _inline_foreignkey_fieldname = "sacerevisiae_strain"

    sacerevisiae_strain = models.ForeignKey(
        SaCerevisiaeStrain, on_delete=models.PROTECT
    )
    plasmid = models.ForeignKey(
        "Plasmid", verbose_name="Plasmid", on_delete=models.PROTECT
    )
    present_in_stocked_strain = models.BooleanField(
        "present in -80° C stock?",
        help_text="Check, if the culture you stocked for the -80° C "
        "collection contains an episomal plasmid. Leave unchecked, if "
        "you simply want to record that you have transiently transformed "
        "this strain with an episomal plasmid",
        default=False,
    )
    formz_projects = models.ManyToManyField(
        "formz.Project", related_name="cerevisiae_episomal_plasmid_projects", blank=True
    )
    created_date = models.DateField("created", blank=True, null=True)
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    def clean(self):
        errors = {}

        # Check that a transiently transfected plasmid has a created date
        if not self.present_in_stocked_strain and not self.created_date:
            errors["created_date"] = errors.get("created_date", []) + [
                "Transiently tranformed episomal plasmids must have a created date"
            ]

        if errors:
            raise ValidationError(errors)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # If destroyed date not present and plasmid not in stocked strain,
        # automatically set destroyed date
        if self.present_in_stocked_strain:
            self.created_date = None
            self.destroyed_date = None
        else:
            if not self.destroyed_date and self.created_date:
                self.destroyed_date = self.created_date + timedelta(
                    days=random.randint(7, 28)
                )

        super().save(force_insert, force_update, using, update_fields)

    def is_highlighted(self):
        return self.present_in_stocked_strain
