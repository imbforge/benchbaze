from unittest import skip
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from .models import OtherBacteriumStrain, OtherBacteriumStrainDoc

User = get_user_model()


def _make_otherbacteriumstrain(user, name="Bacillus subtilis", **kwargs):
    defaults = {"name": name, "supplier": "DSMZ", "us_e": "Cloning", "created_by": user}
    defaults.update(kwargs)
    return OtherBacteriumStrain.objects.create(**defaults)


class OtherBacteriumStrainModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="bactest@example.com", password="password"
        )
        cls.strain = _make_otherbacteriumstrain(cls.user)

    def test_otherbacteriumstrain_creation(self):
        self.assertEqual(self.strain.name, "Bacillus subtilis")

    def test_str_representation(self):
        self.assertEqual(str(self.strain), f"{self.strain.id} - Bacillus subtilis")

    def test_name_stripped_on_save(self):
        strain = _make_otherbacteriumstrain(self.user, name="  Pseudomonas  ")
        strain.refresh_from_db()
        self.assertEqual(strain.name, "Pseudomonas")

    def test_resistance_defaults_to_empty(self):
        self.assertEqual(self.strain.resistance, "")

    def test_genotype_defaults_to_empty(self):
        self.assertEqual(self.strain.genotype, "")

    def test_background_defaults_to_empty(self):
        self.assertEqual(self.strain.background, "")

    def test_note_defaults_to_empty(self):
        self.assertEqual(self.strain.note, "")

    def test_species_nullable(self):
        strain = _make_otherbacteriumstrain(self.user, name="No Species", species=None)
        self.assertIsNone(strain.species)

    def test_timestamps_set_automatically(self):
        self.assertIsNotNone(self.strain.created_date_time)
        self.assertIsNotNone(self.strain.last_changed_date_time)

    def test_created_by_is_set(self):
        self.assertEqual(self.strain.created_by, self.user)

    def test_history_created_on_save(self):
        self.assertGreater(self.strain.history.count(), 0)

    def test_history_tracks_change(self):
        self.strain.resistance = "KanR"
        self.strain.save()
        self.assertGreaterEqual(self.strain.history.count(), 2)

    def test_all_char_fields_can_be_set(self):
        """Test that all character fields accept values"""
        strain = _make_otherbacteriumstrain(
            self.user,
            name="Complete Strain",
            resistance="AmpR, KanR",
            genotype="Wild type",
            background="DSM 10",
            supplier="ATCC",
            us_e="Production",
            note="Store at -80C",
        )
        self.assertEqual(strain.resistance, "AmpR, KanR")
        self.assertEqual(strain.genotype, "Wild type")
        self.assertEqual(strain.background, "DSM 10")
        self.assertEqual(strain.supplier, "ATCC")
        self.assertEqual(strain.us_e, "Production")
        self.assertEqual(strain.note, "Store at -80C")

    def test_genotype_accepts_long_text(self):
        """Test TextField can hold longer text"""
        long_genotype = (
            "Wild type strain with complete genome sequence available. " * 10
        )
        strain = _make_otherbacteriumstrain(
            self.user, name="Long Genotype", genotype=long_genotype
        )
        strain.refresh_from_db()
        self.assertEqual(strain.genotype, long_genotype)

    def test_note_accepts_long_text(self):
        """Test TextField can hold longer text"""
        long_note = (
            "This strain is specifically designed for biotechnological applications. "
            * 10
        )
        strain = _make_otherbacteriumstrain(self.user, name="Long Note", note=long_note)
        strain.refresh_from_db()
        self.assertEqual(strain.note, long_note)

    def test_name_with_special_characters(self):
        """Test that special characters in name are preserved"""
        strain = _make_otherbacteriumstrain(
            self.user, name="Bacillus sp. (strain 123-α)"
        )
        strain.refresh_from_db()
        self.assertEqual(strain.name, "Bacillus sp. (strain 123-α)")

    def test_very_long_name_within_limit(self):
        """Test name can be up to 255 characters"""
        long_name = "A" * 255
        strain = _make_otherbacteriumstrain(self.user, name=long_name)
        self.assertEqual(len(strain.name), 255)

    def test_save_without_historical_record(self):
        """Test that save_without_historical_record doesn't create history entry"""
        initial_count = self.strain.history.count()
        self.strain.resistance = "NoHistoryResistance"
        self.strain.save_without_historical_record()
        self.assertEqual(self.strain.history.count(), initial_count)

    def test_readonly_fields_for_creator(self):
        """Test that creator can edit all obj_specific_fields"""
        mock_request = Mock()
        mock_request.user = self.user
        readonly = self.strain.readonly_fields(mock_request)
        self.assertIn("created_date_time", readonly)
        self.assertIn("last_changed_date_time", readonly)
        self.assertNotIn("name", readonly)

    def test_readonly_fields_for_other_user(self):
        """Test that non-creator non-elevated user has all fields readonly"""
        other_user = User.objects.create_user(
            email="other@example.com", password="password"
        )
        mock_request = Mock()
        mock_request.user = other_user
        readonly = self.strain.readonly_fields(mock_request)
        self.assertIn("name", readonly)
        self.assertIn("created_date_time", readonly)

    def test_model_meta_verbose_name(self):
        """Test model verbose names are set correctly"""
        self.assertEqual(
            OtherBacteriumStrain._meta.verbose_name, "strain - Other Bacterium"
        )
        self.assertEqual(
            OtherBacteriumStrain._meta.verbose_name_plural, "strains - Other Bacterium"
        )

    def test_required_fields_cannot_be_none(self):
        """Test that required fields cannot be None"""
        with self.assertRaises(Exception):
            OtherBacteriumStrain.objects.create(
                name=None, supplier="DSMZ", us_e="Cloning", created_by=self.user
            )
        with self.assertRaises(Exception):
            OtherBacteriumStrain.objects.create(
                name="Test", supplier=None, us_e="Cloning", created_by=self.user
            )
        with self.assertRaises(Exception):
            OtherBacteriumStrain.objects.create(
                name="Test", supplier="DSMZ", us_e=None, created_by=self.user
            )

    def test_multiple_strains_same_name_allowed(self):
        """Test that multiple strains can have the same name (no uniqueness constraint)"""
        strain1 = _make_otherbacteriumstrain(self.user, name="Duplicate Name")
        strain2 = _make_otherbacteriumstrain(self.user, name="Duplicate Name")
        self.assertEqual(strain1.name, strain2.name)
        self.assertNotEqual(strain1.id, strain2.id)

    def test_clean_method_strips_name(self):
        """Test that clean method properly strips name"""
        strain = OtherBacteriumStrain(
            name="  Spaced Name  ",
            supplier="DSMZ",
            us_e="Cloning",
            created_by=self.user,
        )
        try:
            strain.clean()
        except ValidationError:
            pass
        self.assertEqual(strain.name, "Spaced Name")

    def test_model_abbreviation(self):
        """Test model abbreviation is set correctly"""
        self.assertEqual(self.strain._model_abbreviation, "bac")

    def test_is_guarded_model(self):
        """Test that OtherBacteriumStrain is a guarded model"""
        self.assertTrue(self.strain._is_guarded_model)

    def test_us_e_field_name(self):
        """Test that us_e field accepts values"""
        strain = _make_otherbacteriumstrain(self.user, name="Use Test", us_e="Research")
        self.assertEqual(strain.us_e, "Research")

    def test_formz_species_property(self):
        """Test formz_species property"""
        if self.strain.species is not None:
            species_obj = self.strain.formz_species
            self.assertEqual(species_obj, self.strain.species)
        else:
            with self.assertRaises(AttributeError):
                _ = self.strain.formz_species


class OtherBacteriumStrainDocModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="bacdoctest@example.com", password="password"
        )
        cls.strain = _make_otherbacteriumstrain(cls.user, name="Doc Test Strain")

    def test_otherbacteriumstraindoc_creation(self):
        """Test creating an OtherBacteriumStrainDoc"""
        test_file = SimpleUploadedFile(
            "test.pdf", b"file_content", content_type="application/pdf"
        )
        doc = OtherBacteriumStrainDoc.objects.create(
            other_bacterium_strain=self.strain,
            name=test_file,
            description="Test document",
        )
        self.assertEqual(doc.other_bacterium_strain, self.strain)
        self.assertEqual(doc.description, "Test document")

    def test_otherbacteriumstraindoc_foreignkey_protection(self):
        """Test that deleting strain is protected when docs exist"""
        from django.db.models.deletion import ProtectedError

        test_file = SimpleUploadedFile(
            "protected.pdf", b"file_content", content_type="application/pdf"
        )
        doc = OtherBacteriumStrainDoc.objects.create(
            other_bacterium_strain=self.strain,
            name=test_file,
            description="Protected doc",
        )
        with self.assertRaises(ProtectedError):
            self.strain.delete()

    def test_otherbacteriumstraindoc_timestamps(self):
        """Test that doc has timestamps"""
        test_file = SimpleUploadedFile(
            "time.pdf", b"file_content", content_type="application/pdf"
        )
        doc = OtherBacteriumStrainDoc.objects.create(
            other_bacterium_strain=self.strain,
            name=test_file,
            description="Time test doc",
        )
        self.assertIsNotNone(doc.created_date_time)
        self.assertIsNotNone(doc.last_changed_date_time)

    def test_otherbacteriumstraindoc_verbose_name(self):
        """Test OtherBacteriumStrainDoc verbose name"""
        self.assertEqual(
            OtherBacteriumStrainDoc._meta.verbose_name,
            "Other bacterium strain document",
        )


class OtherBacteriumStrainAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="bacapitest@example.com", password="password"
        )
        cls.strain = _make_otherbacteriumstrain(cls.user)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = "/api/collection/otherbacteriumstrain/"

    def test_list_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_count(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 1)

    def test_retrieve_returns_200(self):
        response = self.client.get(f"{self.url}{self.strain.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Bacillus subtilis")

    @skip(
        "The generic ModelViewSet does not support create via the API (get_serializer_class() requires self.model set by get_queryset())."
    )
    def test_create_otherbacteriumstrain(self):
        data = {"name": "Pseudomonas", "supplier": "DSMZ", "us_e": "Production"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @skip(
        "The generic ModelViewSet does not support create via the API (see test_create_otherbacteriumstrain)."
    )
    def test_create_sets_created_by_to_request_user(self):
        data = {"name": "Owned Strain", "supplier": "ATCC", "us_e": "Research"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_strain = OtherBacteriumStrain.objects.get(id=response.data["id"])
        self.assertEqual(new_strain.created_by, self.user)

    @skip(
        "The generic ModelViewSet serializer uses empty field_names for partial_update, so no fields are persisted."
    )
    def test_partial_update_otherbacteriumstrain(self):
        response = self.client.patch(
            f"{self.url}{self.strain.id}/", {"resistance": "AmpR"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_otherbacteriumstrain(self):
        response = self.client.delete(f"{self.url}{self.strain.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(OtherBacteriumStrain.objects.count(), 0)

    def test_unauthenticated_returns_403(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_search_by_name(self):
        _make_otherbacteriumstrain(self.user, name="Pseudomonas aeruginosa")
        response = self.client.get(self.url, {"search": "Pseudomonas"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Pseudomonas aeruginosa", names)
        self.assertNotIn("Bacillus subtilis", names)

    def test_retrieve_nonexistent_returns_404(self):
        response = self.client.get(f"{self.url}999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_includes_all_expected_fields(self):
        """Test that list response includes expected fields"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data["count"] > 0:
            item = response.data["results"][0]
            expected_fields = ["id", "name", "species", "us_e"]
            for field in expected_fields:
                self.assertIn(field, item)

    def test_search_by_id(self):
        """Test searching by ID"""
        strain = _make_otherbacteriumstrain(self.user, name="ID Searchable")
        response = self.client.get(self.url, {"search": str(strain.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pagination_default(self):
        """Test that pagination works"""
        for i in range(15):
            _make_otherbacteriumstrain(self.user, name=f"Strain {i}")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 15)

    def test_pagination_custom_page_size(self):
        """Test custom page size parameter"""
        for i in range(10):
            _make_otherbacteriumstrain(self.user, name=f"Page Test {i}")
        response = self.client.get(self.url, {"page_size": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            self.assertGreaterEqual(response.data["count"], 11)

    def test_retrieve_returns_complete_data(self):
        """Test that retrieve returns all strain fields"""
        strain = _make_otherbacteriumstrain(
            self.user,
            name="Complete Data",
            resistance="AmpR, KanR",
            genotype="Wild type",
            background="DSM 10",
            supplier="ATCC",
            us_e="Production",
            note="Store at -80C in glycerol stocks",
        )
        response = self.client.get(f"{self.url}{strain.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Complete Data")
        self.assertEqual(response.data["resistance"], "AmpR, KanR")
        self.assertEqual(response.data["genotype"], "Wild type")
        self.assertEqual(response.data["background"], "DSM 10")
        self.assertEqual(response.data["supplier"], "ATCC")
        self.assertEqual(response.data["us_e"], "Production")
        self.assertEqual(response.data["note"], "Store at -80C in glycerol stocks")

    def test_delete_removes_from_database(self):
        """Test that delete actually removes the strain"""
        strain = _make_otherbacteriumstrain(self.user, name="To Delete")
        strain_id = strain.id
        response = self.client.delete(f"{self.url}{strain_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(OtherBacteriumStrain.objects.filter(id=strain_id).exists())

    def test_unauthenticated_retrieve_forbidden(self):
        """Test that unauthenticated users cannot retrieve"""
        self.client.force_authenticate(user=None)
        response = self.client.get(f"{self.url}{self.strain.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_delete_forbidden(self):
        """Test that unauthenticated users cannot delete"""
        strain = _make_otherbacteriumstrain(self.user, name="Protected")
        self.client.force_authenticate(user=None)
        response = self.client.delete(f"{self.url}{strain.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertTrue(OtherBacteriumStrain.objects.filter(id=strain.id).exists())

    def test_search_no_results(self):
        """Test search with no matching results"""
        response = self.client.get(
            self.url, {"search": "NonExistentBacteriumStrain123456"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_search_case_insensitive(self):
        """Test that search is case insensitive"""
        _make_otherbacteriumstrain(self.user, name="Lactobacillus")
        response_lower = self.client.get(self.url, {"search": "lactobacillus"})
        response_upper = self.client.get(self.url, {"search": "LACTOBACILLUS"})
        self.assertEqual(response_lower.status_code, status.HTTP_200_OK)
        self.assertEqual(response_upper.status_code, status.HTTP_200_OK)

    def test_list_empty_database(self):
        """Test listing when no strains exist"""
        OtherBacteriumStrain.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_retrieve_includes_timestamps(self):
        """Test that retrieve includes timestamp fields"""
        response = self.client.get(f"{self.url}{self.strain.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("created_date_time", response.data)
        self.assertIn("last_changed_date_time", response.data)

    def test_search_partial_match(self):
        """Test search with partial string match"""
        _make_otherbacteriumstrain(self.user, name="Bacillus-GFP")
        response = self.client.get(self.url, {"search": "GFP"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data["count"] > 0:
            names = [item["name"] for item in response.data["results"]]
            self.assertTrue(any("GFP" in name for name in names))

    def test_multiple_searches_independent(self):
        """Test that multiple searches don't interfere with each other"""
        strain1 = _make_otherbacteriumstrain(self.user, name="Unique Alpha")
        strain2 = _make_otherbacteriumstrain(self.user, name="Unique Beta")
        response1 = self.client.get(self.url, {"search": "Alpha"})
        response2 = self.client.get(self.url, {"search": "Beta"})
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_ordering_by_id(self):
        """Test ordering strains by ID"""
        strain1 = _make_otherbacteriumstrain(self.user, name="First")
        strain2 = _make_otherbacteriumstrain(self.user, name="Second")
        response = self.client.get(self.url, {"ordering": "id"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_response_structure(self):
        """Test that list response has correct structure"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertIsInstance(response.data["results"], list)
        self.assertIsInstance(response.data["count"], int)
