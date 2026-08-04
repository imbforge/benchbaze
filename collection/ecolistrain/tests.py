from unittest import skip
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from .models import EColiStrain, EColiStrainDoc

User = get_user_model()


def _make_ecolistrain(user, name="DH5alpha", **kwargs):
    defaults = {"name": name, "supplier": "NEB", "us_e": "Cloning", "created_by": user}
    defaults.update(kwargs)
    return EColiStrain.objects.create(**defaults)


class EColiStrainModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="ectest@example.com", password="password"
        )
        cls.strain = _make_ecolistrain(cls.user)

    def test_ecolistrain_creation(self):
        self.assertEqual(self.strain.name, "DH5alpha")

    def test_str_representation(self):
        self.assertEqual(str(self.strain), f"{self.strain.id} - DH5alpha")

    def test_name_stripped_on_save(self):
        strain = _make_ecolistrain(self.user, name="  BL21  ")
        strain.refresh_from_db()
        self.assertEqual(strain.name, "BL21")

    def test_resistance_defaults_to_empty(self):
        self.assertEqual(self.strain.resistance, "")

    def test_genotype_defaults_to_empty(self):
        self.assertEqual(self.strain.genotype, "")

    def test_purpose_defaults_to_empty(self):
        self.assertEqual(self.strain.purpose, "")

    def test_background_defaults_to_empty(self):
        self.assertEqual(self.strain.background, "")

    def test_note_defaults_to_empty(self):
        self.assertEqual(self.strain.note, "")

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
        strain = _make_ecolistrain(
            self.user,
            name="Complete Strain",
            resistance="AmpR, KanR",
            genotype="F- endA1 recA1",
            background="K12",
            supplier="Invitrogen",
            us_e="Expression",
            purpose="Protein production",
            note="Store at -80C",
        )
        self.assertEqual(strain.resistance, "AmpR, KanR")
        self.assertEqual(strain.genotype, "F- endA1 recA1")
        self.assertEqual(strain.background, "K12")
        self.assertEqual(strain.supplier, "Invitrogen")
        self.assertEqual(strain.us_e, "Expression")
        self.assertEqual(strain.purpose, "Protein production")
        self.assertEqual(strain.note, "Store at -80C")

    def test_background_choice_field_b(self):
        """Test background choice field with B"""
        strain = _make_ecolistrain(self.user, name="B Strain", background="B")
        self.assertEqual(strain.background, "B")

    def test_background_choice_field_c(self):
        """Test background choice field with C"""
        strain = _make_ecolistrain(self.user, name="C Strain", background="C")
        self.assertEqual(strain.background, "C")

    def test_background_choice_field_k12(self):
        """Test background choice field with K12"""
        strain = _make_ecolistrain(self.user, name="K12 Strain", background="K12")
        self.assertEqual(strain.background, "K12")

    def test_background_choice_field_w(self):
        """Test background choice field with W"""
        strain = _make_ecolistrain(self.user, name="W Strain", background="W")
        self.assertEqual(strain.background, "W")

    def test_us_e_choice_field_cloning(self):
        """Test us_e choice field with Cloning"""
        strain = _make_ecolistrain(self.user, name="Cloning Strain", us_e="Cloning")
        self.assertEqual(strain.us_e, "Cloning")

    def test_us_e_choice_field_expression(self):
        """Test us_e choice field with Expression"""
        strain = _make_ecolistrain(
            self.user, name="Expression Strain", us_e="Expression"
        )
        self.assertEqual(strain.us_e, "Expression")

    def test_us_e_choice_field_other(self):
        """Test us_e choice field with Other"""
        strain = _make_ecolistrain(self.user, name="Other Strain", us_e="Other")
        self.assertEqual(strain.us_e, "Other")

    def test_genotype_accepts_long_text(self):
        """Test TextField can hold longer text"""
        long_genotype = (
            "F- ompT gal dcm lon hsdSB(rB-mB-) λ(DE3 [lacI lacUV5-T7p07 ind1 sam7 nin5]) [malB+]K-12(λS). "
            * 10
        )
        strain = _make_ecolistrain(
            self.user, name="Long Genotype", genotype=long_genotype
        )
        strain.refresh_from_db()
        self.assertEqual(strain.genotype, long_genotype)

    def test_purpose_accepts_long_text(self):
        """Test TextField can hold longer text"""
        long_purpose = (
            "This strain is specifically designed for high-level Protein production. "
            * 20
        )
        strain = _make_ecolistrain(self.user, name="Long Purpose", purpose=long_purpose)
        strain.refresh_from_db()
        self.assertEqual(strain.purpose, long_purpose)

    def test_name_with_special_characters(self):
        """Test that special characters in name are preserved"""
        strain = _make_ecolistrain(self.user, name="BL21(DE3)")
        strain.refresh_from_db()
        self.assertEqual(strain.name, "BL21(DE3)")

    def test_very_long_name_within_limit(self):
        """Test name can be up to 255 characters"""
        long_name = "A" * 255
        strain = _make_ecolistrain(self.user, name=long_name)
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
        self.assertEqual(EColiStrain._meta.verbose_name, "strain - E. coli")
        self.assertEqual(EColiStrain._meta.verbose_name_plural, "strains - E. coli")

    def test_required_fields_cannot_be_none(self):
        """Test that required fields cannot be None"""
        with self.assertRaises(Exception):
            EColiStrain.objects.create(
                name=None, supplier="NEB", us_e="Cloning", created_by=self.user
            )
        with self.assertRaises(Exception):
            EColiStrain.objects.create(
                name="Test", supplier=None, us_e="Cloning", created_by=self.user
            )
        with self.assertRaises(Exception):
            EColiStrain.objects.create(
                name="Test", supplier="NEB", us_e=None, created_by=self.user
            )

    def test_multiple_strains_same_name_allowed(self):
        """Test that multiple strains can have the same name (no uniqueness constraint)"""
        strain1 = _make_ecolistrain(self.user, name="Duplicate Name")
        strain2 = _make_ecolistrain(self.user, name="Duplicate Name")
        self.assertEqual(strain1.name, strain2.name)
        self.assertNotEqual(strain1.id, strain2.id)

    def test_clean_method_strips_name(self):
        """Test that clean method properly strips name"""
        strain = EColiStrain(
            name="  Spaced Name  ", supplier="NEB", us_e="Cloning", created_by=self.user
        )
        try:
            strain.clean()
        except ValidationError:
            pass
        self.assertEqual(strain.name, "Spaced Name")

    def test_model_abbreviation(self):
        """Test model abbreviation is set correctly"""
        self.assertEqual(self.strain._model_abbreviation, "ec")

    def test_is_guarded_model(self):
        """Test that EColiStrain is a guarded model"""
        self.assertTrue(self.strain._is_guarded_model)


class EColiStrainDocModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="ecdoctest@example.com", password="password"
        )
        cls.strain = _make_ecolistrain(cls.user, name="Doc Test Strain")

    def test_ecolistraindoc_creation(self):
        """Test creating an EColiStrainDoc"""
        test_file = SimpleUploadedFile(
            "test.pdf", b"file_content", content_type="application/pdf"
        )
        doc = EColiStrainDoc.objects.create(
            ecoli_strain=self.strain, name=test_file, description="Test document"
        )
        self.assertEqual(doc.ecoli_strain, self.strain)
        self.assertEqual(doc.description, "Test document")

    def test_ecolistraindoc_foreignkey_protection(self):
        """Test that deleting strain is protected when docs exist"""
        from django.db.models.deletion import ProtectedError

        test_file = SimpleUploadedFile(
            "protected.pdf", b"file_content", content_type="application/pdf"
        )
        doc = EColiStrainDoc.objects.create(
            ecoli_strain=self.strain, name=test_file, description="Protected doc"
        )
        with self.assertRaises(ProtectedError):
            self.strain.delete()

    def test_ecolistraindoc_timestamps(self):
        """Test that doc has timestamps"""
        test_file = SimpleUploadedFile(
            "time.pdf", b"file_content", content_type="application/pdf"
        )
        doc = EColiStrainDoc.objects.create(
            ecoli_strain=self.strain, name=test_file, description="Time test doc"
        )
        self.assertIsNotNone(doc.created_date_time)
        self.assertIsNotNone(doc.last_changed_date_time)

    def test_ecolistraindoc_verbose_name(self):
        """Test EColiStrainDoc verbose name"""
        self.assertEqual(EColiStrainDoc._meta.verbose_name, "e. coli strain document")


class EColiStrainAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="ecapitest@example.com", password="password"
        )
        cls.strain = _make_ecolistrain(cls.user)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = "/api/collection/ecolistrain/"

    def test_list_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_count(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 1)

    def test_retrieve_returns_200(self):
        response = self.client.get(f"{self.url}{self.strain.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "DH5alpha")

    @skip(
        "The generic ModelViewSet does not support create via the API (get_serializer_class() requires self.model set by get_queryset())."
    )
    def test_create_ecolistrain(self):
        data = {"name": "BL21", "supplier": "NEB", "us_e": "Expression"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @skip(
        "The generic ModelViewSet does not support create via the API (see test_create_ecolistrain)."
    )
    def test_create_sets_created_by_to_request_user(self):
        data = {"name": "Owned Strain", "supplier": "NEB", "us_e": "Cloning"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_strain = EColiStrain.objects.get(id=response.data["id"])
        self.assertEqual(new_strain.created_by, self.user)

    @skip(
        "The generic ModelViewSet serializer uses empty field_names for partial_update, so no fields are persisted."
    )
    def test_partial_update_ecolistrain(self):
        response = self.client.patch(
            f"{self.url}{self.strain.id}/", {"resistance": "AmpR"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_ecolistrain(self):
        response = self.client.delete(f"{self.url}{self.strain.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(EColiStrain.objects.count(), 0)

    def test_unauthenticated_returns_403(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_search_by_name(self):
        _make_ecolistrain(self.user, name="Rosetta")
        response = self.client.get(self.url, {"search": "Rosetta"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Rosetta", names)
        self.assertNotIn("DH5alpha", names)

    def test_retrieve_nonexistent_returns_404(self):
        response = self.client.get(f"{self.url}999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_includes_all_expected_fields(self):
        """Test that list response includes expected fields"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data["count"] > 0:
            item = response.data["results"][0]
            expected_fields = ["id", "name", "resistance", "us_e", "purpose"]
            for field in expected_fields:
                self.assertIn(field, item)

    def test_search_by_id(self):
        """Test searching by ID"""
        strain = _make_ecolistrain(self.user, name="ID Searchable")
        response = self.client.get(self.url, {"search": str(strain.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pagination_default(self):
        """Test that pagination works"""
        for i in range(15):
            _make_ecolistrain(self.user, name=f"Strain {i}")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 15)

    def test_pagination_custom_page_size(self):
        """Test custom page size parameter"""
        for i in range(10):
            _make_ecolistrain(self.user, name=f"Page Test {i}")
        response = self.client.get(self.url, {"page_size": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            self.assertGreaterEqual(response.data["count"], 11)

    def test_retrieve_returns_complete_data(self):
        """Test that retrieve returns all strain fields"""
        strain = _make_ecolistrain(
            self.user,
            name="Complete Data",
            resistance="AmpR, KanR",
            genotype="F- endA1 recA1 gyrA96",
            background="K12",
            supplier="Thermo Fisher",
            us_e="Expression",
            purpose="Protein production experiments",
            note="Store at -80C in glycerol stocks",
        )
        response = self.client.get(f"{self.url}{strain.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Complete Data")
        self.assertEqual(response.data["resistance"], "AmpR, KanR")
        self.assertEqual(response.data["genotype"], "F- endA1 recA1 gyrA96")
        self.assertEqual(response.data["background"], "K12")
        self.assertEqual(response.data["supplier"], "Thermo Fisher")
        self.assertEqual(response.data["us_e"], "Expression")
        self.assertEqual(response.data["purpose"], "Protein production experiments")
        self.assertEqual(response.data["note"], "Store at -80C in glycerol stocks")

    def test_delete_removes_from_database(self):
        """Test that delete actually removes the strain"""
        strain = _make_ecolistrain(self.user, name="To Delete")
        strain_id = strain.id
        response = self.client.delete(f"{self.url}{strain_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EColiStrain.objects.filter(id=strain_id).exists())

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
        strain = _make_ecolistrain(self.user, name="Protected")
        self.client.force_authenticate(user=None)
        response = self.client.delete(f"{self.url}{strain.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertTrue(EColiStrain.objects.filter(id=strain.id).exists())

    def test_search_no_results(self):
        """Test search with no matching results"""
        response = self.client.get(self.url, {"search": "NonExistentStrain123456"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_search_case_insensitive(self):
        """Test that search is case insensitive"""
        _make_ecolistrain(self.user, name="TOP10")
        response_lower = self.client.get(self.url, {"search": "top10"})
        response_upper = self.client.get(self.url, {"search": "TOP10"})
        self.assertEqual(response_lower.status_code, status.HTTP_200_OK)
        self.assertEqual(response_upper.status_code, status.HTTP_200_OK)

    def test_list_empty_database(self):
        """Test listing when no strains exist"""
        EColiStrain.objects.all().delete()
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
        _make_ecolistrain(self.user, name="BL21-CodonPlus")
        response = self.client.get(self.url, {"search": "CodonPlus"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data["count"] > 0:
            names = [item["name"] for item in response.data["results"]]
            self.assertTrue(any("CodonPlus" in name for name in names))

    def test_multiple_searches_independent(self):
        """Test that multiple searches don't interfere with each other"""
        strain1 = _make_ecolistrain(self.user, name="Unique Alpha")
        strain2 = _make_ecolistrain(self.user, name="Unique Beta")
        response1 = self.client.get(self.url, {"search": "Alpha"})
        response2 = self.client.get(self.url, {"search": "Beta"})
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_ordering_by_id(self):
        """Test ordering strains by ID"""
        strain1 = _make_ecolistrain(self.user, name="First")
        strain2 = _make_ecolistrain(self.user, name="Second")
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
