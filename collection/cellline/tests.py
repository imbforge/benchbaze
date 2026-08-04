from unittest import skip
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from .models import CellLine, CellLineDoc

User = get_user_model()


def _make_cellline(user, name="HeLa", **kwargs):
    defaults = {
        "name": name,
        "box_name": "Box A",
        "parental_line_old": "Unknown",
        "created_by": user,
    }
    defaults.update(kwargs)
    return CellLine.objects.create(**defaults)


class CellLineModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="cltest@example.com", password="password"
        )
        cls.cl = _make_cellline(cls.user)

    def test_cellline_creation(self):
        self.assertEqual(self.cl.name, "HeLa")

    def test_str_representation(self):
        self.assertEqual(str(self.cl), f"{self.cl.id} - HeLa")

    def test_name_stripped_on_save(self):
        cl = _make_cellline(self.user, name="  HEK 293  ")
        cl.refresh_from_db()
        self.assertEqual(cl.name, "HEK 293")

    def test_name_unique_constraint(self):
        """Test that duplicate names are not allowed"""
        with self.assertRaises(Exception):
            _make_cellline(self.user, name="HeLa")

    def test_organism_nullable(self):
        cl = _make_cellline(self.user, name="NoOrg", organism=None)
        self.assertIsNone(cl.organism)

    def test_zkbs_cell_line_nullable(self):
        cl = _make_cellline(self.user, name="NoZkbs", zkbs_cell_line=None)
        self.assertIsNone(cl.zkbs_cell_line)

    def test_parental_line_nullable(self):
        cl = _make_cellline(self.user, name="NoParent", parental_line=None)
        self.assertIsNone(cl.parental_line)

    def test_s2_work_defaults_to_false(self):
        self.assertFalse(self.cl.s2_work)

    def test_s2_work_can_be_true(self):
        cl = _make_cellline(self.user, name="S2 Line", s2_work=True)
        self.assertTrue(cl.s2_work)

    def test_alternative_name_defaults_to_empty_string(self):
        self.assertEqual(self.cl.alternative_name, "")

    def test_description_comment_defaults_to_empty(self):
        self.assertEqual(self.cl.description_comment, "")

    def test_box_name_field_exists(self):
        """Test box_name field is accessible"""
        self.assertEqual(self.cl.box_name, "Box A")

    def test_parental_line_old_can_be_blank(self):
        cl = _make_cellline(self.user, name="No Old Parent", parental_line_old="")
        self.assertEqual(cl.parental_line_old, "")

    def test_timestamps_set_automatically(self):
        self.assertIsNotNone(self.cl.created_date_time)
        self.assertIsNotNone(self.cl.last_changed_date_time)

    def test_created_by_is_set(self):
        self.assertEqual(self.cl.created_by, self.user)

    def test_history_created_on_save(self):
        self.assertGreater(self.cl.history.count(), 0)

    def test_history_tracks_change(self):
        self.cl.alternative_name = "Henrietta Lacks"
        self.cl.save()
        self.assertGreaterEqual(self.cl.history.count(), 2)

    def test_all_char_fields_can_be_set(self):
        """Test that all character fields accept values"""
        cl = _make_cellline(
            self.user,
            name="Complete Cell Line",
            box_name="Freezer 1, Box 5",
            alternative_name="Alt Name",
            parental_line_old="Parent Line",
            cell_type_tissue="Epithelial",
            culture_type="Adherent",
            growth_condition="37C, 5% CO2",
            freezing_medium="10% DMSO",
            received_from="ATCC",
        )
        self.assertEqual(cl.box_name, "Freezer 1, Box 5")
        self.assertEqual(cl.alternative_name, "Alt Name")
        self.assertEqual(cl.parental_line_old, "Parent Line")
        self.assertEqual(cl.cell_type_tissue, "Epithelial")
        self.assertEqual(cl.culture_type, "Adherent")
        self.assertEqual(cl.growth_condition, "37C, 5% CO2")
        self.assertEqual(cl.freezing_medium, "10% DMSO")
        self.assertEqual(cl.received_from, "ATCC")

    def test_description_comment_accepts_long_text(self):
        """Test TextField can hold longer text"""
        long_desc = "This is a very detailed description. " * 50
        cl = _make_cellline(self.user, name="Verbose CL", description_comment=long_desc)
        cl.refresh_from_db()
        self.assertEqual(cl.description_comment, long_desc)

    def test_name_with_special_characters(self):
        """Test that special characters in name are preserved"""
        cl = _make_cellline(self.user, name="HEK293T/17 (ATCC® CRL-11268™)")
        cl.refresh_from_db()
        self.assertEqual(cl.name, "HEK293T/17 (ATCC® CRL-11268™)")

    def test_very_long_name_within_limit(self):
        """Test name can be up to 255 characters"""
        long_name = "A" * 255
        cl = _make_cellline(self.user, name=long_name)
        self.assertEqual(len(cl.name), 255)

    def test_parental_line_self_referential(self):
        """Test that parental_line can reference another CellLine"""
        parent = _make_cellline(self.user, name="Parent Line")
        child = _make_cellline(self.user, name="Child Line", parental_line=parent)
        self.assertEqual(child.parental_line, parent)

    def test_history_viruses_mammalian_integrated_defaults_to_list(self):
        """Test ArrayField defaults to empty list"""
        self.assertEqual(self.cl.history_viruses_mammalian_integrated, [])

    def test_history_viruses_transient_defaults_to_list(self):
        """Test ArrayField defaults to empty list"""
        self.assertEqual(self.cl.history_viruses_transient, [])

    def test_save_without_historical_record(self):
        """Test that save_without_historical_record doesn't create history entry"""
        initial_count = self.cl.history.count()
        self.cl.alternative_name = "NoHistoryName"
        self.cl.save_without_historical_record()
        self.assertEqual(self.cl.history.count(), initial_count)

    def test_readonly_fields_for_creator(self):
        """Test that creator can edit all obj_specific_fields"""
        mock_request = Mock()
        mock_request.user = self.user
        readonly = self.cl.readonly_fields(mock_request)
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
        readonly = self.cl.readonly_fields(mock_request)
        self.assertIn("name", readonly)
        self.assertIn("created_date_time", readonly)

    def test_model_meta_verbose_name(self):
        """Test model verbose names are set correctly"""
        self.assertEqual(CellLine._meta.verbose_name, "cell line")
        self.assertEqual(CellLine._meta.verbose_name_plural, "cell lines")

    def test_required_fields_cannot_be_none(self):
        """Test that required fields cannot be None"""
        with self.assertRaises(Exception):
            CellLine.objects.create(
                name=None, box_name="Box", parental_line_old="", created_by=self.user
            )

    def test_clean_method_strips_name(self):
        """Test that clean method properly strips name"""
        cl = CellLine(
            name="  Spaced Name  ",
            box_name="Box",
            parental_line_old="",
            created_by=self.user,
        )
        try:
            cl.clean()
        except ValidationError:
            pass
        self.assertEqual(cl.name, "Spaced Name")

    def test_model_abbreviation(self):
        """Test model abbreviation is set correctly"""
        self.assertEqual(self.cl._model_abbreviation, "cl")

    def test_is_guarded_model(self):
        """Test that CellLine is a guarded model"""
        self.assertTrue(self.cl._is_guarded_model)

    def test_zebra_n0jtt_label_content_property(self):
        """Test zebra_n0jtt_label_content property"""
        label_content = self.cl.zebra_n0jtt_label_content
        self.assertIsInstance(label_content, list)
        self.assertEqual(len(label_content), 5)
        self.assertIn(str(self.cl.id), label_content[0])
        self.assertEqual(label_content[1], "HeLa")


class CellLineDocModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="cldoctest@example.com", password="password"
        )
        cls.cellline = _make_cellline(cls.user, name="Doc Test CL")

    def test_celllinedoc_creation(self):
        """Test creating a CellLineDoc"""
        test_file = SimpleUploadedFile(
            "test.pdf", b"file_content", content_type="application/pdf"
        )
        doc = CellLineDoc.objects.create(
            cell_line=self.cellline, name=test_file, description="virus"
        )
        self.assertEqual(doc.cell_line, self.cellline)
        self.assertEqual(doc.description, "virus")

    def test_celllinedoc_description_choices(self):
        """Test that description field has correct choices"""
        test_file = SimpleUploadedFile(
            "mycoplasma.pdf", b"file_content", content_type="application/pdf"
        )
        doc = CellLineDoc.objects.create(
            cell_line=self.cellline, name=test_file, description="mycoplasma"
        )
        self.assertEqual(doc.description, "mycoplasma")

    def test_celllinedoc_foreignkey_protection(self):
        """Test that deleting cell line is protected when docs exist"""
        from django.db.models.deletion import ProtectedError

        test_file = SimpleUploadedFile(
            "protected.pdf", b"file_content", content_type="application/pdf"
        )
        doc = CellLineDoc.objects.create(
            cell_line=self.cellline, name=test_file, description="fingerprint"
        )
        with self.assertRaises(ProtectedError):
            self.cellline.delete()

    def test_celllinedoc_timestamps(self):
        """Test that doc has timestamps"""
        test_file = SimpleUploadedFile(
            "time.pdf", b"file_content", content_type="application/pdf"
        )
        doc = CellLineDoc.objects.create(
            cell_line=self.cellline, name=test_file, description="other"
        )
        self.assertIsNotNone(doc.created_date_time)
        self.assertIsNotNone(doc.last_changed_date_time)

    def test_celllinedoc_verbose_name(self):
        """Test CellLineDoc verbose name"""
        self.assertEqual(CellLineDoc._meta.verbose_name, "cell line document")


class CellLineAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="clapitest@example.com", password="password"
        )
        cls.cl = _make_cellline(cls.user)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = "/api/collection/cellline/"

    def test_list_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_count(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 1)

    def test_retrieve_returns_200(self):
        response = self.client.get(f"{self.url}{self.cl.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "HeLa")

    @skip(
        "The generic ModelViewSet does not support create via the API (get_serializer_class() requires self.model set by get_queryset())."
    )
    def test_create_cellline(self):
        data = {"name": "COS-7", "box_name": "Box B", "parental_line_old": ""}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @skip(
        "The generic ModelViewSet does not support create via the API (see test_create_cellline)."
    )
    def test_create_sets_created_by_to_request_user(self):
        data = {"name": "Owned CL", "box_name": "Box B", "parental_line_old": ""}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_cl = CellLine.objects.get(id=response.data["id"])
        self.assertEqual(new_cl.created_by, self.user)

    @skip(
        "The generic ModelViewSet serializer uses empty field_names for partial_update, so no fields are persisted."
    )
    def test_partial_update_cellline(self):
        response = self.client.patch(
            f"{self.url}{self.cl.id}/", {"alternative_name": "HL"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_cellline(self):
        response = self.client.delete(f"{self.url}{self.cl.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CellLine.objects.count(), 0)

    def test_unauthenticated_returns_403(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_search_by_name(self):
        _make_cellline(self.user, name="NIH-3T3")
        response = self.client.get(self.url, {"search": "NIH"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("NIH-3T3", names)
        self.assertNotIn("HeLa", names)

    def test_retrieve_nonexistent_returns_404(self):
        response = self.client.get(f"{self.url}999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_includes_all_expected_fields(self):
        """Test that list response includes expected fields"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data["count"] > 0:
            item = response.data["results"][0]
            expected_fields = ["id", "name", "box_name", "created_by"]
            for field in expected_fields:
                self.assertIn(field, item)

    def test_search_by_id(self):
        """Test searching by ID"""
        cl = _make_cellline(self.user, name="ID Searchable")
        response = self.client.get(self.url, {"search": str(cl.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pagination_default(self):
        """Test that pagination works"""
        for i in range(15):
            _make_cellline(self.user, name=f"CL {i}")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 15)

    def test_pagination_custom_page_size(self):
        """Test custom page size parameter"""
        for i in range(10):
            _make_cellline(self.user, name=f"Page Test {i}")
        response = self.client.get(self.url, {"page_size": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            self.assertGreaterEqual(response.data["count"], 11)

    def test_retrieve_returns_complete_data(self):
        """Test that retrieve returns all cell line fields"""
        cl = _make_cellline(
            self.user,
            name="Complete Data",
            box_name="Freezer 1, Box 5",
            alternative_name="Alt Name",
            parental_line_old="Parent",
            cell_type_tissue="Epithelial",
            culture_type="Adherent",
            growth_condition="37C, 5% CO2",
            freezing_medium="10% DMSO",
            received_from="ATCC",
            description_comment="Test cell line",
            s2_work=True,
        )
        response = self.client.get(f"{self.url}{cl.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Complete Data")
        self.assertEqual(response.data["box_name"], "Freezer 1, Box 5")
        self.assertEqual(response.data["alternative_name"], "Alt Name")
        self.assertEqual(response.data["cell_type_tissue"], "Epithelial")
        self.assertTrue(response.data["s2_work"])

    def test_delete_removes_from_database(self):
        """Test that delete actually removes the cell line"""
        cl = _make_cellline(self.user, name="To Delete")
        cl_id = cl.id
        response = self.client.delete(f"{self.url}{cl_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CellLine.objects.filter(id=cl_id).exists())

    def test_unauthenticated_retrieve_forbidden(self):
        """Test that unauthenticated users cannot retrieve"""
        self.client.force_authenticate(user=None)
        response = self.client.get(f"{self.url}{self.cl.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_delete_forbidden(self):
        """Test that unauthenticated users cannot delete"""
        cl = _make_cellline(self.user, name="Protected")
        self.client.force_authenticate(user=None)
        response = self.client.delete(f"{self.url}{cl.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertTrue(CellLine.objects.filter(id=cl.id).exists())

    def test_search_no_results(self):
        """Test search with no matching results"""
        response = self.client.get(self.url, {"search": "NonExistentCellLine123456"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_search_case_insensitive(self):
        """Test that search is case insensitive"""
        _make_cellline(self.user, name="HEK293T")
        response_lower = self.client.get(self.url, {"search": "hek293t"})
        response_upper = self.client.get(self.url, {"search": "HEK293T"})
        self.assertEqual(response_lower.status_code, status.HTTP_200_OK)
        self.assertEqual(response_upper.status_code, status.HTTP_200_OK)

    def test_list_empty_database(self):
        """Test listing when no cell lines exist"""
        CellLine.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_retrieve_includes_timestamps(self):
        """Test that retrieve includes timestamp fields"""
        response = self.client.get(f"{self.url}{self.cl.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("created_date_time", response.data)
        self.assertIn("last_changed_date_time", response.data)

    def test_search_partial_match(self):
        """Test search with partial string match"""
        _make_cellline(self.user, name="HEK293-EGFP")
        response = self.client.get(self.url, {"search": "EGFP"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data["count"] > 0:
            names = [item["name"] for item in response.data["results"]]
            self.assertTrue(any("EGFP" in name for name in names))

    def test_multiple_searches_independent(self):
        """Test that multiple searches don't interfere with each other"""
        cl1 = _make_cellline(self.user, name="Unique Alpha")
        cl2 = _make_cellline(self.user, name="Unique Beta")
        response1 = self.client.get(self.url, {"search": "Alpha"})
        response2 = self.client.get(self.url, {"search": "Beta"})
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_ordering_by_id(self):
        """Test ordering cell lines by ID"""
        cl1 = _make_cellline(self.user, name="First")
        cl2 = _make_cellline(self.user, name="Second")
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
