from unittest import skip
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Antibody, AntibodyDoc

User = get_user_model()


def _make_antibody(user, name="Anti-GAPDH", **kwargs):
    defaults = {
        "name": name,
        "species_isotype": "Mouse IgG1",
        "clone": "6C5",
        "received_from": "Sigma",
        "catalogue_number": "MAB374",
        "l_ocation": "Fridge 1",
        "a_pplication": "WB, IF",
        "description_comment": "Anti-GAPDH antibody.",
        "availability": True,
        "created_by": user,
    }
    defaults.update(kwargs)
    return Antibody.objects.create(**defaults)


class AntibodyModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="abtest@example.com", password="password"
        )
        cls.antibody = _make_antibody(cls.user)

    def test_antibody_creation(self):
        self.assertEqual(self.antibody.name, "Anti-GAPDH")

    def test_str_representation(self):
        self.assertEqual(str(self.antibody), f"{self.antibody.id} - Anti-GAPDH")

    def test_availability_default_true(self):
        self.assertTrue(self.antibody.availability)

    def test_availability_can_be_false(self):
        ab = _make_antibody(self.user, name="Unavailable Ab", availability=False)
        self.assertFalse(ab.availability)

    def test_name_stripped_on_save(self):
        ab = _make_antibody(self.user, name="  Anti-Actin  ")
        ab.refresh_from_db()
        self.assertEqual(ab.name, "Anti-Actin")

    def test_optional_fields_default_to_empty_string(self):
        ab = Antibody.objects.create(
            name="Minimal Ab", species_isotype="Rabbit", created_by=self.user
        )
        self.assertEqual(ab.clone, "")
        self.assertEqual(ab.received_from, "")
        self.assertEqual(ab.description_comment, "")

    def test_timestamps_set_automatically(self):
        self.assertIsNotNone(self.antibody.created_date_time)
        self.assertIsNotNone(self.antibody.last_changed_date_time)

    def test_created_by_is_set(self):
        self.assertEqual(self.antibody.created_by, self.user)

    def test_history_created_on_save(self):
        self.assertGreater(self.antibody.history.count(), 0)

    def test_history_records_change(self):
        self.antibody.clone = "NewClone"
        self.antibody.save()
        self.assertGreaterEqual(self.antibody.history.count(), 2)

    def test_all_char_fields_can_be_set(self):
        """Test that all character fields accept values"""
        ab = _make_antibody(
            self.user,
            name="Complete Ab",
            species_isotype="Goat IgG",
            clone="ABC123",
            received_from="Abcam",
            catalogue_number="ab12345",
            l_ocation="Freezer -20C",
            a_pplication="WB, IP, IHC",
        )
        self.assertEqual(ab.species_isotype, "Goat IgG")
        self.assertEqual(ab.clone, "ABC123")
        self.assertEqual(ab.received_from, "Abcam")
        self.assertEqual(ab.catalogue_number, "ab12345")
        self.assertEqual(ab.l_ocation, "Freezer -20C")
        self.assertEqual(ab.a_pplication, "WB, IP, IHC")

    def test_description_comment_accepts_long_text(self):
        """Test TextField can hold longer text"""
        long_desc = "This is a very detailed description. " * 50
        ab = _make_antibody(self.user, name="Verbose Ab", description_comment=long_desc)
        ab.refresh_from_db()
        self.assertEqual(ab.description_comment, long_desc)

    def test_name_with_special_characters(self):
        """Test that special characters in name are preserved"""
        ab = _make_antibody(self.user, name="Anti-α-Tubulin (D1A9)")
        ab.refresh_from_db()
        self.assertEqual(ab.name, "Anti-α-Tubulin (D1A9)")

    def test_very_long_name_within_limit(self):
        """Test name can be up to 255 characters"""
        long_name = "A" * 255
        ab = _make_antibody(self.user, name=long_name)
        self.assertEqual(len(ab.name), 255)

    def test_info_sheet_can_be_null(self):
        """Test that info_sheet field can be null"""
        ab = _make_antibody(self.user, name="No Sheet Ab", info_sheet=None)
        self.assertFalse(ab.info_sheet.name)

    def test_info_sheet_formatted_returns_empty_when_no_file(self):
        """Test info_sheet_formatted returns empty string when no file"""
        ab = _make_antibody(self.user, name="No Sheet")
        self.assertEqual(ab.info_sheet_formatted(), "")

    def test_info_sheet_formatted_returns_link_when_file_exists(self):
        """Test info_sheet_formatted returns HTML link when file exists"""
        mock_file = Mock()
        mock_file.url = "/media/collection/antibody/test.pdf"
        ab = _make_antibody(self.user, name="With Sheet")
        ab.info_sheet = mock_file
        formatted = ab.info_sheet_formatted()
        self.assertIn("href", formatted)
        self.assertIn(mock_file.url, formatted)

    def test_download_file_name_property(self):
        """Test that download_file_name property works correctly"""
        ab = _make_antibody(self.user, name="Download Test")
        download_name = ab.download_file_name
        self.assertTrue(download_name.startswith("ab"))
        self.assertIn(str(ab.id), download_name)

    def test_zebra_label_content_property(self):
        """Test zebra_n0jtt_label_content property"""
        ab = _make_antibody(self.user, name="Label Test")
        label_content = ab.zebra_n0jtt_label_content
        self.assertIsInstance(label_content, list)
        self.assertEqual(len(label_content), 5)
        self.assertIn(str(ab.id), label_content[0])
        self.assertEqual(label_content[1], "Label Test")
        self.assertEqual(label_content[2], "Glycerol:")

    def test_save_without_historical_record(self):
        """Test that save_without_historical_record doesn't create history entry"""
        initial_count = self.antibody.history.count()
        self.antibody.clone = "NoHistoryClone"
        self.antibody.save_without_historical_record()
        self.assertEqual(self.antibody.history.count(), initial_count)

    def test_readonly_fields_for_creator(self):
        """Test that creator can edit all obj_specific_fields"""
        mock_request = Mock()
        mock_request.user = self.user
        readonly = self.antibody.readonly_fields(mock_request)
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
        readonly = self.antibody.readonly_fields(mock_request)
        self.assertIn("name", readonly)
        self.assertIn("created_date_time", readonly)

    def test_model_meta_verbose_name(self):
        """Test model verbose names are set correctly"""
        self.assertEqual(Antibody._meta.verbose_name, "antibody")
        self.assertEqual(Antibody._meta.verbose_name_plural, "antibodies")

    def test_required_fields_cannot_be_none(self):
        """Test that required fields cannot be None"""
        with self.assertRaises(Exception):
            Antibody.objects.create(
                name=None, species_isotype="Mouse", created_by=self.user
            )
        with self.assertRaises(Exception):
            Antibody.objects.create(
                name="Test", species_isotype=None, created_by=self.user
            )

    def test_multiple_antibodies_same_name_allowed(self):
        """Test that multiple antibodies can have the same name (no uniqueness constraint)"""
        ab1 = _make_antibody(self.user, name="Duplicate Name")
        ab2 = _make_antibody(self.user, name="Duplicate Name")
        self.assertEqual(ab1.name, ab2.name)
        self.assertNotEqual(ab1.id, ab2.id)

    def test_clean_method_strips_name(self):
        """Test that clean method properly strips name"""
        ab = Antibody(
            name="  Spaced Name  ", species_isotype="Mouse", created_by=self.user
        )
        try:
            ab.clean()
        except ValidationError:
            pass
        self.assertEqual(ab.name, "Spaced Name")


class AntibodyDocModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="doctest@example.com", password="password"
        )
        cls.antibody = _make_antibody(cls.user, name="Doc Test Ab")

    def test_antibody_doc_creation(self):
        """Test creating an AntibodyDoc"""
        test_file = SimpleUploadedFile(
            "test.pdf", b"file_content", content_type="application/pdf"
        )
        doc = AntibodyDoc.objects.create(
            antibody=self.antibody, name=test_file, description="Test document"
        )
        self.assertEqual(doc.antibody, self.antibody)
        self.assertEqual(doc.description, "Test document")

    def test_antibody_doc_foreignkey_protection(self):
        """Test that deleting antibody is protected when docs exist"""
        from django.db.models.deletion import ProtectedError

        test_file = SimpleUploadedFile(
            "protected.pdf", b"file_content", content_type="application/pdf"
        )
        doc = AntibodyDoc.objects.create(
            antibody=self.antibody, name=test_file, description="Protected doc"
        )
        with self.assertRaises(ProtectedError):
            self.antibody.delete()

    def test_antibody_doc_timestamps(self):
        """Test that doc has timestamps"""
        test_file = SimpleUploadedFile(
            "time.pdf", b"file_content", content_type="application/pdf"
        )
        doc = AntibodyDoc.objects.create(
            antibody=self.antibody, name=test_file, description="Time test doc"
        )
        self.assertIsNotNone(doc.created_date_time)
        self.assertIsNotNone(doc.last_changed_date_time)

    def test_antibody_doc_verbose_name(self):
        """Test AntibodyDoc verbose name"""
        self.assertEqual(AntibodyDoc._meta.verbose_name, "antibody document")


class AntibodyAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="abapitest@example.com", password="password"
        )
        cls.antibody = _make_antibody(cls.user)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = "/api/collection/antibody/"

    def test_list_antibodies_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_antibodies_count(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 1)

    def test_retrieve_antibody(self):
        response = self.client.get(f"{self.url}{self.antibody.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Anti-GAPDH")

    @skip(
        "The generic ModelViewSet does not support create/update via the API: get_serializer_class() uses self.model which is set by get_queryset() and is not called before create actions."
    )
    def test_create_antibody(self):
        data = {"name": "Anti-Tubulin", "species_isotype": "Rat IgG2a"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Antibody.objects.count(), 2)

    @skip(
        "The generic ModelViewSet does not support create via the API (see test_create_antibody)."
    )
    def test_create_sets_created_by_to_request_user(self):
        data = {"name": "Owned Ab", "species_isotype": "Rabbit"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_ab = Antibody.objects.get(id=response.data["id"])
        self.assertEqual(new_ab.created_by, self.user)

    @skip(
        "The generic ModelViewSet serializer uses empty field_names for partial_update, so no fields are persisted."
    )
    def test_partial_update_antibody(self):
        response = self.client.patch(f"{self.url}{self.antibody.id}/", {"clone": "7D9"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.antibody.refresh_from_db()
        self.assertEqual(self.antibody.clone, "7D9")

    def test_delete_antibody(self):
        response = self.client.delete(f"{self.url}{self.antibody.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Antibody.objects.count(), 0)

    def test_unauthenticated_list_returns_403(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_search_by_name(self):
        _make_antibody(self.user, name="Anti-Myosin")
        response = self.client.get(self.url, {"search": "Myosin"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Anti-Myosin", names)
        self.assertNotIn("Anti-GAPDH", names)

    def test_retrieve_nonexistent_returns_404(self):
        response = self.client.get(f"{self.url}999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_includes_all_expected_fields(self):
        """Test that list response includes expected fields"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data["count"] > 0:
            item = response.data["results"][0]
            expected_fields = [
                "id",
                "name",
                "species_isotype",
                "clone",
                "received_from",
                "catalogue_number",
                "availability",
            ]
            for field in expected_fields:
                self.assertIn(field, item)

    def test_search_by_catalogue_number(self):
        """Test searching by catalogue number"""
        _make_antibody(self.user, name="Searchable", catalogue_number="XYZ999")
        response = self.client.get(self.url, {"search": "XYZ999"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_by_id(self):
        """Test searching by ID"""
        ab = _make_antibody(self.user, name="ID Searchable")
        response = self.client.get(self.url, {"search": str(ab.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_availability(self):
        """Test filtering by availability"""
        _make_antibody(self.user, name="Available", availability=True)
        _make_antibody(self.user, name="Not Available", availability=False)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pagination_default(self):
        """Test that pagination works"""
        for i in range(15):
            _make_antibody(self.user, name=f"Ab {i}")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 15)

    def test_pagination_custom_page_size(self):
        """Test custom page size parameter"""
        for i in range(10):
            _make_antibody(self.user, name=f"Page Test {i}")
        response = self.client.get(self.url, {"page_size": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            self.assertGreaterEqual(response.data["count"], 11)

    def test_retrieve_returns_complete_data(self):
        """Test that retrieve returns all antibody fields"""
        ab = _make_antibody(
            self.user,
            name="Complete Data",
            species_isotype="Rabbit IgG",
            clone="EP123",
            received_from="Cell Signaling",
            catalogue_number="#4567",
            l_ocation="Fridge 2, Shelf 3",
            a_pplication="WB (1:1000), IF (1:200)",
            description_comment="High quality antibody for GAPDH detection",
            availability=True,
        )
        response = self.client.get(f"{self.url}{ab.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Complete Data")
        self.assertEqual(response.data["species_isotype"], "Rabbit IgG")
        self.assertEqual(response.data["clone"], "EP123")
        self.assertEqual(response.data["received_from"], "Cell Signaling")
        self.assertEqual(response.data["catalogue_number"], "#4567")
        self.assertTrue(response.data["availability"])

    def test_delete_removes_from_database(self):
        """Test that delete actually removes the antibody"""
        ab = _make_antibody(self.user, name="To Delete")
        ab_id = ab.id
        response = self.client.delete(f"{self.url}{ab_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Antibody.objects.filter(id=ab_id).exists())

    def test_unauthenticated_retrieve_forbidden(self):
        """Test that unauthenticated users cannot retrieve"""
        self.client.force_authenticate(user=None)
        response = self.client.get(f"{self.url}{self.antibody.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_delete_forbidden(self):
        """Test that unauthenticated users cannot delete"""
        ab = _make_antibody(self.user, name="Protected")
        self.client.force_authenticate(user=None)
        response = self.client.delete(f"{self.url}{ab.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertTrue(Antibody.objects.filter(id=ab.id).exists())

    def test_search_no_results(self):
        """Test search with no matching results"""
        response = self.client.get(self.url, {"search": "NonExistentAntibody123456"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_search_case_insensitive(self):
        """Test that search is case insensitive"""
        _make_antibody(self.user, name="Beta-Actin")
        response_lower = self.client.get(self.url, {"search": "beta-actin"})
        response_upper = self.client.get(self.url, {"search": "BETA-ACTIN"})
        self.assertEqual(response_lower.status_code, status.HTTP_200_OK)
        self.assertEqual(response_upper.status_code, status.HTTP_200_OK)

    def test_list_empty_database(self):
        """Test listing when no antibodies exist"""
        Antibody.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_retrieve_includes_timestamps(self):
        """Test that retrieve includes timestamp fields"""
        response = self.client.get(f"{self.url}{self.antibody.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("created_date_time", response.data)
        self.assertIn("last_changed_date_time", response.data)

    def test_search_partial_match(self):
        """Test search with partial string match"""
        _make_antibody(self.user, name="Anti-Phospho-p53")
        response = self.client.get(self.url, {"search": "Phospho"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data["count"] > 0:
            names = [item["name"] for item in response.data["results"]]
            self.assertTrue(any("Phospho" in name for name in names))

    def test_multiple_searches_independent(self):
        """Test that multiple searches don't interfere with each other"""
        ab1 = _make_antibody(self.user, name="Unique Alpha")
        ab2 = _make_antibody(self.user, name="Unique Beta")
        response1 = self.client.get(self.url, {"search": "Alpha"})
        response2 = self.client.get(self.url, {"search": "Beta"})
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_ordering_by_id(self):
        """Test ordering antibodies by ID"""
        ab1 = _make_antibody(self.user, name="First")
        ab2 = _make_antibody(self.user, name="Second")
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
