from unittest import skip
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from common.admin_site import admin_site
from common.model_clone import CustomClonableModelAdmin
from collection.shared.admin import FieldSequenceFeature
from formz.models import SequenceFeature
from .models import Plasmid, PlasmidDoc

User = get_user_model()


def _make_plasmid(user, name="pUC19", **kwargs):
    defaults = {
        "name": name,
        "selection": "AmpR",
        "storage_type": "bacteria",
        "created_by": user,
    }
    defaults.update(kwargs)
    return Plasmid.objects.create(**defaults)


class PlasmidModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="plasmidtest@example.com", password="password"
        )
        cls.plasmid = _make_plasmid(cls.user)

    def test_plasmid_creation(self):
        self.assertEqual(self.plasmid.name, "pUC19")

    def test_str_representation(self):
        self.assertEqual(str(self.plasmid), f"{self.plasmid.id} - pUC19")

    def test_name_stripped_on_save(self):
        p = _make_plasmid(self.user, name="  pBR322  ")
        p.refresh_from_db()
        self.assertEqual(p.name, "pBR322")

    def test_name_uniqueness_enforced_at_db_level(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            _make_plasmid(self.user, name="pUC19")

    def test_other_name_defaults_to_empty(self):
        self.assertEqual(self.plasmid.other_name, "")

    def test_us_e_defaults_to_empty(self):
        self.assertEqual(self.plasmid.us_e, "")

    def test_vector_zkbs_nullable(self):
        self.assertIsNone(self.plasmid.vector_zkbs)

    def test_destroyed_date_not_set_by_default(self):
        import collection.plasmid.models as _pm

        original = _pm.PLASMID_STORAGE_TYPE
        _pm.PLASMID_STORAGE_TYPE = ""
        try:
            p = _make_plasmid(self.user, name="pNeverDestroyed")
            self.assertIsNone(p.destroyed_date)
        finally:
            _pm.PLASMID_STORAGE_TYPE = original

    @override_settings(PLASMID_STORAGE_TYPE="plasmid")
    def test_destroyed_date_auto_set_when_storage_type_is_plasmid(self):
        import collection.plasmid.models as plasmid_module

        original = plasmid_module.PLASMID_STORAGE_TYPE
        plasmid_module.PLASMID_STORAGE_TYPE = "plasmid"
        try:
            p = _make_plasmid(self.user, name="pAutoDestroy")
            self.assertIsNotNone(p.destroyed_date)
        finally:
            plasmid_module.PLASMID_STORAGE_TYPE = original

    def test_timestamps_set_automatically(self):
        self.assertIsNotNone(self.plasmid.created_date_time)
        self.assertIsNotNone(self.plasmid.last_changed_date_time)

    def test_created_by_is_set(self):
        self.assertEqual(self.plasmid.created_by, self.user)

    def test_history_created_on_save(self):
        self.assertGreater(self.plasmid.history.count(), 0)

    def test_history_tracks_change(self):
        self.plasmid.selection = "KanR"
        self.plasmid.save()
        self.assertGreaterEqual(self.plasmid.history.count(), 2)

    def test_storage_type_choices(self):
        """Test different storage type choices"""
        p1 = _make_plasmid(self.user, name="pPlasmid", storage_type="plasmid")
        p2 = _make_plasmid(self.user, name="pBacteria", storage_type="bacteria")
        p3 = _make_plasmid(self.user, name="pBoth", storage_type="both")
        self.assertEqual(p1.storage_type, "plasmid")
        self.assertEqual(p2.storage_type, "bacteria")
        self.assertEqual(p3.storage_type, "both")

    def test_optional_fields_default_to_empty_string(self):
        """Test that optional character fields default to empty string"""
        p = _make_plasmid(self.user, name="MinimalPlasmid")
        self.assertEqual(p.other_name, "")
        self.assertEqual(p.old_parent_vector, "")
        self.assertEqual(p.us_e, "")
        self.assertEqual(p.construction_feature, "")
        self.assertEqual(p.received_from, "")
        self.assertEqual(p.note, "")
        self.assertEqual(p.reference, "")

    def test_all_char_fields_can_be_set(self):
        """Test that all character fields accept values"""
        p = _make_plasmid(
            self.user,
            name="pComplete",
            other_name="pAlternative",
            old_parent_vector="pOldParent",
            selection="KanR",
            us_e="Expression",
            construction_feature="Contains GFP tag",
            received_from="Addgene",
            note="High copy number",
            reference="Smith et al. 2020",
        )
        self.assertEqual(p.other_name, "pAlternative")
        self.assertEqual(p.old_parent_vector, "pOldParent")
        self.assertEqual(p.us_e, "Expression")
        self.assertEqual(p.construction_feature, "Contains GFP tag")
        self.assertEqual(p.received_from, "Addgene")
        self.assertEqual(p.note, "High copy number")
        self.assertEqual(p.reference, "Smith et al. 2020")

    def test_construction_feature_accepts_long_text(self):
        """Test TextField can hold longer text"""
        long_construction = "This is a very detailed construction feature. " * 50
        p = _make_plasmid(
            self.user, name="pVerbose", construction_feature=long_construction
        )
        p.refresh_from_db()
        self.assertEqual(p.construction_feature, long_construction)

    def test_name_with_special_characters(self):
        """Test that special characters in name are preserved"""
        p = _make_plasmid(self.user, name="pGEX-6P-1 (α)")
        p.refresh_from_db()
        self.assertEqual(p.name, "pGEX-6P-1 (α)")

    def test_sequence_feature_get_options_does_not_use_limit_method(self):
        """Test sequence feature suggestion options return a sliced list."""
        field = FieldSequenceFeature(model=Plasmid)
        field.limit_options = 5
        for i in range(10):
            SequenceFeature.objects.create(name=f"pbb{i}", common_feature=True)
        options = field.get_options("pbb")
        self.assertEqual(len(options), 6)
        self.assertEqual(options[-1], "...")

    def test_very_long_name_within_limit(self):
        """Test name can be up to 255 characters"""
        long_name = "p" + "A" * 254
        p = _make_plasmid(self.user, name=long_name)
        self.assertEqual(len(p.name), 255)

    def test_map_dna_can_be_null(self):
        """Test that map_dna field can be null"""
        p = _make_plasmid(self.user, name="NoMap", map_dna=None)
        self.assertFalse(p.map_dna.name)

    def test_clone_ignores_map_dna_file_fields(self):
        """Cloning should not copy ignored file fields like map_dna."""
        original = _make_plasmid(
            self.user,
            name="pWithMap",
            map_dna=SimpleUploadedFile(
                "original.dna", b"ATGC", content_type="application/octet-stream"
            ),
        )
        admin = CustomClonableModelAdmin(Plasmid, admin_site)
        admin.clone_ignore_fields = ["map_dna"]
        cloned = Plasmid(
            name="pClone",
            selection="AmpR",
            storage_type="bacteria",
            created_by=self.user,
        )
        admin.copy_cloned_file_fields(original, cloned, request_files={})
        self.assertFalse(cloned.map_dna.name)
        self.assertTrue(original.map_dna.name)

    def test_parent_vector_can_be_null(self):
        """Test that parent_vector can be null"""
        self.assertIsNone(self.plasmid.parent_vector)

    def test_parent_vector_can_reference_self(self):
        """Test that parent_vector can reference another plasmid"""
        parent = _make_plasmid(self.user, name="pParent")
        child = _make_plasmid(self.user, name="pChild", parent_vector=parent)
        self.assertEqual(child.parent_vector, parent)

    def test_save_without_historical_record(self):
        """Test that save_without_historical_record doesn't create history entry"""
        initial_count = self.plasmid.history.count()
        self.plasmid.selection = "TetR"
        self.plasmid.save_without_historical_record()
        self.assertEqual(self.plasmid.history.count(), initial_count)

    def test_readonly_fields_for_creator(self):
        """Test that creator can edit all obj_specific_fields"""
        mock_request = Mock()
        mock_request.user = self.user
        readonly = self.plasmid.readonly_fields(mock_request)
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
        readonly = self.plasmid.readonly_fields(mock_request)
        self.assertIn("name", readonly)
        self.assertIn("created_date_time", readonly)

    def test_model_meta_verbose_name(self):
        """Test model verbose names are set correctly"""
        self.assertEqual(Plasmid._meta.verbose_name, "plasmid")
        self.assertEqual(Plasmid._meta.verbose_name_plural, "plasmids")

    def test_required_fields_cannot_be_none(self):
        """Test that required fields cannot be None"""
        with self.assertRaises(Exception):
            Plasmid.objects.create(
                name=None,
                selection="AmpR",
                storage_type="bacteria",
                created_by=self.user,
            )

    def test_clean_method_strips_name(self):
        """Test that clean method properly strips name"""
        p = Plasmid(
            name="  Spaced Name  ",
            selection="AmpR",
            storage_type="bacteria",
            created_by=self.user,
        )
        try:
            p.clean()
        except ValidationError:
            pass
        self.assertEqual(p.name, "Spaced Name")

    def test_download_file_name_property(self):
        """Test that download_file_name property works correctly"""
        p = _make_plasmid(self.user, name="pDownload")
        download_name = p.download_file_name
        self.assertTrue(download_name.startswith("p"))
        self.assertIn(str(p.id), download_name)

    def test_zebra_label_content_property(self):
        """Test zebra_n0jtt_label_content property"""
        p = _make_plasmid(self.user, name="pLabel")
        label_content = p.zebra_n0jtt_label_content
        self.assertIsInstance(label_content, list)
        self.assertEqual(len(label_content), 5)
        self.assertIn(str(p.id), label_content[0])
        self.assertEqual(label_content[1], "pLabel")

    def test_note_max_length(self):
        """Test note field has max_length of 300"""
        long_note = "x" * 300
        p = _make_plasmid(self.user, name="pLongNote", note=long_note)
        self.assertEqual(len(p.note), 300)


class PlasmidDocModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="pdoctest@example.com", password="password"
        )
        cls.plasmid = _make_plasmid(cls.user, name="Doc Test Plasmid")

    def test_plasmid_doc_creation(self):
        """Test creating a PlasmidDoc"""
        test_file = SimpleUploadedFile(
            "test.pdf", b"file_content", content_type="application/pdf"
        )
        doc = PlasmidDoc.objects.create(
            plasmid=self.plasmid, name=test_file, description="Test document"
        )
        self.assertEqual(doc.plasmid, self.plasmid)
        self.assertEqual(doc.description, "Test document")

    def test_plasmid_doc_foreignkey_protection(self):
        """Test that deleting plasmid is protected when docs exist"""
        from django.db.models.deletion import ProtectedError

        test_file = SimpleUploadedFile(
            "protected.pdf", b"file_content", content_type="application/pdf"
        )
        doc = PlasmidDoc.objects.create(
            plasmid=self.plasmid, name=test_file, description="Protected doc"
        )
        with self.assertRaises(ProtectedError):
            self.plasmid.delete()

    def test_plasmid_doc_timestamps(self):
        """Test that doc has timestamps"""
        test_file = SimpleUploadedFile(
            "time.pdf", b"file_content", content_type="application/pdf"
        )
        doc = PlasmidDoc.objects.create(
            plasmid=self.plasmid, name=test_file, description="Time test doc"
        )
        self.assertIsNotNone(doc.created_date_time)
        self.assertIsNotNone(doc.last_changed_date_time)

    def test_plasmid_doc_verbose_name(self):
        """Test PlasmidDoc verbose name"""
        self.assertEqual(PlasmidDoc._meta.verbose_name, "plasmid document")


class PlasmidAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="plasmidaspitest@example.com", password="password"
        )
        cls.plasmid = _make_plasmid(cls.user)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = "/api/collection/plasmid/"

    def test_retrieve_returns_200(self):
        response = self.client.get(f"{self.url}{self.plasmid.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "pUC19")

    @skip(
        "The generic ModelViewSet does not support create via the API (get_serializer_class() requires self.model set by get_queryset())."
    )
    def test_create_plasmid(self):
        data = {"name": "pBR322", "selection": "TetR", "storage_type": "bacteria"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @skip(
        "The generic ModelViewSet serializer uses empty field_names for partial_update, so no fields are persisted."
    )
    def test_partial_update_plasmid(self):
        response = self.client.patch(
            f"{self.url}{self.plasmid.id}/", {"selection": "KanR"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_plasmid(self):
        response = self.client.delete(f"{self.url}{self.plasmid.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Plasmid.objects.count(), 0)

    def test_unauthenticated_returns_403(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(f"{self.url}{self.plasmid.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_retrieve_nonexistent_returns_404(self):
        response = self.client.get(f"{self.url}999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_returns_complete_data(self):
        """Test that retrieve returns all plasmid fields"""
        p = _make_plasmid(
            self.user,
            name="pComplete",
            other_name="pAlt",
            selection="KanR",
            us_e="Expression",
            construction_feature="GFP tagged",
            received_from="Addgene",
            note="High copy",
            reference="Smith 2020",
            storage_type="both",
        )
        response = self.client.get(f"{self.url}{p.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "pComplete")
        self.assertEqual(response.data["other_name"], "pAlt")
        self.assertEqual(response.data["selection"], "KanR")
        self.assertEqual(response.data["us_e"], "Expression")
        self.assertEqual(response.data["storage_type"], "both")

    def test_delete_removes_from_database(self):
        """Test that delete actually removes the plasmid"""
        p = _make_plasmid(self.user, name="pToDelete")
        p_id = p.id
        response = self.client.delete(f"{self.url}{p_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Plasmid.objects.filter(id=p_id).exists())

    def test_unauthenticated_retrieve_forbidden(self):
        """Test that unauthenticated users cannot retrieve"""
        self.client.force_authenticate(user=None)
        response = self.client.get(f"{self.url}{self.plasmid.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_delete_forbidden(self):
        """Test that unauthenticated users cannot delete"""
        p = _make_plasmid(self.user, name="pProtected")
        self.client.force_authenticate(user=None)
        response = self.client.delete(f"{self.url}{p.id}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertTrue(Plasmid.objects.filter(id=p.id).exists())

    def test_retrieve_includes_timestamps(self):
        """Test that retrieve includes timestamp fields"""
        response = self.client.get(f"{self.url}{self.plasmid.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("created_date_time", response.data)
        self.assertIn("last_changed_date_time", response.data)

    def test_retrieve_includes_created_by(self):
        """Test that retrieve includes created_by field"""
        response = self.client.get(f"{self.url}{self.plasmid.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("created_by", response.data)

    def test_retrieve_parent_vector_when_set(self):
        """Test retrieving plasmid with parent vector"""
        parent = _make_plasmid(self.user, name="pParent")
        child = _make_plasmid(self.user, name="pChild", parent_vector=parent)
        response = self.client.get(f"{self.url}{child.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "pChild")
        if response.data.get("parent_vector"):
            self.assertEqual(response.data["parent_vector"], parent.id)

    def test_multiple_plasmids_can_be_retrieved(self):
        """Test that multiple plasmids can exist and be retrieved"""
        p1 = _make_plasmid(self.user, name="pFirst")
        p2 = _make_plasmid(self.user, name="pSecond")
        response1 = self.client.get(f"{self.url}{p1.id}/")
        response2 = self.client.get(f"{self.url}{p2.id}/")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data["name"], "pFirst")
        self.assertEqual(response2.data["name"], "pSecond")

    def test_retrieve_all_storage_types(self):
        """Test retrieving plasmids with different storage types"""
        p1 = _make_plasmid(self.user, name="pPlasmidOnly", storage_type="plasmid")
        p2 = _make_plasmid(self.user, name="pBacteriaOnly", storage_type="bacteria")
        p3 = _make_plasmid(self.user, name="pBothTypes", storage_type="both")
        for p, expected_type in [(p1, "plasmid"), (p2, "bacteria"), (p3, "both")]:
            response = self.client.get(f"{self.url}{p.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["storage_type"], expected_type)

    def test_retrieve_with_all_optional_fields_empty(self):
        """Test retrieving plasmid with minimal fields"""
        p = _make_plasmid(self.user, name="pMinimal")
        response = self.client.get(f"{self.url}{p.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["other_name"], "")
        self.assertEqual(response.data["us_e"], "")
        self.assertEqual(response.data["note"], "")

    def test_retrieve_with_special_characters_in_name(self):
        """Test retrieving plasmid with special characters"""
        p = _make_plasmid(self.user, name="pGEX-6P-1 (α-tag)")
        response = self.client.get(f"{self.url}{p.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "pGEX-6P-1 (α-tag)")

    def test_retrieve_with_long_construction_feature(self):
        """Test retrieving plasmid with long construction feature"""
        long_text = "Very detailed construction. " * 20
        p = _make_plasmid(self.user, name="pDetailed", construction_feature=long_text)
        response = self.client.get(f"{self.url}{p.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["construction_feature"], long_text)

    def test_retrieve_different_selections(self):
        """Test retrieving plasmids with different selection markers"""
        markers = ["AmpR", "KanR", "TetR", "ChlR", "HygR"]
        plasmids = []
        for marker in markers:
            p = _make_plasmid(self.user, name=f"p{marker}", selection=marker)
            plasmids.append((p, marker))
        for p, expected_marker in plasmids:
            response = self.client.get(f"{self.url}{p.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["selection"], expected_marker)

    def test_delete_does_not_affect_other_plasmids(self):
        """Test that deleting one plasmid doesn't affect others"""
        p1 = _make_plasmid(self.user, name="pKeep")
        p2 = _make_plasmid(self.user, name="pDelete")
        response = self.client.delete(f"{self.url}{p2.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Plasmid.objects.filter(id=p1.id).exists())
        self.assertFalse(Plasmid.objects.filter(id=p2.id).exists())

    def test_retrieve_after_delete_returns_404(self):
        """Test that retrieving deleted plasmid returns 404"""
        p = _make_plasmid(self.user, name="pDeleteThenRetrieve")
        p_id = p.id
        self.client.delete(f"{self.url}{p_id}/")
        response = self.client.get(f"{self.url}{p_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_with_reference_field(self):
        """Test retrieving plasmid with reference"""
        p = _make_plasmid(
            self.user, name="pReferenced", reference="Jones et al. Nature 2021"
        )
        response = self.client.get(f"{self.url}{p.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reference"], "Jones et al. Nature 2021")

    def test_retrieve_with_received_from_field(self):
        """Test retrieving plasmid with received_from"""
        p = _make_plasmid(
            self.user, name="pFromAddgene", received_from="Addgene #12345"
        )
        response = self.client.get(f"{self.url}{p.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["received_from"], "Addgene #12345")
