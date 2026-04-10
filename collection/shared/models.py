import base64
import os
from io import BytesIO, StringIO
from urllib.parse import urlencode

from Bio import SeqIO
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.base import ModelBase
from django.forms import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
import requests


from approval.models import Approval
from common.actions import export_action_tsv, export_action_xlsx
from common.models import HistoryFieldMixin, SaveWithoutHistoricalRecordMixin
from formz.actions import formz_as_html

from ..storage.models import Location
from .actions import create_n0jtt_zebra_label

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)
OVE_URL = getattr(settings, "OVE_URL", "")
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
MEDIA_URL = settings.MEDIA_URL
AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class ApprovalFieldsMixin(models.Model):
    """Common approval fields"""

    class Meta:
        abstract = True

    # Fields
    created_approval_by_pi = models.BooleanField(
        "record creation approval", default=False
    )
    last_changed_approval_by_pi = models.BooleanField(
        "record change approval", default=None, null=True
    )
    approval_by_pi_date_time = models.DateTimeField(null=True, default=None)
    approval = GenericRelation(Approval)
    approval_user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name="%(class)s_approval_user",
        on_delete=models.PROTECT,
        null=True,
    )

    # Static properties
    _history_view_ignore_fields = [
        "created_approval_by_pi",
        "last_changed_approval_by_pi",
        "approval_by_pi_date_time",
        "approval_formatted",
        "approval_user",
    ]

    def approval_formatted(self):
        """Shows whether record has been approved or not"""

        if self.last_changed_approval_by_pi is not None:
            return self.last_changed_approval_by_pi
        else:
            return self.created_approval_by_pi

    approval_formatted.short_description = "Approval"
    approval_formatted.boolean = True
    approval_formatted.field_type = "BooleanField"


class OwnershipFieldsMixin(models.Model):
    """Common ownership fields"""

    class Meta:
        abstract = True

    # Ownership Fields
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    created_by = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name="%(class)s_createdby_user",
        on_delete=models.PROTECT,
    )

    # Static properties
    _history_view_ignore_fields = [
        "created_date_time",
        "last_changed_date_time",
    ]

    def readonly_fields(self, request):
        """Returns readonly fields based on which user is requesting the object"""

        can_change = False

        if request.user == self.created_by or request.user.is_elevated_user:
            can_change = True

        elif getattr(self, "_is_guarded_model", False) and request.user.has_perm(
            f"{self._meta.app_label}.change_{self._meta.model_name}", self
        ):
            can_change = True

        readonly_fields = self._obj_specific_fields + self._obj_unmodifiable_fields
        if can_change:
            readonly_fields = self._obj_unmodifiable_fields

        return readonly_fields


class HistoryDocFieldMixin(models.Model):
    """Common history doc field"""

    class Meta:
        abstract = True

    # Fields
    history_documents = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="documents",
        blank=True,
        null=True,
        default=list,
    )


class HistoryPlasmidsFieldsMixin(models.Model):
    """Common history field to keep information for different
    kinds of plasmids"""

    class Meta:
        abstract = True

    # Fields
    history_integrated_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="integrated plasmid",
        blank=True,
        null=True,
        default=list,
    )
    history_cassette_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="cassette plasmids",
        blank=True,
        null=True,
        default=list,
    )
    history_episomal_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="episomal plasmids",
        blank=True,
        null=True,
        default=list,
    )
    history_all_plasmids_in_stocked_strain = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="all plasmids in stocked strain",
        blank=True,
        null=True,
        default=list,
    )


class FormZFieldsMixin(models.Model):
    """Common FormZ fields"""

    class Meta:
        abstract = True

    _formz_enable = True

    # Fields
    formz_projects = models.ManyToManyField(
        "formz.Project",
        verbose_name="projects",
        related_name="%(class)s_formz_projects",
        blank=False,
    )
    formz_risk_group = models.PositiveSmallIntegerField(
        "risk group", choices=((1, 1), (2, 2)), blank=False, null=True
    )
    formz_gentech_methods = models.ManyToManyField(
        "formz.GenTechMethod",
        verbose_name="genTech methods",
        help_text="The genetic method(s) used to create this record",
        related_name="%(class)s_gentech_methods",
        blank=True,
    )
    sequence_features = models.ManyToManyField(
        "formz.SequenceFeature",
        verbose_name="sequence features",
        help_text="Use only when a feature is not present in the chosen plasmid(s), if any. "
        "Searching against the aliases of a feature is case-sensitive. "
        '<a href="/formz/sequencefeature/" target="_blank">View all/Change</a>',
        related_name="%(class)s_sequence_features",
        blank=True,
    )
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    history_formz_projects = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="formZ projects",
        blank=True,
        null=True,
        default=list,
    )
    history_formz_gentech_methods = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="genTech methods",
        blank=True,
        null=True,
        default=list,
    )
    history_sequence_features = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="formz elements",
        blank=True,
        null=True,
        default=list,
    )

    # Static properties
    _show_formz = True
    _actions = [formz_as_html]

    @property
    def formz_species(self):
        species = None
        if storage := getattr(self, "get_model_storage", lambda: None)():
            species = storage.species
            species.risk_group = storage.species_risk_group
        return species

    @property
    def formz_locations(self):
        return getattr(self, "locations", []) or getattr(
            self.__class__, "get_model_locations", []
        )

    @property
    def formz_s2(self):
        return getattr(self, "s2_work", False) or self.formz_risk_group == 2

    @property
    def formz_s2_plasmids(self):
        return None

    @property
    def formz_transfected(self):
        return False

    @property
    def formz_virus_packaging_cell_line(self):
        return None

    @property
    def formz_genotype(self):
        return getattr(self, "genotype", None)

    @property
    def show_formz(self):
        return self._show_formz


class InfoSheetMaxSizeMixin:
    """Clean method for models that have an info sheet"""

    def info_sheet_formatted(self):
        """Format sheet as <a> html element"""

        if self.info_sheet:
            return format_html(
                '<a class="magnific-popup-iframe-pdflink" href="{}">View</a>',
                self.info_sheet.url,
            )
        else:
            return ""

    info_sheet_formatted.short_description = "Approval"
    info_sheet_formatted.field_type = "FileField"
    info_sheet_formatted.short_description = "Info Sheet"

    def clean_field_info_sheet_max_size(self):
        errors = (
            super().clean_field_info_sheet_max_size()
            if hasattr(super(), "clean_field_info_sheet_max_size")
            else {}
        )
        file_size_limit = FILE_SIZE_LIMIT_MB * 1024 * 1024

        if self.info_sheet:
            # Check if file is bigger than FILE_SIZE_LIMIT_MB
            if self.info_sheet.size > file_size_limit:
                errors["info_sheet"] = errors.get("info_sheet", []) + [
                    f"File too large. Size cannot exceed {FILE_SIZE_LIMIT_MB} MB."
                ]

            # Check if file's extension is '.pdf'
            try:
                info_sheet_ext = os.path.splitext(self.info_sheet.name)[1].lower()
            except Exception:
                info_sheet_ext = None
            if info_sheet_ext is None or info_sheet_ext != "pdf":
                errors["info_sheet"] = errors.get("info_sheet", []) + [
                    "Invalid file format. Please select a valid .pdf file"
                ]

        return errors


class NameUniqueCheckMixin:
    """Mixin for checking uniqueness of the 'name' field"""

    def clean_field_name(self):
        errors = (
            super().clean_field_name() if hasattr(super(), "clean_field_name") else {}
        )

        # Check if an object with this name already exists.
        # We exclude the current instance (self.pk) so we don't block updates
        # Use this instead of a unique constraint on the name field, as done in
        # most models, to account for initial import scenarios where duplicate
        # names exist
        duplicate_exists = (
            self.__class__.objects.filter(name=self.name).exclude(pk=self.pk).exists()
        )

        if duplicate_exists:
            errors["name"] = [
                capfirst(
                    f"{self._meta.verbose_name} with this {self._meta.get_field('name').verbose_name} already exists."
                )
            ]

        return errors


class MapFileCheckPropertiesMixin:
    """Clean method and common properties for models that have a map sheet"""

    def clean_field_map_file(self):
        errors = (
            super().clean_field_map_file()
            if hasattr(super(), "clean_field_map_file")
            else {}
        )

        file_size_limit = FILE_SIZE_LIMIT_MB * 1024 * 1024
        valid_extensions = [".dna", ".gbk", ".gb"]

        # Get the saved object from the database to compare file fields and only validate
        # if the file has changed, avoiding unnecessary validation
        saved_obj = None
        if self.pk is not None:
            saved_obj = self.__class__.objects.get(id=self.pk)

        # Check if map_dna file is changed, if so, validate the new file.
        if self.map_dna and self.map_dna.name != getattr(
            getattr(saved_obj, "map_dna", None), "name", None
        ):
            # Check if file is bigger than FILE_SIZE_LIMIT_MB
            if self.map_dna.size > file_size_limit:
                errors["map_dna"] = errors.get("map_dna", []) + [
                    f"The map is too large. Size cannot exceed {FILE_SIZE_LIMIT_MB} MB."
                ]

            # Check file extension is valid
            try:
                map_ext = os.path.splitext(self.map_dna.name)[1].lower()
            except Exception:
                map_ext = None
            if map_ext is None or map_ext not in valid_extensions:
                errors["map_dna"] = errors.get("map_dna", []) + [
                    f"Invalid file format. Allowed extensions are: {', '.join(valid_extensions)}"
                ]
            else:
                try:
                    self.map_dna.open("rb")  # Ensure file handle is open
                    # If the file extension is .dna, check if it's a valid SnapGene file
                    if map_ext == ".dna":
                        # Check if .dna file is a real SnapGene file
                        SeqIO.read(BytesIO(self.map_dna.read()), "snapgene")
                    # If it is .gbk, check if it's a valid GenBank file.
                    elif map_ext in [".gbk", ".gb"]:
                        SeqIO.read(
                            StringIO(self.map_dna.read().decode("utf-8")), "genbank"
                        )
                    else:
                        raise ValidationError("Unsupported file extension.")
                except Exception as e:
                    errors["map_dna"] = errors.get("map_dna", []) + [
                        f"Invalid file format. Please select a valid {map_ext} file. Error: {e}"
                    ]

        return errors

    @property
    def png_map_as_base64(self):
        """Returns html image element for map"""

        png_data = base64.b64encode(open(self.map_png.path, "rb").read()).decode(
            "ascii"
        )
        return str(png_data)

    @property
    def utf8_encoded_gbk(self):
        """Returns a decoded gbk plasmid map"""

        return self.map_gbk.read().decode()

    @property
    def map_ove_url(self):
        """Returns the url to view the a SnapGene file in OVE"""

        params = {
            "file_name": self.map_dna.url,
            "title": self.full_title,
            "file_format": "dna",
        }

        return f"{OVE_URL}?{urlencode(params)}"

    @property
    def find_oligos_map_gbk_ove_url(self):
        """Returns the url to import all oligos into the plasmid map
        and view it in OVE"""

        params = {
            "file_name": f"/{self._meta.app_label}/{self._meta.model_name}/{self.pk}/find_oligos/",
            "title": f"{self.full_title} (imported oligos)",
            "file_format": "gbk",
            "show_oligos": "true",
        }

        return f"{OVE_URL}?{urlencode(params)}"

    @property
    def full_title(self):
        """Returns the full title for the map, used in OVE and as alt text for the image"""

        return f"{self._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{self.__str__()}"

    def map_formatted(self):
        if self.map_dna:
            return mark_safe(
                f'<a class="magnific-popup-iframe-map-dna" title="Map viewer" href="{self.map_ove_url}">⦾</a>'
            )
        else:
            return ""

    map_formatted.short_description = "Map"
    map_formatted.field_type = "FileField"

    # Get features from dna_map

    def _feature_label(self, feature):
        """Prefer label-like qualifiers when available, then fall back to feature type."""

        # Check common label-like qualifiers in order of preference, returning the first one found
        for key in ("label", "gene", "locus_tag", "note"):
            value = feature.qualifiers.get(key)
            if value:
                return str(value[0]).strip()
        return feature.type

    def _extract_location_bounds(self, location):
        """Return (start, end, strand_symbol) for a location, merging parts if needed."""

        if location is None:
            return None

        # If the location has multiple parts (e.g. from a join), take the min start and max
        # end across all parts
        parts = getattr(location, "parts", None)
        if parts and len(parts) > 1:
            start = min(int(part.start) for part in parts)
            end = max(int(part.end) for part in parts)
            strand = location.strand
            if strand is None:
                for part in parts:
                    if part.strand is not None:
                        strand = part.strand
                        break
        # If the location has no parts, just take its start and end
        else:
            start = int(location.start)
            end = int(location.end)
            strand = location.strand
        # Convert strand to symbol to be descriptive
        strand_symbol = {1: "+", -1: "-"}.get(strand, "?")
        return (start, end, strand_symbol)

    def _feature_bounds(self, feature):
        """Return (start, end, strand_symbol) for a feature's location, merging parts if needed."""
        return self._extract_location_bounds(feature.location)

    def _is_ignored_feature(self, feature):
        label = self._feature_label(feature).strip().lower()
        ftype = feature.type.strip().lower()
        return label == "source" or ftype == "source" or ftype == "primer_bind"

    def get_map_dna_record(self):
        """Returns a SeqRecord object for the map_dna file, or None if not available or invalid"""
        if not self.map_dna:
            return None
        try:
            name = self.map_dna.name.lower()
            if name.endswith(".dna"):
                return SeqIO.read(self.map_dna.path, "snapgene")
            elif name.endswith((".gbk", ".gb")):
                return SeqIO.read(self.map_dna.path, "genbank")
        except Exception:
            return None

    def get_map_dna_simple_features(self):
        """Returns a list of features in the map_dna file, with each feature represented
        as a tuple of

        (label, type, (start, end, strand_symbol))

        The start and end positions are merged across all parts of the feature if it has
        multiple parts (e.g. from a join). Strand is represented as '+' for forward, '-'
        for reverse, and '?' for unknown or mixed."""

        record = self.get_map_dna_record()

        if record is None:
            return []

        return [
            (self._feature_label(f), f.type, self._extract_location_bounds(f.location))
            for f in record.features
            if not self._is_ignored_feature(f)
        ]

    def get_map_dna_feature_names(self):
        """Return the names of the features in the map_dna file"""

        features = self.get_map_dna_simple_features()
        feature_names = [feature[0].strip() for feature in features]
        return feature_names

    def _covert_map_dna_to_dict(self):
        """Convert the map_dna file to a dictionary format that can be used in the frontend"""

        record = self.get_map_dna_record()
        if record is None:
            return {}

        return {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "sequence": str(record.seq),
            "features": [
                {
                    "type": f.type,
                    "location": [
                        (int(p.start), int(p.end), p.strand) for p in f.location.parts
                    ]
                    if hasattr(f.location, "parts")
                    else (
                        int(f.location.start),
                        int(f.location.end),
                        f.location.strand,
                    ),
                    "qualifiers": f.qualifiers,
                }
                for f in record.features
            ],
            "annotations": record.annotations,
        }

    def convert_map_dna_to_svg(self):
        """Convert the map_dna file to svg format for display in the frontend"""

        if not self.map_dna:
            raise Exception("No map file available to convert")

        # Get the map_dna file as an SVG string from the conversion service
        response = requests.get(
            "http://localhost:3000",
            params={
                "path": self.map_dna.path,
                "title": self.full_title,
            },
        )

        if response.status_code == 200:
            return response.text
        else:
            raise Exception(
                f"Failed to convert the map to SVG. Response: {response.text}"
            )


class CommonCollectionModelPropertiesMixin:
    _backup = True

    @property
    def all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        return []

    @property
    def all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        return []

    @property
    def all_plasmids_with_maps(self):
        """Returns all plasmids with a map"""
        return []

    @property
    def all_sequence_features(self):
        """Returns all features in stocked organism"""

        return self.sequence_features.order_by("name")

    @property
    def all_uncommon_sequence_features(self):
        """Returns all uncommon features in stocked organism"""

        return self.all_sequence_features.filter(common_feature=False)

    @property
    def all_common_sequence_features(self):
        """Returns all common features in stocked organism"""

        return self.all_sequence_features.filter(common_feature=True)

    @property
    def url_admin(self):
        """Returns the url to the admin change page for this record"""

        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=(self.pk,),
        )

    @property
    def all_instock_viruses(self):
        """Returns all viruses present in the stocked organism"""

        return []


class LocationMixin(models.Model):
    class Meta:
        abstract = True

    _storage_requires_species = False

    locations = GenericRelation(
        "collection.LocationItem", related_query_name="%(class)s"
    )

    history_locations = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="locations",
        blank=True,
        null=True,
        default=list,
    )

    @classmethod
    def get_model_locations(cls):
        """Returns all locations for this model class"""
        return Location.objects.filter(
            storage__collection__app_label=cls._meta.app_label,
            storage__collection__model=cls._meta.model_name,
        )

    @classmethod
    def get_model_storage(cls):
        """Returns the storage that has mandatory location for this model class"""
        content_type = ContentType.objects.get_for_model(cls)
        return getattr(content_type, "storage", None)


class ZebraLabelFieldsMixin:
    _actions = [create_n0jtt_zebra_label]

    @property
    def zebra_n0jtt_label_content(self):
        return [
            f"<b>{self._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{self.id}</b>",
            self.name,
            "",
            "",
            str(self.created_by)[:17],
        ]


class AggregateVariableModelMeta(ModelBase):
    """Metaclass to aggregate variables from the class hierarchy, such as _actions.
    Must inherit from ModelBase to ensure Django's model creation process is not disrupted"""

    def __new__(mcs, name, bases, attrs):
        # Ensure that Django's ModelBase does its work first
        cls = super().__new__(mcs, name, bases, attrs)

        # The variables to collect
        vars_to_collect = ["_actions"]

        for var_name in vars_to_collect:
            # Collect the variable from the class and all its bases, starting from the
            # furthest bases (e.g. BaseCollectionModel) to the closest (the actual model
            # class), and concatenate them into a single list
            raw_collection = [
                item
                for base in reversed(cls.__mro__)
                if var_name in base.__dict__
                for item in (
                    base.__dict__[var_name]
                    if isinstance(base.__dict__[var_name], (list, tuple))
                    else [base.__dict__[var_name]]
                )
            ]

            # Use dict.fromkeys to remove duplicates while preserving the order
            setattr(cls, var_name, list(dict.fromkeys(raw_collection)))

        return cls


class BaseCollectionModel(
    SaveWithoutHistoricalRecordMixin,
    OwnershipFieldsMixin,
    HistoryFieldMixin,
    models.Model,
    metaclass=AggregateVariableModelMeta,
):
    """Base model for collection models, with relevant common fields and methods"""

    class Meta:
        abstract = True

    _actions = [export_action_xlsx, export_action_tsv]

    def clean(self):
        """Enhanced clean method to call all methods starting with 'clean_field_'"""

        super().clean()

        errors = [
            func()
            for func_name in dir(self)
            if func_name.startswith("clean_field_")
            and callable(func := getattr(self, func_name))
        ]

        if errors:
            # Combine ValidationError instances
            combined_errors = {}
            for err in errors:
                # If err is a dict, it contains field-specific errors
                if isinstance(err, dict):
                    for field, field_errors in err.items():
                        combined_errors.setdefault(field, []).extend(field_errors)
                # If err is a list, it contains non-field errors
                elif isinstance(err, list):
                    combined_errors.setdefault("__all__", []).extend(err)

            raise ValidationError(combined_errors)

    def clean_field_name(self):
        """Strip spaces from name, not in save(), this ensures that the cleaned
        value is used in form validation and uniqueness checks.
        """
        errors = (
            super().clean_field_name() if hasattr(super(), "clean_field_name") else {}
        )

        if getattr(self, "name", None) is not None and self.name != "":
            self.name = self.name.strip()

        return errors

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if getattr(self, "name", None) is not None and self.name != "":
            self.name = self.name.strip()

        super().save(force_insert, force_update, using, update_fields)
