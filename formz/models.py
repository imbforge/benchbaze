from django.conf import settings
from django.db import models
from django.forms import ValidationError
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from import_export.fields import Field as ImportExportField

AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class NucleicAcidPurity(models.Model):
    class Meta:
        verbose_name = "nuclei acid purity"
        verbose_name_plural = "nuclei acid purities"
        ordering = [
            "english_name",
        ]

    english_name = models.CharField("English name", max_length=255, blank=False)
    german_name = models.CharField("German name", max_length=255, blank=False)

    def __str__(self):
        return str(self.english_name)


class NucleicAcidRisk(models.Model):
    class Meta:
        verbose_name = "nuclei acid risk potential"
        verbose_name_plural = "nuclei acid risk potentials"
        ordering = [
            "english_name",
        ]

    english_name = models.CharField("English name", max_length=255, blank=False)
    german_name = models.CharField("German name", max_length=255, blank=False)

    def __str__(self):
        return str(self.english_name)


class GenTechMethod(models.Model):
    class Meta:
        verbose_name = "genTech method"
        verbose_name_plural = "genTech methods"
        ordering = [
            "english_name",
        ]

    english_name = models.CharField("English name", max_length=255, blank=False)
    german_name = models.CharField("German name", max_length=255, blank=False)

    def __str__(self):
        return str(self.english_name)


class Project(models.Model):
    class Meta:
        verbose_name = "project"
        verbose_name_plural = "projects"
        ordering = [
            "id",
        ]

    title = models.CharField(
        "title", help_text="<i>Titel</i>", max_length=255, blank=False
    )
    short_title = models.CharField(
        "short title", help_text="<i>Kurzer Titel</i>", max_length=255, blank=False
    )
    short_title_english = models.CharField(
        "English short title", max_length=255, blank=False
    )
    parent_project = models.ForeignKey(
        "self",
        verbose_name="parent project",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    safety_level = models.PositiveSmallIntegerField(
        "safety level",
        help_text="<i>Sicherheitsstufe</i>",
        choices=((1, 1), (2, 2)),
        blank=False,
        null=True,
    )
    project_leader = models.ManyToManyField(
        AUTH_USER_MODEL,
        verbose_name="project leaders",
        related_name="formz_project_leader",
        help_text="<i>Projektleiter</i>",
        blank=False,
    )
    deputy_project_leader = models.ManyToManyField(
        AUTH_USER_MODEL,
        verbose_name="deputy project leaders",
        related_name="formz_deputy_project_leader",
        help_text="<i>Stellvertretende Projektleiter</i>",
        blank=True,
    )
    objectives = models.CharField(
        "objectives of strategy",
        help_text="<i>Zielsetzung</i>",
        max_length=255,
        blank=True,
    )
    description = models.TextField(
        "Description of strategy/performance",
        help_text="Techniques, organisms, plasmids, etc. "
        "<i>Beschreibung der Durchführung</i>",
        blank=True,
    )
    donor_organims = models.CharField(
        "donor organisms",
        help_text="Used organisms, their risk group and safety-relevant properties. "
        "<i>Verwendete Spenderorganismen</i>",
        max_length=255,
        blank=True,
    )
    potential_risk_nuc_acid = models.TextField(
        "potential risks of transferred nucleic acids",
        help_text="Include safety-relevant properties. "
        "<i>Gefährdungspotentiale der übertragenen Nukleinsäuren</i>",
        blank=True,
    )
    vectors = models.TextField(
        "Vectors", help_text="Include safety-relevant properties", blank=True
    )
    recipient_organisms = models.CharField(
        "recipient organisms",
        help_text="Include risk groups and safety-relevant properties. "
        "<i>Verwendete Empfängerorganismen</i>",
        max_length=255,
        blank=True,
    )
    generated_gmo = models.TextField(
        "generated GMOs",
        help_text="Include risk groups and safety-relevant properties. "
        "<i>Erzeugte GVO</i>",
        blank=True,
    )
    hazard_activity = models.TextField(
        "hazard-relevant characteristics of activity",
        help_text="<i>Gefährdungsrelevante Merkmale der Tätigkeit</i>",
        blank=True,
    )
    hazards_employee = models.TextField(
        "severity and likelihood of hazards to employees and/or the environment",
        help_text="<i>Schwere und Wahrscheinlichkeit einer Gefährdung der "
        "Mitarbeiter und/oder der Umwelt</i>",
        blank=True,
    )
    beginning_work_date = models.DateField(
        "beginning of work",
        help_text="<i>Beginn der Arbeiten</i>",
        blank=False,
        null=True,
    )
    end_work_date = models.DateField(
        "end of work", help_text="<i>Ende der Arbeiten</i>", blank=True, null=True
    )
    genetic_work_classification = models.CharField(
        "classification of genetic work",
        help_text="<i>Einstufung der gentechnischen Arbeiten</i>",
        max_length=255,
        blank=True,
    )
    users = models.ManyToManyField(
        AUTH_USER_MODEL,
        related_name="formz_project_users",
        blank=True,
        through="ProjectUser",
    )

    def __str__(self):
        return str(self.short_title_english)

    def clean(self):
        errors = {}

        if '"' in self.short_title or '"' in self.short_title_english:
            errors["short_title"] = (
                'Double air quotes (") are not allowed in this field'
            )

        if errors:
            raise ValidationError(errors)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # Remove any leading and trailing white spaces
        if self.short_title:
            self.short_title = self.short_title.strip()
        if self.short_title_english:
            self.short_title_english = self.short_title_english.strip()

        super().save(force_insert, force_update, using, update_fields)


class ProjectUser(models.Model):
    formz_project = models.ForeignKey(
        "Project", verbose_name="formZ project", on_delete=models.PROTECT
    )
    user = models.ForeignKey(
        AUTH_USER_MODEL, verbose_name="user", on_delete=models.PROTECT
    )
    beginning_work_date = models.DateField("beginning of work", blank=True, null=True)
    end_work_date = models.DateField("end of work", blank=True, null=True)


class ZkbsPlasmid(models.Model):
    class Meta:
        verbose_name = "ZKBS plasmid"
        verbose_name_plural = "ZKBS plasmids"
        ordering = [
            "name",
        ]

    name = models.CharField("name", max_length=255, blank=False)
    source = models.CharField("source", max_length=255, blank=False)
    purpose = models.CharField("purpose", max_length=255, blank=False)
    description = models.TextField("description", blank=True)

    def __str__(self):
        return str(self.name)


class ZkbsOncogene(models.Model):
    class Meta:
        verbose_name = "ZKBS oncogene"
        verbose_name_plural = "ZKBS oncogenes"
        ordering = [
            "name",
        ]

    name = models.CharField("name", max_length=255, blank=False)
    synonym = models.CharField("synonym", max_length=255)
    species = models.CharField("species", max_length=255, blank=False)
    risk_potential = models.CharField("risk potential", max_length=255, blank=False)
    reference = models.TextField("description")
    additional_measures = models.BooleanField("additional measures?", blank=True)

    def __str__(self):
        return str(self.name)


class ZkbsCellLine(models.Model):
    class Meta:
        verbose_name = "ZKBS cell line"
        verbose_name_plural = "ZKBS cell lines"
        ordering = [
            "name",
        ]

    name = models.CharField("name", max_length=255, blank=False)
    synonym = models.CharField("synonym", max_length=255, blank=True)
    organism = models.CharField("organism", max_length=255, blank=False)
    risk_potential = models.CharField("risk potential", max_length=255, blank=False)
    origin = models.CharField("origin", max_length=255)
    virus = models.CharField("virus", max_length=255)
    genetically_modified = models.BooleanField("genetically modified?", blank=True)

    def __str__(self):
        return str(self.name)


class Species(models.Model):
    class Meta:
        verbose_name = "species"
        verbose_name_plural = "species"
        ordering = ["latin_name", "common_name"]

    latin_name = models.CharField(
        "latin name",
        help_text="Use FULL latin name, e.g. Homo sapiens",
        max_length=255,
        blank=True,
    )
    common_name = models.CharField("common name", max_length=255, blank=True)
    risk_group = models.PositiveSmallIntegerField(
        "risk group", choices=((1, 1), (2, 2), (3, 3), (4, 4)), blank=False, null=True
    )
    name_for_search = models.CharField(max_length=255, null=False, unique=True)
    show_in_cell_line_collection = models.BooleanField(
        "show as organism in cell line collection?", default=False
    )

    @property
    def display_name(self):
        return self.latin_name if self.latin_name else self.common_name

    @property
    def name_formatted(self):
        return (
            format_html("<i>{}</i>", self.latin_name)
            if self.latin_name
            else self.common_name
        )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # Remove any leading and trailing white spaces
        if self.latin_name:
            self.latin_name = self.latin_name.strip()
        if self.common_name:
            self.common_name = self.common_name.strip()

        self.name_for_search = self.latin_name if self.latin_name else self.common_name

        super().save(force_insert, force_update, using, update_fields)

    def clean(self):
        errors = []

        if not self.latin_name and not self.common_name:
            errors.append(
                ValidationError("You must enter either a latin name or a common name")
            )

        if len(errors) > 0:
            raise ValidationError(errors)

    def __str__(self):
        return (
            "{} - RG {}".format(self.name_for_search, self.risk_group)
            if self.risk_group
            else self.name_for_search
        )


class SequenceFeature(models.Model):
    class Meta:
        verbose_name = "sequence feature"
        verbose_name_plural = "sequence features"
        ordering = [
            "name",
        ]

    _show_in_frontend = True

    name = models.CharField(
        "name",
        max_length=255,
        help_text="This is only the name displayed in the rendered FormZ form. "
        "It is NOT used for auto-detection of features in a plasmid map, only "
        "aliases (below) are used for that. Duplicates are allowed, therefore, "
        "instead of using, for example, 'Hs EXO1', use 'EXO1'",
        blank=False,
    )
    donor_organism = models.ManyToManyField(
        Species,
        verbose_name="donor organism",
        help_text="Choose none, for artificial elements",
        blank=False,
    )
    nuc_acid_purity = models.ForeignKey(
        "NucleicAcidPurity",
        verbose_name="nucleic acid purity",
        on_delete=models.PROTECT,
        blank=False,
        null=True,
    )
    nuc_acid_risk = models.ForeignKey(
        "NucleicAcidRisk",
        verbose_name="nucleic acid risk potential",
        on_delete=models.PROTECT,
        blank=False,
        null=True,
    )
    zkbs_oncogene = models.ForeignKey(
        "ZkbsOncogene",
        verbose_name="ZKBS database oncogene",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        help_text='<a href="/formz/zkbsoncogene/" target="_blank">View</a>',
    )
    description = models.TextField("description", blank=True)
    common_feature = models.BooleanField(
        "is this a common plasmid feature?",
        help_text="e.g. an antibiotic resistance marker or a commonly used promoter",
        default=False,
        blank=False,
    )

    _search_fields = [
        "id",
        "name",
    ]
    _api_list_fields = [
        "id",
        "name",
        "donor_species_names_formatted",
        "donor_species_risk_groups",
        "nuc_acid_risk_formatted",
    ]

    _api_item_fields = [
        "id",
        "name",
        "donor_organism",
        "nuc_acid_purity",
        "nuc_acid_risk",
        "zkbs_oncogene",
        "description",
        "common_feature",
        "donor_species_names_formatted",
        "donor_species_risk_groups",
        "donor_species_max_risk_group",
        "nuc_acid_risk_formatted",
        "nuc_acid_purity_formatted",
        "zkbs_oncogene_formatted",
    ]

    _export_field_names = (
        "id",
        "name",
        "donor_species_custom_field",
        "nuc_acid_purity_custom_field",
        "nuc_acid_risk_custom_field",
        "zkbs_oncogene_custom_field",
        "description",
        "common_feature_custom_field",
    )
    _export_custom_fields = {
        "fields": {
            "donor_species_custom_field": ImportExportField(
                column_name="Donor species"
            ),
            "nuc_acid_purity_custom_field": ImportExportField(
                column_name="Nucleic acid purity",
                attribute="nuc_acid_purity__english_name",
            ),
            "nuc_acid_risk_custom_field": ImportExportField(
                column_name="Nucleic acid risk", attribute="nuc_acid_risk__english_name"
            ),
            "zkbs_oncogene_custom_field": ImportExportField(
                column_name="ZKBS Oncogene", attribute="zkbs_oncogene__name"
            ),
            "common_feature_custom_field": ImportExportField(
                column_name="Common feature"
            ),
        },
        "dehydrate_methods": {
            "donor_species_custom_field": lambda obj: ", ".join(
                [s.display_name for s in obj.donor_organism.all()]
            ),
            "common_feature_custom_field": lambda obj: (
                "True" if obj.common_feature else "False"
            ),
        },
    }

    def __str__(self):
        return (
            str(self.name)
            if self.common_feature
            else f"{self.name} - {self.donor_organism.first().name_for_search}"
        )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.name = self.name.strip()
        super().save(force_insert, force_update, using, update_fields)

    def donor_species_names_formatted(self):
        species_names = [s.name_formatted for s in self.donor_organism.all()]
        try:
            species_names.remove("none")
        except Exception:
            pass
        return mark_safe(", ".join(species_names))

    donor_species_names_formatted.use_api = True
    donor_species_names_formatted.field_type = models.CharField

    def donor_species_risk_groups(self):
        species_risk_groups = []
        for species in self.donor_organism.all():
            if species.risk_group:
                species_risk_groups.append(species.risk_group)

        return ", ".join([str(i) for i in species_risk_groups])

    donor_species_risk_groups.use_api = True
    donor_species_risk_groups.field_type = models.CharField

    def donor_species_max_risk_group(self):
        species_risk_groups = [0]
        for species in self.donor_organism.all():
            if species.risk_group:
                species_risk_groups.append(species.risk_group)

        return max(species_risk_groups)

    donor_species_max_risk_group.use_api = True
    donor_species_max_risk_group.field_type = models.IntegerField

    def get_admin_change_url(self):
        return reverse("admin:formz_sequencefeature_change", args=[self.id])

    def nuc_acid_risk_formatted(self):
        return self.nuc_acid_risk.english_name if self.nuc_acid_risk else ""

    nuc_acid_risk_formatted.use_api = True
    nuc_acid_risk_formatted.field_type = models.CharField

    def zkbs_oncogene_formatted(self):
        return self.zkbs_oncogene.name if self.zkbs_oncogene else ""

    zkbs_oncogene_formatted.use_api = True
    zkbs_oncogene_formatted.field_type = models.CharField

    def nuc_acid_purity_formatted(self):
        return self.nuc_acid_purity.english_name if self.nuc_acid_purity else ""

    nuc_acid_purity_formatted.use_api = True
    nuc_acid_purity_formatted.field_type = models.CharField


class SequenceFeatureAlias(models.Model):
    class Meta:
        verbose_name = "sequence feature alias"
        verbose_name_plural = "sequence feature aliases"
        ordering = [
            "label",
        ]

    label = models.CharField("alias", max_length=255, blank=True, unique=True)
    sequence_feature = models.ForeignKey(
        "SequenceFeature", on_delete=models.PROTECT, related_name="alias"
    )

    def __str__(self):
        return str(self.label)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.label = self.label.strip()
        super().save(force_insert, force_update, using, update_fields)


class Header(models.Model):
    class Meta:
        verbose_name = "header"
        verbose_name_plural = "headers"

    operator = models.CharField(
        "operator", max_length=255, help_text="Name des Betreibers", blank=False
    )
    address = models.TextField(
        "address of bioengineering facility",
        help_text="Anschrift der gentechnischen Anlage",
        blank=False,
    )
    name_biosafety_officer = models.CharField(
        "name of the biosafety officer",
        max_length=255,
        help_text="Name des Beauftragten für die Biologische Sicherheit",
        blank=False,
    )

    s1_approval_file_num = models.CharField(
        "file number for S1 approval",
        max_length=255,
        help_text="e.g. 21-29,8 B 56.01; TgbNr.: 8/29,0/11/36",
        blank=False,
    )
    s1_approval_date = models.DateField("S1 approval date", blank=False, null=True)
    s2_approval_file_num = models.CharField(
        "file number for S2 approval",
        max_length=255,
        help_text="e.g. 29,8 B 56.02:21; TgbNr.: 8/29,0/13/46",
        blank=False,
    )
    s2_approval_date = models.DateField("S2 approval date", blank=False, null=True)

    def __str__(self):
        return str(self.operator)
