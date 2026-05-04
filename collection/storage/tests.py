from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.forms import ValidationError
from django.test import TestCase

from collection.inhibitor.models import Inhibitor
from collection.plasmid.models import Plasmid
from formz.models import Species

from .models import Location, LocationItem, LocationName, Storage

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_location_name(name="Freezer A", **kwargs):
    defaults = dict(name=name)
    defaults.update(kwargs)
    return LocationName.objects.create(**defaults)


def _make_storage(model_class=None, **kwargs):
    if model_class is None:
        model_class = Inhibitor
    ct = ContentType.objects.get_for_model(model_class)
    defaults = dict(collection=ct)
    defaults.update(kwargs)
    return Storage.objects.create(**defaults)


def _make_location(storage, location_name, level=1, **kwargs):
    defaults = dict(
        storage=storage,
        level=level,
        name=location_name,
        storage_temperature="-80",
        storage_format="9×9",
        coordinate_format="alphanumeric",
    )
    defaults.update(kwargs)
    return Location.objects.create(**defaults)


def _make_location_item(location, content_object, **kwargs):
    ct = ContentType.objects.get_for_model(content_object)
    defaults = dict(
        content_type=ct,
        object_id=content_object.pk,
        location=location,
    )
    defaults.update(kwargs)
    return LocationItem.objects.create(**defaults)


# ---------------------------------------------------------------------------
# LocationName tests
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Storage tests
# ---------------------------------------------------------------------------


class StorageModelTest(TestCase):
    def setUp(self):
        self.storage = _make_storage()

    def test_storage_creation(self):
        ct = ContentType.objects.get_for_model(Inhibitor)
        self.assertEqual(self.storage.collection, ct)

    def test_str_representation(self):
        # capfirst(verbose_name) of the linked model
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
        # Inhibitor has no _storage_requires_species — clean() should not raise
        try:
            self.storage.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly")

    def test_clean_raises_when_species_required_but_not_set(self):
        # Plasmid has _storage_requires_species = "Escherichia coli"
        storage = _make_storage(model_class=Plasmid)
        with self.assertRaises(ValidationError) as ctx:
            storage.clean()
        self.assertIn("species", ctx.exception.message_dict)

    def test_clean_raises_when_species_set_but_not_required(self):
        species = Species.objects.create(
            name_for_search="testspecies", latin_name="Test species", risk_group=1
        )
        self.storage.species = species
        with self.assertRaises(ValidationError) as ctx:
            self.storage.clean()
        self.assertIn("species", ctx.exception.message_dict)

    def test_clean_raises_when_species_set_but_risk_group_missing(self):
        # Use Plasmid storage (requires species) but omit risk group
        species = Species.objects.create(
            name_for_search="ecoli-rg", latin_name="Escherichia coli", risk_group=1
        )
        storage = _make_storage(model_class=Plasmid, species=species)
        with self.assertRaises(ValidationError) as ctx:
            storage.clean()
        self.assertIn("species_risk_group", ctx.exception.message_dict)


# ---------------------------------------------------------------------------
# Location tests
# ---------------------------------------------------------------------------


class LocationModelTest(TestCase):
    def setUp(self):
        self.storage = _make_storage()
        self.loc_name = _make_location_name(name="Freezer -80 A")
        self.location = _make_location(self.storage, self.loc_name)

    def test_location_creation(self):
        self.assertEqual(self.location.level, 1)
        self.assertEqual(self.location.storage, self.storage)

    def test_str_representation(self):
        # "❶ | Freezer -80 A | -80° C | 9×9 box"
        result = str(self.location)
        self.assertIn("❶", result)
        self.assertIn("Freezer -80 A", result)
        self.assertIn("-80° C", result)
        self.assertIn("9×9 box", result)

    def test_description_stripped_on_save(self):
        loc = _make_location(
            self.storage,
            self.loc_name,
            level=2,
            description="  Back shelf  ",
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


# ---------------------------------------------------------------------------
# LocationItem tests
# ---------------------------------------------------------------------------


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
            self.storage,
            self.loc_name,
            coordinate_format="none",
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
        # clean() only raises ValidationError when coordinate.strip() is truthy.
        # Supply a coordinate so the raise path is reached, and verify that the
        # missing-box error is included.
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
            self.storage,
            self.loc_name,
            level=4,
            coordinate_format="numeric",
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
            self.storage,
            self.loc_name,
            level=4,
            coordinate_format="numeric",
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
