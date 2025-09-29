from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from import_export.fields import Field

from common.actions import export_tsv_action, export_xlsx_action
from common.models import DocFileMixin, HistoryFieldMixin, SaveWithoutHistoricalRecord
from formz.actions import formz_as_html
from formz.models import GenTechMethod, SequenceFeature, Species
from formz.models import Project as FormZProject

from ..oligo.models import Oligo
from ..plasmid.models import Plasmid
from ..shared.models import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    DnaMapMixin,
    FormZFieldsMixin,
    HistoryDocFieldMixin,
    OwnershipFieldsMixin,
)

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)


class WormStrainAlleleDoc(DocFileMixin):
    class Meta:
        verbose_name = "worm strain allele document"

    _inline_foreignkey_fieldname = "worm_strain_allele"
    _mixin_props = {
        "destination_dir": "collection/wormstrainalleledoc/",
        "file_prefix": "waDoc",
        "parent_field_name": "worm_strain_allele",
    }

    worm_strain_allele = models.ForeignKey("WormStrainAllele", on_delete=models.PROTECT)


class WormStrainAllele(
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    DnaMapMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "allele - Worm"
        verbose_name_plural = "alleles - Worm"

    _model_upload_to = "collection/wormstrainallele/"

    # Fields
    lab_identifier = models.CharField(
        "prefix/Lab identifier",
        max_length=15,
        blank=False,
    )
    typ_e = models.CharField(
        "type",
        choices=(("t", "Transgene"), ("m", "Mutation")),
        max_length=5,
        blank=False,
    )
    transgene = models.CharField(
        "transgene", help_text="Genotype", max_length=255, blank=True
    )
    transgene_position = models.CharField(
        "transgene position", max_length=255, blank=True
    )
    transgene_plasmids = models.ManyToManyField(
        Plasmid,
        verbose_name="transgene plasmids",
        related_name="%(class)s_transgene_plasmids",
        help_text="The plasmid(s) in the transgene",
        blank=True,
    )
    mutation = models.CharField(
        "mutation", help_text="Genotype", max_length=255, blank=True
    )
    mutation_type = models.CharField("mutation type", max_length=255, blank=True)
    mutation_position = models.CharField(
        "mutation position", max_length=255, blank=True
    )
    reference_strain = models.ForeignKey(
        "WormStrain",
        verbose_name="reference strain",
        on_delete=models.PROTECT,
        related_name="%(class)s_reference_strain",
        blank=True,
        null=True,
    )
    made_by_method = models.ForeignKey(
        GenTechMethod,
        verbose_name="made by method",
        related_name="%(class)s_made_by_method",
        help_text="The method used to create the allele",
        on_delete=models.PROTECT,
        blank=False,
    )
    made_by_person = models.CharField("made by person", max_length=255, blank=False)
    made_with_plasmids = models.ManyToManyField(
        Plasmid,
        verbose_name="made with plasmids",
        help_text="The plasmid(s) used to create the transgene/mutation",
        blank=True,
    )
    notes = models.TextField("notes", blank=True)
    map = models.FileField(
        "map (.dna)",
        help_text=f"only SnapGene .dna files, max. {FILE_SIZE_LIMIT_MB} MB",
        upload_to=_model_upload_to + "dna/",
        blank=True,
    )
    map_png = models.ImageField(
        "map (.png)", upload_to=_model_upload_to + "png/", blank=True
    )
    map_gbk = models.FileField(
        "Map (.gbk)",
        upload_to=_model_upload_to + "gbk/",
        help_text=f"only .gbk or .gb files, max. {FILE_SIZE_LIMIT_MB} MB",
        blank=True,
    )
    sequence_features = models.ManyToManyField(
        SequenceFeature,
        verbose_name="elements",
        help_text="Searching against the aliases of a sequence feature is case-sensitive. "
        '<a href="/formz/sequencefeature/" target="_blank">View all/Change</a>',
        blank=True,
    )

    history_sequence_features = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="formz elements",
        blank=True,
        null=True,
        default=list,
    )
    history_made_with_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="made with plasmids",
        blank=True,
        null=True,
        default=list,
    )
    history_transgene_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="transgene plasmids",
        blank=True,
        null=True,
        default=list,
    )

    # Static properties
    _model_abbreviation = "wa"
    german_name = "Allel"
    _history_array_fields = {
        "history_sequence_features": SequenceFeature,
        "history_made_with_plasmids": Plasmid,
        "history_transgene_plasmids": Plasmid,
        "history_documents": WormStrainAlleleDoc,
    }
    _history_view_ignore_fields = OwnershipFieldsMixin._history_view_ignore_fields + [
        "map_png",
        "map_gbk",
    ]
    _search_fields = ["id", "mutation", "transgene"]
    _list_display_frozen = ["id"]
    _list_display = [
        "typ_e",
        "description",
        "map_formatted",
        "created_by",
    ]

    _autocomplete_fields = [
        "sequence_features",
        "made_by_method",
        "reference_strain",
        "transgene_plasmids",
        "made_with_plasmids",
    ]
    _export_field_names = [
        "id",
        "lab_identifier",
        "type",
        "transgene",
        "transgene_position",
        "transgene_plasmids",
        "mutation",
        "mutation_type",
        "mutation_position",
        "reference_strain",
        "made_by_method",
        "made_by_person",
        "made_with_plasmids",
        "notes",
        "created_date_time",
        "created_by",
    ]
    _export_custom_fields = {
        "fields": {
            "made_by_method": Field(column_name="Made by method"),
            "type": Field(column_name="Type"),
        },
        "dehydrate_methods": {
            "made_by_method": lambda obj: obj.made_by_method.english_name,
            "type": lambda obj: obj.get_typ_e_display(),
        },
    }
    _actions = [export_xlsx_action, export_tsv_action, formz_as_html]

    _show_formz = False
    _show_plasmids_in_model = True
    _obj_specific_fields = [
        "lab_identifier",
        "typ_e",
        "transgene",
        "transgene_position",
        "transgene_plasmids",
        "mutation",
        "mutation_type",
        "mutation_position",
        "reference_strain",
        "made_by_method",
        "made_by_person",
        "made_with_plasmids",
        "notes",
        "map",
        "map_png",
        "map_gbk",
        "sequence_features",
    ]
    _obj_unmodifiable_fields = [
        "created_date_time",
        "last_changed_date_time",
        "created_by",
    ]
    _set_readonly_fields = [
        "map_png",
    ]

    # Methods
    def __str__(self):
        return f"{self.lab_identifier}{self.id} - {self.name}"

    @property
    def name(self):
        return self.transgene or self.mutation

    @property
    def download_file_name(self):
        return self.__str__()

    @property
    def plasmids_in_model(self):
        return sorted(
            list(set(self.history_transgene_plasmids + self.history_made_with_plasmids))
        )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.lab_identifier = self.lab_identifier.strip()
        super().save(force_insert, force_update, using, update_fields)


WORM_SPECIES_CHOICES = (
    ("celegans", "Caenorhabditis elegans"),
    ("cbriggsae", "Caenorhabditis briggsae"),
    ("cinopinata", "Caenorhabditis inopinata"),
    ("cjaponica", "Caenorhabditis japonica"),
    ("ppacificus", "Pristionchus pacificus"),
)


class WormStrainDoc(DocFileMixin):
    class Meta:
        verbose_name = "worm strain document"

    _inline_foreignkey_fieldname = "worm_strain"
    _mixin_props = {
        "destination_dir": "collection/wormstraindoc/",
        "file_prefix": "wDoc",
        "parent_field_name": "worm_strain",
    }

    worm_strain = models.ForeignKey("WormStrain", on_delete=models.PROTECT)


class WormStrain(
    SaveWithoutHistoricalRecord,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryFieldMixin,
    HistoryDocFieldMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "strain - Worm"
        verbose_name_plural = "strains - Worm"

    # Fields
    name = models.CharField("name", max_length=255, blank=False)
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
    construction = models.TextField("construction", blank=True)
    outcrossed = models.CharField("outcrossed", max_length=255, blank=True)
    growth_conditions = models.CharField(
        "growth conditions", max_length=255, blank=True
    )
    organism = models.CharField(
        "organism",
        choices=WORM_SPECIES_CHOICES,
        max_length=15,
        default="celegans",
        blank=False,
    )

    integrated_dna_plasmids = models.ManyToManyField(
        Plasmid,
        verbose_name="plasmids",
        related_name="%(class)s_integrated_plasmids",
        blank=True,
    )
    integrated_dna_oligos = models.ManyToManyField(
        Oligo,
        verbose_name="oligos",
        related_name="%(class)s_integrated_oligos",
        blank=True,
    )

    selection = models.CharField("selection", max_length=255, blank=True)
    phenotype = models.TextField("phenotype", blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    note = models.CharField("note", max_length=255, blank=True)
    reference = models.CharField("reference", max_length=255, blank=True)
    at_cgc = models.BooleanField(
        "at CGC?", help_text="Caenorhabditis Genetics Center", blank=True, default=False
    )

    location_freezer1 = models.CharField(
        "location Freezer 1", max_length=255, blank=True
    )
    location_freezer2 = models.CharField(
        "location Freezer 2", max_length=255, blank=True
    )
    location_backup = models.CharField("location Backup", max_length=255, blank=True)
    alleles = models.ManyToManyField(
        WormStrainAllele,
        verbose_name="alleles",
        related_name="%(class)s_alleles",
        blank=True,
    )

    history_integrated_dna_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="integrated plasmids",
        blank=True,
        null=True,
        default=list,
    )
    history_integrated_dna_oligos = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="integrated oligos",
        blank=True,
        null=True,
        default=list,
    )
    history_genotyping_oligos = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="genotyping oligos",
        blank=True,
        null=True,
        default=list,
    )
    history_alleles = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="alleles",
        blank=True,
        null=True,
        default=list,
    )

    # Static properties
    _model_abbreviation = "w"
    _show_in_frontend = True
    _history_array_fields = {
        "history_integrated_dna_plasmids": Plasmid,
        "history_integrated_dna_oligos": Oligo,
        "history_formz_projects": FormZProject,
        "history_formz_gentech_methods": GenTechMethod,
        "history_sequence_features": SequenceFeature,
        "history_genotyping_oligos": Oligo,
        "history_documents": WormStrainDoc,
        "history_alleles": WormStrainAllele,
    }
    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + OwnershipFieldsMixin._history_view_ignore_fields
    )
    _m2m_save_ignore_fields = ["history_genotyping_oligos"]
    _search_fields = [
        "id",
        "name",
    ]
    _export_field_names = [
        "id",
        "name",
        "chromosomal_genotype",
        "parent_1",
        "parent_2",
        "construction",
        "outcrossed",
        "growth_conditions",
        "organism",
        "integrated_dna_plasmids",
        "integrated_dna_oligos",
        "selection",
        "phenotype",
        "received_from",
        "us_e",
        "note",
        "reference",
        "at_cgc",
        "location_freezer1",
        "location_freezer2",
        "location_backup",
        "primers_for_genotyping",
        "created_date_time",
        "created_by",
    ]
    _export_custom_fields = {
        "fields": {
            "primers_for_genotyping": Field(column_name="Primers for genotyping"),
        },
        "dehydrate_methods": {
            "primers_for_genotyping": lambda obj: ",".join(
                [str(i) for i in obj.history_genotyping_oligos]
            ),
        },
    }
    _actions = [export_xlsx_action, export_tsv_action, formz_as_html]
    _list_display_frozen = _search_fields
    _list_display = [
        "chromosomal_genotype",
        "stocked_formatted",
        "created_by",
        "approval_formatted",
    ]
    _show_formz = True
    _show_plasmids_in_model = True
    _autocomplete_fields = [
        "parent_1",
        "parent_2",
        "formz_projects",
        "formz_gentech_methods",
        "sequence_features",
        "alleles",
        "integrated_dna_plasmids",
        "integrated_dna_oligos",
    ]
    _obj_specific_fields = [
        "name",
        "chromosomal_genotype",
        "parent_1",
        "parent_2",
        "construction",
        "outcrossed",
        "growth_conditions",
        "organism",
        "selection",
        "phenotype",
        "received_from",
        "us_e",
        "note",
        "reference",
        "at_cgc",
        "alleles",
        "integrated_dna_plasmids",
        "integrated_dna_oligos",
        "location_freezer1",
        "location_freezer2",
        "location_backup",
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
            {"fields": _obj_specific_fields[:15]},
        ],
        [
            "Integrated DNA",
            {
                "fields": _obj_specific_fields[15:18],
            },
        ],
        [
            "Location",
            {"fields": _obj_specific_fields[18:21]},
        ],
        [
            "FormZ",
            {"fields": _obj_specific_fields[21:]},
        ],
    ]
    _change_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields[:15] + _obj_unmodifiable_fields},
        ],
        [
            "Integrated DNA",
            {
                "fields": _obj_specific_fields[15:18],
            },
        ],
        [
            "Location",
            {"fields": _obj_specific_fields[18:21]},
        ],
        [
            "FormZ",
            {"classes": (("collapse",)), "fields": _obj_specific_fields[21:]},
        ],
    ]

    # Methods
    def __str__(self):
        return f"{self.id} - {self.name}"

    def stocked_formatted(self):
        if any(
            len(s.strip()) > 0
            for s in [
                self.location_freezer1,
                self.location_freezer2,
                self.location_backup,
            ]
        ):
            return True
        return False

    stocked_formatted.use_api = True
    stocked_formatted.field_type = models.BooleanField

    @property
    def all_sequence_features(self):
        """Returns all features in stocked organism"""

        elements = self.sequence_features.all()
        all_plasmids = self.integrated_dna_plasmids.all()
        all_oligos = self.integrated_dna_oligos.all()
        all_alleles = self.alleles.all()
        for pl in all_plasmids:
            elements = elements | pl.sequence_features.all()
        for ol in all_oligos:
            elements = elements | ol.sequence_features.all()
        for al in all_alleles:
            elements = elements | al.sequence_features.all()
        return elements.distinct().order_by("name")

    @property
    def all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        return self.integrated_dna_plasmids.all().distinct().order_by("id")

    @property
    def history_all_plasmids_in_stocked_strain(self):
        """Returns the IDs of the plasmids present in the stocked organism"""

        return self.all_instock_plasmids.values_list("id", flat=True)

    @property
    def all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        return None

    @property
    def all_plasmids_with_maps(self):
        """Returns all plasmids and alleles with a map"""

        return list(
            self.alleles.all().distinct().exclude(map="").order_by("id")
        ) + list(
            self.integrated_dna_plasmids.all().distinct().exclude(map="").order_by("id")
        )

    @property
    def plasmids_in_model(self):
        return self.history_all_plasmids_in_stocked_strain

    @property
    def formz_species(self):
        species = Species(
            latin_name=self.get_organism_display(), risk_group=self.formz_risk_group
        )
        return species

    @property
    def formz_genotype(self):
        return self.chromosomal_genotype

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.name = self.name.strip()
        super().save(force_insert, force_update, using, update_fields)


class WormStrainGenotypingAssay(models.Model):
    class Meta:
        verbose_name = "worm strain genotyping assay"
        verbose_name_plural = "worm strain genotyping assays"

    _inline_foreignkey_fieldname = "worm_strain"

    worm_strain = models.ForeignKey(WormStrain, on_delete=models.PROTECT)
    locus_allele = models.CharField("locus/allele", max_length=255, blank=False)
    oligos = models.ManyToManyField(Oligo, related_name="%(class)s_oligos", blank=False)

    def __str__(self):
        return str(self.id)
