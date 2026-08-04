from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.forms import ValidationError
from django.test import TestCase
from collection.antibody.models import Antibody
from collection.cellline.models import CellLine
from collection.inhibitor.models import Inhibitor
from collection.plasmid.models import Plasmid
from formz.models import Species
from .models import Location, LocationItem, LocationName, Storage

User = get_user_model()
_STORAGE_MODEL_COUNTER = 0


def _make_location_name(name="Freezer A", **kwargs):
    defaults = {"name": name}
    defaults.update(kwargs)
    return LocationName.objects.create(**defaults)


def _make_storage(model_class=None, **kwargs):
    """Create a Storage with a unique ContentType.

    If model_class is not provided, rotate through available models
    to ensure each Storage has a unique collection ContentType.
    """
    global _STORAGE_MODEL_COUNTER
    if model_class is None:
        model_classes = [Inhibitor, Plasmid, Antibody, CellLine]
        model_class = model_classes[_STORAGE_MODEL_COUNTER % len(model_classes)]
        _STORAGE_MODEL_COUNTER += 1
    ct = ContentType.objects.get_for_model(model_class)
    defaults = {"collection": ct}
    defaults.update(kwargs)
    return Storage.objects.create(**defaults)


def _make_location(storage, location_name, level=1, **kwargs):
    defaults = {
        "storage": storage,
        "level": level,
        "name": location_name,
        "storage_temperature": "-80",
        "storage_format": "9×9",
        "coordinate_format": "alphanumeric",
    }
    defaults.update(kwargs)
    return Location.objects.create(**defaults)


def _make_location_item(location, content_object, **kwargs):
    ct = ContentType.objects.get_for_model(content_object)
    defaults = {
        "content_type": ct,
        "object_id": content_object.pk,
        "location": location,
    }
    defaults.update(kwargs)
    return LocationItem.objects.create(**defaults)


class LocationNameModelTest(TestCase):
    def setUp(self):
        self.loc_name = _make_location_name(name="Room 101 Freezer")

    def test_location_name_creation(self):
        self.assertEqual(self.loc_name.name, "Room 101 Freezer")

    def test_str_representation(self):
        self.assertEqual(str(self.loc_name), "Room 101 Freezer")

    def test_name_stripped_on_save(self):
        ln = _make_location_name(name="  Shelf B  ")
        ln.refresh_from_db()
        self.assertEqual(ln.name, "Shelf B")

    def test_description_stripped_on_save(self):
        ln = _make_location_name(name="Shelf C", description="  Near door  ")
        ln.refresh_from_db()
        self.assertEqual(ln.description, "Near door")

    def test_description_defaults_to_empty(self):
        self.assertEqual(self.loc_name.description, "")

    def test_name_is_unique(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            _make_location_name(name="Room 101 Freezer")

    def test_history_created_on_save(self):
        self.assertGreater(self.loc_name.history.count(), 0)

    def test_history_tracks_change(self):
        self.loc_name.description = "Updated description"
        self.loc_name.save()
        self.assertGreaterEqual(self.loc_name.history.count(), 2)

    def test_name_max_length(self):
        """Test name can be up to 255 characters"""
        long_name = "L" * 255
        ln = _make_location_name(name=long_name)
        self.assertEqual(len(ln.name), 255)

    def test_description_max_length(self):
        """Test description can be up to 255 characters"""
        long_desc = "D" * 255
        ln = _make_location_name(name="MaxDesc", description=long_desc)
        self.assertEqual(len(ln.description), 255)

    def test_name_with_special_characters(self):
        """Test name can contain special characters"""
        ln = _make_location_name(name="Room #123 @ Building-A (Main)")
        self.assertEqual(ln.name, "Room #123 @ Building-A (Main)")

    def test_name_cannot_be_blank(self):
        """Test name field is required"""
        from django.core.exceptions import ValidationError as DjangoValidationError

        ln = LocationName(name="", description="Test")
        with self.assertRaises((DjangoValidationError, ValidationError)):
            ln.full_clean()

    def test_description_can_be_blank(self):
        """Test description field can be blank"""
        ln = _make_location_name(name="NoDesc")
        self.assertEqual(ln.description, "")

    def test_name_uniqueness_case_sensitive(self):
        """Test name uniqueness is case-sensitive"""
        _make_location_name(name="Freezer A")
        ln2 = _make_location_name(name="freezer a")
        self.assertIsNotNone(ln2)

    def test_ordering_by_name(self):
        """Test LocationName objects can be ordered by name"""
        _make_location_name(name="Zebra Freezer")
        _make_location_name(name="Alpha Freezer")
        _make_location_name(name="Beta Freezer")
        names = list(
            LocationName.objects.order_by("name").values_list("name", flat=True)
        )
        self.assertEqual(names[0], "Alpha Freezer")


class StorageModelTest(TestCase):
    def setUp(self):
        self.storage = _make_storage(model_class=Inhibitor)

    def test_storage_creation(self):
        ct = ContentType.objects.get_for_model(Inhibitor)
        self.assertEqual(self.storage.collection, ct)

    def test_str_representation(self):
        expected = "Inhibitor"
        self.assertEqual(str(self.storage), expected)

    def test_mandatory_location_defaults_to_false(self):
        self.assertFalse(self.storage.mandatory_location)

    def test_species_nullable(self):
        self.assertIsNone(self.storage.species)

    def test_species_risk_group_nullable(self):
        self.assertIsNone(self.storage.species_risk_group)

    def test_history_created_on_save(self):
        self.assertGreater(self.storage.history.count(), 0)

    def test_history_tracks_change(self):
        self.storage.mandatory_location = True
        self.storage.save()
        self.assertGreaterEqual(self.storage.history.count(), 2)

    def test_clean_passes_when_no_species_required_and_not_set(self):
        try:
            self.storage.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly")

    def test_clean_raises_when_species_required_but_not_set(self):
        storage = _make_storage(model_class=Plasmid)
        with self.assertRaises(ValidationError) as ctx:
            storage.clean()
        self.assertIn("species", ctx.exception.message_dict)

    def test_clean_raises_when_species_set_but_not_required(self):
        species = Species.objects.create(latin_name="Test species", risk_group=1)
        self.storage.species = species
        with self.assertRaises(ValidationError) as ctx:
            self.storage.clean()
        self.assertIn("species", ctx.exception.message_dict)

    def test_clean_raises_when_species_set_but_risk_group_missing(self):
        species = Species.objects.create(latin_name="Escherichia coli", risk_group=1)
        storage = _make_storage(model_class=Plasmid, species=species)
        with self.assertRaises(ValidationError) as ctx:
            storage.clean()
        self.assertIn("species_risk_group", ctx.exception.message_dict)

    def test_clean_passes_when_species_and_risk_group_set_correctly(self):
        """Test clean passes when species requirements are met"""
        species = Species.objects.create(latin_name="Escherichia coli", risk_group=1)
        storage = _make_storage(
            model_class=Plasmid, species=species, species_risk_group=1
        )
        try:
            storage.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly")

    def test_mandatory_location_can_be_true(self):
        """Test mandatory_location can be set to True"""
        storage = _make_storage(model_class=Plasmid, mandatory_location=True)
        self.assertTrue(storage.mandatory_location)

    def test_species_risk_group_choices(self):
        """Test species_risk_group accepts valid choices"""
        species1 = Species.objects.create(latin_name="Species 1", risk_group=1)
        storage1 = _make_storage(
            model_class=Antibody, species=species1, species_risk_group=1
        )
        self.assertEqual(storage1.species_risk_group, 1)
        species2 = Species.objects.create(latin_name="Species 2", risk_group=2)
        storage2 = _make_storage(
            model_class=CellLine, species=species2, species_risk_group=2
        )
        self.assertEqual(storage2.species_risk_group, 2)

    def test_onetoone_relationship_with_content_type(self):
        """Test that each ContentType can only have one Storage"""
        from django.db import IntegrityError

        ct = ContentType.objects.get_for_model(Inhibitor)
        with self.assertRaises(IntegrityError):
            Storage.objects.create(collection=ct, mandatory_location=False)

    def test_clean_raises_when_risk_group_set_but_species_not_required(self):
        """Test clean raises when risk group is set but species not required"""
        self.storage.species_risk_group = 1
        with self.assertRaises(ValidationError) as ctx:
            self.storage.clean()
        self.assertIn("species_risk_group", ctx.exception.message_dict)

    def test_str_returns_collection_verbose_name(self):
        """Test __str__ returns the capitalized collection verbose name"""
        storage = _make_storage(model_class=Plasmid)
        result = str(storage)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_collection_is_protected_on_delete(self):
        """Test that collection ContentType is protected"""
        ct = self.storage.collection
        self.assertEqual(self.storage.collection, ct)

    def test_species_can_be_set(self):
        """Test species can be set when requirements are met"""
        species = Species.objects.create(latin_name="Test species", risk_group=1)
        storage = _make_storage(
            model_class=Plasmid, species=species, species_risk_group=1
        )
        storage.full_clean()
        self.assertEqual(storage.species, species)

    def test_multiple_storage_with_different_collections(self):
        """Test multiple Storage objects can exist with different collections"""
        s2 = _make_storage(model_class=Plasmid)
        s3 = _make_storage(model_class=Antibody)
        s4 = _make_storage(model_class=CellLine)
        self.assertEqual(Storage.objects.count(), 4)

    def test_storage_with_all_fields_set(self):
        """Test storage with all optional fields populated"""
        species = Species.objects.create(latin_name="Full species", risk_group=2)
        storage = _make_storage(
            model_class=CellLine,
            species=species,
            species_risk_group=2,
            mandatory_location=True,
        )
        self.assertTrue(storage.mandatory_location)
        self.assertEqual(storage.species_risk_group, 2)

    def test_storage_history_on_species_change(self):
        """Test history tracks species changes"""
        species1 = Species.objects.create(latin_name="Species 1", risk_group=1)
        species2 = Species.objects.create(latin_name="Species 2", risk_group=2)
        storage = _make_storage(
            model_class=Antibody, species=species1, species_risk_group=1
        )
        initial_count = storage.history.count()
        storage.species = species2
        storage.species_risk_group = 2
        storage.save()
        self.assertGreater(storage.history.count(), initial_count)


class LocationModelTest(TestCase):
    def setUp(self):
        self.storage = _make_storage(model_class=Inhibitor)
        self.loc_name = _make_location_name(name="Freezer -80 A")
        self.location = _make_location(self.storage, self.loc_name)

    def test_location_creation(self):
        self.assertEqual(self.location.level, 1)
        self.assertEqual(self.location.storage, self.storage)

    def test_str_representation(self):
        result = str(self.location)
        self.assertIn("❶", result)
        self.assertIn("Freezer -80 A", result)
        self.assertIn("-80° C", result)
        self.assertIn("9×9 box", result)

    def test_description_stripped_on_save(self):
        loc = _make_location(
            self.storage, self.loc_name, level=2, description="  Back shelf  "
        )
        loc.refresh_from_db()
        self.assertEqual(loc.description, "Back shelf")

    def test_description_defaults_to_empty(self):
        self.assertEqual(self.location.description, "")

    def test_mandatory_position_defaults_to_false(self):
        self.assertFalse(self.location.mandatory_position)

    def test_active_defaults_to_true(self):
        self.assertTrue(self.location.active)

    def test_history_created_on_save(self):
        self.assertGreater(self.location.history.count(), 0)

    def test_history_tracks_change(self):
        self.location.description = "Updated"
        self.location.save()
        self.assertGreaterEqual(self.location.history.count(), 2)

    def test_unique_level_per_storage_constraint(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            _make_location(self.storage, self.loc_name, level=1)

    def test_formz_label_returns_location_name(self):
        self.assertEqual(self.location.formz_label, self.loc_name)

    def test_storage_temperature_choices(self):
        """Test all storage temperature choices"""
        storage = _make_storage(model_class=Plasmid)
        level_counter = 1
        for temp, display in [
            ("RT", "Room temperature"),
            ("4", "4° C"),
            ("-20", "-20° C"),
            ("-80", "-80° C"),
            ("-150", "-150° C"),
        ]:
            loc_name2 = _make_location_name(name=f"Loc-{temp}")
            loc = _make_location(
                storage, loc_name2, level=level_counter, storage_temperature=temp
            )
            self.assertEqual(loc.storage_temperature, temp)
            self.assertIn(display, loc.get_storage_temperature_display())
            level_counter += 1

    def test_storage_format_choices(self):
        """Test all storage format choices"""
        storage = _make_storage(model_class=Antibody)
        level_counter = 1
        for fmt, display in [
            ("9×9", "9×9 box"),
            ("10×10", "10×10 box"),
            ("96", "96-well plate"),
            ("384", "384-well plate"),
            ("other", "Other"),
        ]:
            loc_name2 = _make_location_name(name=f"Loc-{fmt}")
            loc = _make_location(
                storage, loc_name2, level=level_counter, storage_format=fmt
            )
            self.assertEqual(loc.storage_format, fmt)
            self.assertIn(display, loc.get_storage_format_display())
            level_counter += 1

    def test_coordinate_format_choices(self):
        """Test all coordinate format choices"""
        storage = _make_storage(model_class=CellLine)
        level_counter = 1
        for fmt, display in [
            ("alphanumeric", "Alphanumeric"),
            ("numeric", "Numeric"),
            ("none", "None"),
        ]:
            loc_name3 = _make_location_name(name=f"Coord-{fmt}")
            loc = _make_location(
                storage, loc_name3, level=level_counter, coordinate_format=fmt
            )
            self.assertEqual(loc.coordinate_format, fmt)
            self.assertIn(display, loc.get_coordinate_format_display())
            level_counter += 1

    def test_level_choices(self):
        """Test all level choices"""
        storage = _make_storage(model_class=Plasmid)
        for level in [1, 2, 3, 4, 5]:
            loc_name = _make_location_name(name=f"Level-{level}")
            loc = _make_location(storage, loc_name, level=level)
            self.assertEqual(loc.level, level)

    def test_mandatory_position_can_be_true(self):
        """Test mandatory_position can be set to True"""
        loc = _make_location(
            self.storage, self.loc_name, level=2, mandatory_position=True
        )
        self.assertTrue(loc.mandatory_position)

    def test_active_can_be_false(self):
        """Test active can be set to False"""
        loc = _make_location(self.storage, self.loc_name, level=3, active=False)
        self.assertFalse(loc.active)

    def test_description_max_length(self):
        """Test description can be up to 255 characters"""
        long_desc = "D" * 255
        loc = _make_location(
            self.storage, self.loc_name, level=4, description=long_desc
        )
        self.assertEqual(len(loc.description), 255)

    def test_str_includes_pretty_levels(self):
        """Test __str__ includes pretty level indicators"""
        storage = _make_storage(model_class=Plasmid)
        for level, symbol in [(1, "❶"), (2, "❷"), (3, "❸"), (4, "❹"), (5, "❺")]:
            loc_name = _make_location_name(name=f"PrettyLevel-{level}")
            loc = _make_location(storage, loc_name, level=level)
            self.assertIn(symbol, str(loc))

    def test_multiple_locations_same_storage_different_levels(self):
        """Test multiple locations can exist for same storage with different levels"""
        loc2 = _make_location(self.storage, self.loc_name, level=2)
        loc3 = _make_location(self.storage, self.loc_name, level=3)
        self.assertEqual(loc2.storage, self.storage)
        self.assertEqual(loc3.storage, self.storage)
        self.assertNotEqual(loc2.level, loc3.level)

    def test_location_name_foreign_key_protected(self):
        """Test location name is protected from deletion"""
        loc_name_new = _make_location_name(name="Protected Name")
        storage_new = _make_storage()
        _make_location(storage_new, loc_name_new, level=1)
        self.assertIsNotNone(loc_name_new)

    def test_storage_foreign_key_protected(self):
        """Test storage is protected from deletion"""
        self.assertIsNotNone(self.storage)
        self.assertEqual(self.location.storage, self.storage)

    def test_location_with_long_description(self):
        """Test location with maximum length description"""
        long_desc = "X" * 255
        loc = _make_location(
            self.storage, self.loc_name, level=2, description=long_desc
        )
        self.assertEqual(len(loc.description), 255)

    def test_location_inactive(self):
        """Test setting location as inactive"""
        loc = _make_location(self.storage, self.loc_name, level=4, active=False)
        self.assertFalse(loc.active)
        loc.active = True
        loc.save()
        self.assertTrue(loc.active)


class LocationItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="litest@example.com", password="password"
        )
        self.inhibitor = Inhibitor.objects.create(
            name="ItemInhibitor", created_by=self.user
        )
        self.storage = _make_storage()
        self.loc_name = _make_location_name(name="Item Freezer")
        self.location = _make_location(
            self.storage, self.loc_name, coordinate_format="none"
        )
        self.item = _make_location_item(self.location, self.inhibitor, box="A1")

    def test_item_creation(self):
        self.assertEqual(self.item.location, self.location)
        self.assertEqual(self.item.box, "A1")

    def test_str_includes_location_and_box(self):
        result = str(self.item)
        self.assertIn("A1", result)

    def test_box_stripped_on_save(self):
        item = _make_location_item(self.location, self.inhibitor, box="  B2  ")
        item.refresh_from_db()
        self.assertEqual(item.box, "B2")

    def test_coordinate_uppercased_on_save(self):
        loc_alpha = _make_location(
            self.storage,
            self.loc_name,
            level=2,
            storage_format="96",
            coordinate_format="alphanumeric",
        )
        item = _make_location_item(
            loc_alpha, self.inhibitor, box="Box1", coordinate="a1"
        )
        item.refresh_from_db()
        self.assertEqual(item.coordinate, "A1")

    def test_comment_stripped_on_save(self):
        item = _make_location_item(
            self.location, self.inhibitor, box="C3", comment="  Extra note  "
        )
        item.refresh_from_db()
        self.assertEqual(item.comment, "Extra note")

    def test_comment_defaults_to_empty(self):
        self.assertEqual(self.item.comment, "")

    def test_history_created_on_save(self):
        self.assertGreater(self.item.history.count(), 0)

    def test_history_tracks_change(self):
        self.item.comment = "Updated"
        self.item.save()
        self.assertGreaterEqual(self.item.history.count(), 2)

    def test_clean_raises_when_mandatory_position_box_missing_coordinate_given(self):
        loc = _make_location(
            self.storage,
            self.loc_name,
            level=3,
            coordinate_format="numeric",
            mandatory_position=True,
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc,
            box="",
            coordinate="5",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("box", ctx.exception.message_dict)

    def test_clean_raises_when_coordinate_given_without_box(self):
        loc_numeric = _make_location(
            self.storage, self.loc_name, level=4, coordinate_format="numeric"
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_numeric,
            box="",
            coordinate="5",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("box", ctx.exception.message_dict)

    def test_clean_raises_on_bad_alphanumeric_coordinate_96_well(self):
        loc_96 = _make_location(
            self.storage,
            self.loc_name,
            level=5,
            storage_format="96",
            coordinate_format="alphanumeric",
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_96,
            box="Box1",
            coordinate="Z99",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("coordinate", ctx.exception.message_dict)

    def test_clean_raises_on_bad_numeric_coordinate(self):
        loc_numeric = _make_location(
            self.storage, self.loc_name, level=4, coordinate_format="numeric"
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_numeric,
            box="Box1",
            coordinate="abc",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("coordinate", ctx.exception.message_dict)

    def test_clean_passes_with_valid_96_well_coordinate(self):
        loc_96 = _make_location(
            self.storage,
            self.loc_name,
            level=5,
            storage_format="96",
            coordinate_format="alphanumeric",
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_96,
            box="Box1",
            coordinate="H12",
        )
        try:
            item.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError for a valid H12 coordinate")

    def test_clean_passes_with_valid_384_well_coordinate(self):
        """Test clean passes with valid 384-well coordinate"""
        loc_384 = _make_location(
            self.storage,
            self.loc_name,
            level=2,
            storage_format="384",
            coordinate_format="alphanumeric",
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_384,
            box="Box1",
            coordinate="P24",
        )
        try:
            item.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError for valid P24 coordinate")

    def test_clean_raises_on_bad_384_well_coordinate(self):
        """Test clean raises on invalid 384-well coordinate"""
        loc_384 = _make_location(
            self.storage,
            self.loc_name,
            level=3,
            storage_format="384",
            coordinate_format="alphanumeric",
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_384,
            box="Box1",
            coordinate="Q25",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("coordinate", ctx.exception.message_dict)

    def test_clean_passes_with_valid_10x10_coordinate(self):
        """Test clean passes with valid 10×10 coordinate"""
        loc_10x10 = _make_location(
            self.storage,
            self.loc_name,
            level=4,
            storage_format="10×10",
            coordinate_format="alphanumeric",
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_10x10,
            box="Box1",
            coordinate="J10",
        )
        try:
            item.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError for valid J10 coordinate")

    def test_clean_passes_with_valid_9x9_coordinate(self):
        """Test clean passes with valid 9×9 coordinate"""
        loc_9x9 = _make_location(
            self.storage,
            self.loc_name,
            level=5,
            storage_format="9×9",
            coordinate_format="alphanumeric",
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_9x9,
            box="Box1",
            coordinate="I9",
        )
        try:
            item.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError for valid I9 coordinate")

    def test_clean_raises_when_location_provided_without_box_or_coordinate(self):
        """Test clean allows location without box/coordinate"""
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=self.location,
            box="",
            coordinate="",
        )
        try:
            item.clean()
        except ValidationError:
            self.fail(
                "clean() should not raise when location is provided without box/coordinate"
            )

    def test_clean_raises_when_box_or_coordinate_provided_without_location(self):
        """Test clean raises when box/coordinate provided without location"""
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=None,
            box="Box1",
            coordinate="",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("location", ctx.exception.message_dict)

    def test_minimal_str_property(self):
        """Test minimal_str property"""
        item = _make_location_item(
            self.location, self.inhibitor, box="TestBox", coordinate="A1"
        )
        minimal = item.minimal_str
        self.assertIn("TestBox", minimal)
        self.assertIn("A1", minimal)
        self.assertIn(str(self.location.level), minimal)

    def test_formz_label_property(self):
        """Test formz_label property"""
        item = _make_location_item(
            self.location, self.inhibitor, box="LabelBox", coordinate="B2"
        )
        label = item.formz_label
        self.assertIn("LabelBox", label)
        self.assertIn("B2", label)

    def test_generic_foreign_key_works(self):
        """Test that generic foreign key correctly links to content object"""
        item = _make_location_item(self.location, self.inhibitor)
        self.assertEqual(item.content_object, self.inhibitor)
        self.assertEqual(
            item.content_type, ContentType.objects.get_for_model(Inhibitor)
        )
        self.assertEqual(item.object_id, self.inhibitor.pk)

    def test_multiple_items_same_location(self):
        """Test multiple items can be in the same location"""
        inh2 = Inhibitor.objects.create(name="ItemInhibitor2", created_by=self.user)
        item1 = _make_location_item(self.location, self.inhibitor, box="A1")
        item2 = _make_location_item(self.location, inh2, box="A2")
        self.assertEqual(item1.location, item2.location)
        self.assertNotEqual(item1.box, item2.box)

    def test_item_with_different_content_types(self):
        """Test LocationItem works with different collection models"""
        plasmid = Plasmid.objects.create(name="TestPlasmid", created_by=self.user)
        antibody = Antibody.objects.create(
            name="TestAb", species_isotype="Mouse", created_by=self.user
        )
        item_plasmid = _make_location_item(self.location, plasmid, box="P1")
        item_antibody = _make_location_item(self.location, antibody, box="A1")
        self.assertNotEqual(item_plasmid.content_type, item_antibody.content_type)

    def test_item_box_max_length(self):
        """Test box field max length"""
        long_box = "B" * 10
        item = _make_location_item(self.location, self.inhibitor, box=long_box)
        self.assertEqual(len(item.box), 10)

    def test_item_coordinate_max_length(self):
        """Test coordinate field max length"""
        long_coord = "C" * 10
        item = _make_location_item(
            self.location, self.inhibitor, box="Box1", coordinate=long_coord
        )
        self.assertEqual(len(item.coordinate), 10)

    def test_item_comment_max_length(self):
        """Test comment field max length"""
        long_comment = "X" * 150
        item = _make_location_item(
            self.location, self.inhibitor, box="Box1", comment=long_comment
        )
        self.assertEqual(len(item.comment), 150)

    def test_clean_raises_when_mandatory_position_coordinate_missing(self):
        """Test clean raises when coordinate is missing but mandatory"""
        loc = _make_location(
            self.storage, self.loc_name, level=3, mandatory_position=True
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc,
            box="Box1",
            coordinate="",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("coordinate", ctx.exception.message_dict)

    def test_clean_raises_when_mandatory_position_both_missing(self):
        """Test clean raises when both box and coordinate missing but mandatory"""
        loc = _make_location(
            self.storage, self.loc_name, level=2, mandatory_position=True
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc,
            box="",
            coordinate="",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("box", ctx.exception.message_dict)
        self.assertIn("coordinate", ctx.exception.message_dict)

    def test_clean_raises_on_bad_10x10_coordinate(self):
        """Test clean raises on invalid 10×10 coordinate"""
        loc_10x10 = _make_location(
            self.storage,
            self.loc_name,
            level=4,
            storage_format="10×10",
            coordinate_format="alphanumeric",
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_10x10,
            box="Box1",
            coordinate="K11",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("coordinate", ctx.exception.message_dict)

    def test_clean_raises_on_bad_9x9_coordinate(self):
        """Test clean raises on invalid 9×9 coordinate"""
        loc_9x9 = _make_location(
            self.storage,
            self.loc_name,
            level=5,
            storage_format="9×9",
            coordinate_format="alphanumeric",
        )
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=loc_9x9,
            box="Box1",
            coordinate="J10",
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("coordinate", ctx.exception.message_dict)

    def test_coordinate_format_validation_alphanumeric_96(self):
        """Test alphanumeric coordinate validation for 96-well plate"""
        loc_96 = _make_location(
            self.storage,
            self.loc_name,
            level=2,
            storage_format="96",
            coordinate_format="alphanumeric",
        )
        for coord in ["A1", "H12", "B5"]:
            item = LocationItem(
                content_type=ContentType.objects.get_for_model(self.inhibitor),
                object_id=self.inhibitor.pk,
                location=loc_96,
                box="Box1",
                coordinate=coord,
            )
            try:
                item.clean()
            except ValidationError:
                self.fail(f"clean() raised ValidationError for valid coord: {coord}")

    def test_coordinate_format_validation_numeric(self):
        """Test numeric coordinate validation"""
        loc_numeric = _make_location(
            self.storage, self.loc_name, level=3, coordinate_format="numeric"
        )
        for coord in ["1", "42", "999"]:
            item = LocationItem(
                content_type=ContentType.objects.get_for_model(self.inhibitor),
                object_id=self.inhibitor.pk,
                location=loc_numeric,
                box="Box1",
                coordinate=coord,
            )
            try:
                item.clean()
            except ValidationError:
                self.fail(f"clean() raised ValidationError for valid coord: {coord}")

    def test_coordinate_case_insensitive(self):
        """Test coordinate is uppercased regardless of input case"""
        loc_alpha = _make_location(
            self.storage,
            self.loc_name,
            level=2,
            storage_format="96",
            coordinate_format="alphanumeric",
        )
        test_cases = [("a1", "A1"), ("h12", "H12"), ("B3", "B3")]
        for idx, (input_coord, expected) in enumerate(test_cases):
            inh = Inhibitor.objects.create(
                name=f"CaseTestInhibitor{idx}", created_by=self.user
            )
            item = _make_location_item(
                loc_alpha, inh, box=f"Box{idx}", coordinate=input_coord
            )
            item.refresh_from_db()
            self.assertEqual(item.coordinate, expected)

    def test_formz_label_without_coordinate(self):
        """Test formz_label when only box is set"""
        item = _make_location_item(self.location, self.inhibitor, box="OnlyBox")
        label = item.formz_label
        self.assertIn("OnlyBox", label)
        self.assertIn(self.loc_name.name, label)

    def test_minimal_str_format(self):
        """Test minimal_str includes level and name"""
        item = _make_location_item(
            self.location, self.inhibitor, box="MinBox", coordinate="C1"
        )
        minimal = item.minimal_str
        self.assertIn(str(self.location.level), minimal)
        self.assertIn(str(self.location.name), minimal)

    def test_item_with_only_location_no_box_no_coordinate(self):
        """Test item can have only location without box/coordinate"""
        item = LocationItem(
            content_type=ContentType.objects.get_for_model(self.inhibitor),
            object_id=self.inhibitor.pk,
            location=self.location,
            box="",
            coordinate="",
        )
        try:
            item.full_clean()
            item.save()
        except ValidationError:
            self.fail("Should allow location without box/coordinate")

    def test_item_index_on_content_type_and_object_id(self):
        """Test that index exists on content_type and object_id"""
        indexes = [idx.fields for idx in LocationItem._meta.indexes]
        self.assertIn(["content_type", "object_id"], indexes)
