from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone
from collection.antibody.models import Antibody
from collection.oligo.models import Oligo
from collection.plasmid.models import Plasmid
from .models import Approval

User = get_user_model()


def _make_plasmid(user, name="Test Plasmid"):
    """Helper to create a plasmid for testing approvals."""
    from collection.ecolistrain.models import EColiStrain

    ecoli = EColiStrain.objects.create(name=f"E. coli for {name}", created_by=user)
    plasmid = Plasmid.objects.create(
        name=name, selection="Amp", storage_type="bacteria", created_by=user
    )
    plasmid.formz_ecoli_strains.add(ecoli)
    return plasmid


def _make_antibody(user, name="Test Antibody"):
    """Helper to create an antibody for testing approvals."""
    return Antibody.objects.create(
        name=name, species_isotype="Mouse IgG", created_by=user
    )


def _make_oligo(user, name="Test Oligo", sequence="ATCGATCG"):
    """Helper to create an oligo for testing approvals."""
    return Oligo.objects.create(name=name, sequence=sequence, created_by=user)


def _make_approval(activity_user, content_object, activity_type="created", **kwargs):
    """Helper to create an approval."""
    defaults = {
        "content_object": content_object,
        "activity_type": activity_type,
        "activity_user": activity_user,
        "message": "Approval message",
    }
    defaults.update(kwargs)
    return Approval.objects.create(**defaults)


class ApprovalModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="approval@example.com", password="password"
        )
        cls.plasmid = _make_plasmid(cls.user)
        cls.approval = _make_approval(cls.user, cls.plasmid)

    def test_approval_creation(self):
        """Test basic approval creation"""
        self.assertIsNotNone(self.approval.id)
        self.assertEqual(self.approval.activity_user, self.user)
        self.assertEqual(self.approval.activity_type, "created")

    def test_approval_with_plasmid(self):
        """Test approval creation with plasmid content object"""
        approval = _make_approval(self.user, self.plasmid, activity_type="created")
        self.assertEqual(approval.content_object, self.plasmid)
        self.assertEqual(approval.object_id, self.plasmid.id)

    def test_approval_with_antibody(self):
        """Test approval creation with antibody content object"""
        antibody = _make_antibody(self.user)
        approval = _make_approval(self.user, antibody, activity_type="changed")
        self.assertEqual(approval.content_object, antibody)
        self.assertEqual(approval.object_id, antibody.id)

    def test_approval_with_oligo(self):
        """Test approval creation with oligo content object"""
        oligo = _make_oligo(self.user)
        approval = _make_approval(self.user, oligo)
        self.assertEqual(approval.content_object, oligo)
        self.assertEqual(approval.object_id, oligo.id)

    def test_activity_type_created(self):
        """Test activity_type can be 'created'"""
        approval = _make_approval(self.user, self.plasmid, activity_type="created")
        self.assertEqual(approval.activity_type, "created")

    def test_activity_type_changed(self):
        """Test activity_type can be 'changed'"""
        approval = _make_approval(self.user, self.plasmid, activity_type="changed")
        self.assertEqual(approval.activity_type, "changed")

    def test_message_field_accepts_text(self):
        """Test message field accepts text"""
        approval = _make_approval(
            self.user, self.plasmid, message="This is an approval message"
        )
        self.assertEqual(approval.message, "This is an approval message")

    def test_message_field_can_be_blank(self):
        """Test message field can be blank"""
        approval = _make_approval(self.user, self.plasmid, message="")
        self.assertEqual(approval.message, "")

    def test_message_max_length(self):
        """Test message field has max length of 255"""
        max_message = "A" * 255
        approval = _make_approval(self.user, self.plasmid, message=max_message)
        self.assertEqual(len(approval.message), 255)

    def test_message_can_be_long(self):
        """Test message can contain up to 255 characters"""
        long_message = "A" * 255
        approval = Approval.objects.create(
            content_object=self.plasmid,
            activity_type="created",
            activity_user=self.user,
            message=long_message,
        )
        self.assertEqual(len(approval.message), 255)

    def test_edited_flag_defaults_to_false(self):
        """Test edited flag defaults to False"""
        approval = _make_approval(self.user, self.plasmid)
        self.assertFalse(approval.edited)

    def test_edited_flag_can_be_true(self):
        """Test edited flag can be set to True"""
        approval = _make_approval(self.user, self.plasmid, edited=True)
        self.assertTrue(approval.edited)

    def test_created_date_time_auto_set(self):
        """Test created_date_time is automatically set"""
        approval = _make_approval(self.user, self.plasmid)
        self.assertIsNotNone(approval.created_date_time)

    def test_message_date_time_can_be_null(self):
        """Test message_date_time can be null"""
        approval = _make_approval(self.user, self.plasmid, message_date_time=None)
        self.assertIsNone(approval.message_date_time)

    def test_message_date_time_can_be_set(self):
        """Test message_date_time can be set"""
        now = timezone.now()
        approval = _make_approval(self.user, self.plasmid, message_date_time=now)
        self.assertEqual(approval.message_date_time, now)

    def test_activity_user_required(self):
        """Test activity_user is required"""
        with self.assertRaises(Exception):
            Approval.objects.create(
                content_object=self.plasmid,
                activity_type="created",
                activity_user=None,
                message="Test",
            )

    def test_activity_user_foreignkey(self):
        """Test activity_user is a valid ForeignKey to User"""
        approval = _make_approval(self.user, self.plasmid)
        self.assertIsInstance(approval.activity_user, User)
        self.assertEqual(approval.activity_user.email, "approval@example.com")

    def test_content_type_set_automatically(self):
        """Test content_type is set automatically from content_object"""
        approval = _make_approval(self.user, self.plasmid)
        plasmid_ct = ContentType.objects.get_for_model(Plasmid)
        self.assertEqual(approval.content_type, plasmid_ct)

    def test_object_id_set_automatically(self):
        """Test object_id is set automatically from content_object"""
        approval = _make_approval(self.user, self.plasmid)
        self.assertEqual(approval.object_id, self.plasmid.id)

    def test_generic_foreign_key_access(self):
        """Test accessing content_object through GenericForeignKey"""
        approval = _make_approval(self.user, self.plasmid)
        self.assertEqual(approval.content_object.id, self.plasmid.id)
        self.assertEqual(approval.content_object.name, "Test Plasmid")

    def test_multiple_approvals_for_same_object(self):
        """Test multiple approvals can exist for same object"""
        approval1 = _make_approval(
            self.user, self.plasmid, activity_type="created", message="First approval"
        )
        approval2 = _make_approval(
            self.user, self.plasmid, activity_type="changed", message="Second approval"
        )
        self.assertNotEqual(approval1.id, approval2.id)
        self.assertEqual(approval1.content_object, approval2.content_object)

    def test_approvals_for_different_object_types(self):
        """Test approvals can be created for different model types"""
        antibody = _make_antibody(self.user)
        oligo = _make_oligo(self.user)
        approval_plasmid = _make_approval(self.user, self.plasmid)
        approval_antibody = _make_approval(self.user, antibody)
        approval_oligo = _make_approval(self.user, oligo)
        self.assertEqual(approval_plasmid.content_object, self.plasmid)
        self.assertEqual(approval_antibody.content_object, antibody)
        self.assertEqual(approval_oligo.content_object, oligo)

    def test_model_meta_verbose_name(self):
        """Test model verbose names are set correctly"""
        self.assertEqual(Approval._meta.verbose_name, "approval")
        self.assertEqual(Approval._meta.verbose_name_plural, "approvals")

    def test_approval_with_different_users(self):
        """Test approvals can have different activity_users"""
        user2 = User.objects.create_user(
            email="approver2@example.com", password="password"
        )
        approval1 = _make_approval(self.user, self.plasmid)
        approval2 = _make_approval(user2, self.plasmid)
        self.assertEqual(approval1.activity_user, self.user)
        self.assertEqual(approval2.activity_user, user2)

    def test_approval_timestamps_different(self):
        """Test that created_date_time is unique for each approval"""
        import time

        approval1 = _make_approval(self.user, self.plasmid)
        time.sleep(0.01)
        approval2 = _make_approval(self.user, self.plasmid)
        self.assertIsNotNone(approval1.created_date_time)
        self.assertIsNotNone(approval2.created_date_time)


class ApprovalEdgeCasesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="edgecase@example.com", password="password"
        )
        cls.plasmid = _make_plasmid(cls.user)

    def test_approval_with_deleted_object(self):
        """Test approval behavior when content_object is deleted"""
        oligo = _make_oligo(self.user, name="To Delete", sequence="AAAATTTT")
        approval = _make_approval(self.user, oligo)
        approval_id = approval.id
        oligo.delete()
        self.assertFalse(Approval.objects.filter(id=approval_id).exists())

    def test_activity_type_invalid_choice(self):
        """Test invalid activity_type raises error on full_clean"""
        approval = Approval(
            content_object=self.plasmid,
            activity_type="invalid_type",
            activity_user=self.user,
        )
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            approval.full_clean()

    def test_message_with_special_characters(self):
        """Test message accepts special characters"""
        special_message = "Approved! @#$%^&*() <html> 你好"
        approval = _make_approval(self.user, self.plasmid, message=special_message)
        self.assertEqual(approval.message, special_message)

    def test_message_with_newlines(self):
        """Test message accepts newlines"""
        message_with_newlines = "Line 1\nLine 2\nLine 3"
        approval = _make_approval(
            self.user, self.plasmid, message=message_with_newlines
        )
        self.assertEqual(approval.message, message_with_newlines)

    def test_approval_query_by_content_type(self):
        """Test querying approvals by content_type"""
        antibody = _make_antibody(self.user)
        approval_plasmid = _make_approval(self.user, self.plasmid)
        approval_antibody = _make_approval(self.user, antibody)
        plasmid_ct = ContentType.objects.get_for_model(Plasmid)
        plasmid_approvals = Approval.objects.filter(content_type=plasmid_ct)
        self.assertIn(approval_plasmid, plasmid_approvals)
        self.assertNotIn(approval_antibody, plasmid_approvals)

    def test_approval_query_by_object_id(self):
        """Test querying approvals by object_id"""
        plasmid2 = _make_plasmid(self.user, name="Second Plasmid")
        approval1 = _make_approval(self.user, self.plasmid)
        approval2 = _make_approval(self.user, plasmid2)
        approvals_for_plasmid1 = Approval.objects.filter(object_id=self.plasmid.id)
        self.assertIn(approval1, approvals_for_plasmid1)
        self.assertNotIn(approval2, approvals_for_plasmid1)

    def test_approval_count_for_object(self):
        """Test counting approvals for specific object"""
        _make_approval(self.user, self.plasmid, activity_type="created")
        _make_approval(self.user, self.plasmid, activity_type="changed")
        _make_approval(self.user, self.plasmid, activity_type="changed")
        plasmid_ct = ContentType.objects.get_for_model(Plasmid)
        count = Approval.objects.filter(
            content_type=plasmid_ct, object_id=self.plasmid.id
        ).count()
        self.assertEqual(count, 3)

    def test_edited_flag_modification(self):
        """Test modifying edited flag after creation"""
        approval = _make_approval(self.user, self.plasmid, edited=False)
        self.assertFalse(approval.edited)
        approval.edited = True
        approval.save()
        approval.refresh_from_db()
        self.assertTrue(approval.edited)

    def test_message_modification(self):
        """Test modifying message after creation"""
        approval = _make_approval(self.user, self.plasmid, message="Original message")
        self.assertEqual(approval.message, "Original message")
        approval.message = "Updated message"
        approval.edited = True
        approval.save()
        approval.refresh_from_db()
        self.assertEqual(approval.message, "Updated message")
        self.assertTrue(approval.edited)

    def test_content_type_foreignkey_protection(self):
        """Test content_type uses PROTECT on delete"""
        approval = _make_approval(self.user, self.plasmid)
        content_type = approval.content_type
        self.assertEqual(
            Approval._meta.get_field("content_type").remote_field.on_delete.__name__,
            "PROTECT",
        )

    def test_activity_user_foreignkey_protection(self):
        """Test activity_user uses PROTECT on delete"""
        approval = _make_approval(self.user, self.plasmid)
        from django.db.models.deletion import ProtectedError

        with self.assertRaises(ProtectedError):
            self.user.delete()
