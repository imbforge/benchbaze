import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.forms import ValidationError
from django.utils.text import capfirst
from simple_history.models import HistoricalRecords


class Storage(models.Model):
    collection = models.OneToOneField(
        "contenttypes.ContentType",
        verbose_name="collection",
        related_name="storage",
        on_delete=models.PROTECT,
        blank=False,
        null=True,
    )
    species = models.ForeignKey(
        "formz.Species",
        verbose_name="species",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    species_risk_group = models.PositiveSmallIntegerField(
        "species risk group", choices=((1, 1), (2, 2)), blank=True, null=True
    )
    mandatory_location = models.BooleanField(
        "Mandatory location?",
        help_text="Whether or not items in this collection must have at least one location assigned",
        default=False,
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "storage location"
        verbose_name_plural = "storage locations"

    def __str__(self):
        return capfirst(self.collection.model_class()._meta.verbose_name)

    def clean(self):
        errors = {}

        requires_species = getattr(
            self.collection.model_class(), "_storage_requires_species", False
        )

        # If the collection requires a species, then it must be set. If it does
        # not require a species, then it must not be set.
        if requires_species and not self.species:
            errors["species"] = [
                f"A species, e.g. {requires_species}, must be set for this collection."
            ]

        if not requires_species and self.species:
            errors["species"] = [
                "This collection does not require a species, leave it blank."
            ]

        if not requires_species and self.species_risk_group:
            errors["species_risk_group"] = [
                "This collection does not require a risk group, leave it blank."
            ]

        if requires_species and self.species and not self.species_risk_group:
            errors["species_risk_group"] = [
                "A risk group must be set if a species is chosen."
            ]

        if errors:
            raise ValidationError(errors)

        return super().clean()


class Location(models.Model):
    _storage_temperature_choices = (
        ("RT", "Room temperature"),
        ("4", "4° C"),
        ("-20", "-20° C"),
        ("-80", "-80° C"),
        ("-150", "-150° C"),
    )
    _storage_format_choices = (
        ("9×9", "9×9 box"),
        ("10×10", "10×10 box"),
        ("96", "96-well plate"),
        ("384", "384-well plate"),
        ("other", "Other"),
    )
    _coordinate_format_choices = (
        (
            "alphanumeric",
            "Alphanumeric (e.g., A1, B3, ..., H12)",
        ),
        ("numeric", "Numeric (e.g., 1, 2, 3, ...)"),
        ("none", "None"),
    )
    _pretty_levels = {1: "❶", 2: "❷", 3: "❸", 4: "❹", 5: "❺"}

    storage = models.ForeignKey(
        "storage", on_delete=models.PROTECT, related_name="locations"
    )
    level = models.PositiveSmallIntegerField(
        "level",
        help_text="Primary, secondary, etc.",
        choices=((1, 1), (2, 2), (3, 3), (4, 4), (5, 5)),
        blank=False,
        null=True,
    )
    name = models.ForeignKey(
        "LocationName",
        verbose_name="location",
        on_delete=models.PROTECT,
        blank=False,
        null=True,
    )
    storage_temperature = models.CharField(
        "storage temperature",
        choices=_storage_temperature_choices,
        max_length=50,
        blank=False,
    )
    storage_format = models.CharField(
        "storage format",
        choices=_storage_format_choices,
        max_length=50,
        blank=False,
    )
    mandatory_position = models.BooleanField(
        "Mandatory position?",
        help_text='Whether or not make the "Box" and "Coordinate" fields mandatory',
        default=False,
    )
    coordinate_format = models.CharField(
        "coordinate format",
        help_text="Whether or not to force coordinates values to match the schema "
        'for the picked storage format. Does not apply to "None". '
        "e.g. A1, B3, ..., H12 for 96-well plates.",
        choices=_coordinate_format_choices,
        max_length=50,
        blank=False,
    )
    description = models.CharField(
        "description",
        max_length=255,
        blank=True,
    )
    active = models.BooleanField("active", default=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "location"
        verbose_name_plural = "locations"
        constraints = [
            models.UniqueConstraint(
                fields=["storage", "level"],
                name="unique_location_level",
                violation_error_message="The level of a location must be unique.",
            )
        ]

    def __str__(self):
        return " | ".join(
            [
                f"{self._pretty_levels.get(self.level, f'({self.level})')}",
                f"{self.name.name}",
                f"{self.get_storage_temperature_display()}",
                f"{self.get_storage_format_display()}",
            ]
        )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.description = self.description.strip()
        super().save(force_insert, force_update, using, update_fields)

    @property
    def formz_label(self):
        return self.name


class LocationName(models.Model):
    name = models.CharField(
        "name",
        max_length=255,
        help_text="A room, a freezer in a room, etc.",
        blank=False,
        unique=True,
    )
    description = models.CharField(
        "description",
        max_length=255,
        blank=True,
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "location name"
        verbose_name_plural = "location names"

    def __str__(self):
        return str(self.name)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.name = self.name.strip()
        self.description = self.description.strip()

        super().save(force_insert, force_update, using, update_fields)


class LocationItem(models.Model):
    content_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.PROTECT
    )
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    location = models.ForeignKey(
        "location", on_delete=models.PROTECT, blank=False, null=True
    )
    box = models.CharField("box", max_length=10, blank=True)
    coordinate = models.CharField(
        "coordinate",
        help_text="For example: A1, B3, ..., P24.",
        max_length=10,
        blank=True,
    )
    comment = models.CharField("comment", max_length=150, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return " | ".join(
            [str(e) for e in [self.location, self.box, self.coordinate] if e]
        )

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def clean(self):
        errors = {}

        if self.location.mandatory_position:
            # Check that box is provided
            if not self.box.strip():
                errors["box"] = errors.get("box", []) + [
                    "Box is required for this location."
                ]

            # Check that coordinate is provided
            if not self.coordinate.strip():
                errors["coordinate"] = errors.get("coordinate", []) + [
                    "Coordinate is required for this location."
                ]

        # Coordinate must be entered if box is provided
        if self.coordinate.strip() and not self.box.strip():
            errors["box"] = errors.get("box", []) + [
                "A value for box must be entered when a coordinate is provided."
            ]

        # Check that coordinate conforms to the expected format
        if self.coordinate.strip():
            # Alphanumeric format
            if self.location.coordinate_format == "alphanumeric":
                pattern = None
                if self.location.storage_format == "96":
                    pattern = r"^[A-H](1[0-2]|[1-9])$"
                elif self.location.storage_format == "384":
                    pattern = r"^([A-P][1-9]|[A-P]1\d|[A-P]2[0-4])$"
                elif self.location.storage_format == "10×10":
                    pattern = r"^[A-J](10|[1-9])$"
                elif self.location.storage_format == "9×9":
                    pattern = r"^[A-I][1-9]$"

                if (
                    pattern
                    and re.match(pattern, self.coordinate.strip().upper()) is None
                ):
                    errors["coordinate"] = errors.get("coordinate", []) + [
                        "Coordinate must be in the correct format for a "
                        f"{self.location.get_storage_format_display()}."
                    ]

            # Numeric format
            elif self.location.coordinate_format == "numeric":
                if not self.coordinate.strip().isnumeric():
                    errors["coordinate"] = errors.get("coordinate", []) + [
                        "Coordinate must be numeric."
                    ]

        if len(errors) > 0:
            raise ValidationError(errors)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.box = self.box.strip()
        self.coordinate = self.coordinate.strip().upper()
        self.comment = self.comment.strip()

        return super().save(force_insert, force_update, using, update_fields)

    @property
    def minimal_str(self):
        return f"({self.location.level}) {self.location.name} {'-'.join([self.box, self.coordinate])}"

    @property
    def formz_label(self):
        return " | ".join(
            [str(e) for e in [self.location.name, self.box, self.coordinate] if e]
        )
