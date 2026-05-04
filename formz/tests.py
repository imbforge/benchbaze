import io
from datetime import date

from django.contrib.auth import get_user_model
from django.forms import ValidationError
from django.test import TestCase
from openpyxl import Workbook

from .models import (
    GenTechMethod,
    Header,
    NucleicAcidPurity,
    NucleicAcidRisk,
    Project,
    SequenceFeature,
    SequenceFeatureAlias,
    Species,
    ZkbsCellLine,
    ZkbsOncogene,
    ZkbsPlasmid,
)
from .update_zkbs_records import (
    update_zkbs_celllines,
    update_zkbs_oncogenes,
    update_zkbs_plasmids,
)

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_species(name_for_search="Homo sapiens", latin_name="Homo sapiens", **kwargs):
    defaults = dict(
        name_for_search=name_for_search,
        latin_name=latin_name,
        risk_group=1,
    )
    defaults.update(kwargs)
    return Species.objects.create(**defaults)


def _make_sequence_feature(name="GFP", common_feature=True, **kwargs):
    purity = NucleicAcidPurity.objects.create(
        english_name="Total RNA", german_name="Gesamt-RNA"
    )
    risk = NucleicAcidRisk.objects.create(english_name="Low", german_name="Niedrig")
    feat = SequenceFeature.objects.create(
        name=name,
        nuc_acid_purity=purity,
        nuc_acid_risk=risk,
        common_feature=common_feature,
        **kwargs,
    )
    return feat


def _excel_bytes(header_row, data_rows, skip_first_row=True):
    """Build an in-memory Excel file with an optional blank first row."""
    wb = Workbook()
    ws = wb.active
    if skip_first_row:
        ws.append([])  # blank row to be skipped
    ws.append(header_row)
    for row in data_rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# NucleicAcidPurity
# ---------------------------------------------------------------------------


class NucleicAcidPurityModelTest(TestCase):
    def test_creation_and_str(self):
        obj = NucleicAcidPurity.objects.create(
            english_name="Genomic DNA", german_name="Genomische DNA"
        )
        self.assertEqual(str(obj), "Genomic DNA")


# ---------------------------------------------------------------------------
# NucleicAcidRisk
# ---------------------------------------------------------------------------


class NucleicAcidRiskModelTest(TestCase):
    def test_creation_and_str(self):
        obj = NucleicAcidRisk.objects.create(english_name="High", german_name="Hoch")
        self.assertEqual(str(obj), "High")


# ---------------------------------------------------------------------------
# GenTechMethod
# ---------------------------------------------------------------------------


class GenTechMethodModelTest(TestCase):
    def test_creation_and_str(self):
        obj = GenTechMethod.objects.create(
            english_name="CRISPR-Cas9", german_name="CRISPR-Cas9"
        )
        self.assertEqual(str(obj), "CRISPR-Cas9")


# ---------------------------------------------------------------------------
# ZkbsPlasmid
# ---------------------------------------------------------------------------


class ZkbsPlasmidModelTest(TestCase):
    def setUp(self):
        self.plasmid = ZkbsPlasmid.objects.create(
            name="pUC19",
            source="ATCC",
            purpose="Cloning vector",
        )

    def test_creation(self):
        self.assertEqual(self.plasmid.name, "pUC19")

    def test_str_representation(self):
        self.assertEqual(str(self.plasmid), "pUC19")

    def test_description_defaults_to_empty(self):
        self.assertEqual(self.plasmid.description, "")


# ---------------------------------------------------------------------------
# ZkbsOncogene
# ---------------------------------------------------------------------------


class ZkbsOncogeneModelTest(TestCase):
    def setUp(self):
        self.oncogene = ZkbsOncogene.objects.create(
            name="KRAS",
            synonym="Ki-ras",
            species="Homo sapiens",
            risk_potential="Medium",
            reference="",
            additional_measures=False,
        )

    def test_creation(self):
        self.assertEqual(self.oncogene.name, "KRAS")

    def test_str_representation(self):
        self.assertEqual(str(self.oncogene), "KRAS")


# ---------------------------------------------------------------------------
# ZkbsCellLine
# ---------------------------------------------------------------------------


class ZkbsCellLineModelTest(TestCase):
    def setUp(self):
        self.cell_line = ZkbsCellLine.objects.create(
            name="HeLa",
            synonym="",
            organism="Homo sapiens",
            risk_potential="2",
            origin="",
            virus="",
            genetically_modified=False,
        )

    def test_creation(self):
        self.assertEqual(self.cell_line.name, "HeLa")

    def test_str_representation(self):
        self.assertEqual(str(self.cell_line), "HeLa")

    def test_genetically_modified_stored(self):
        self.assertFalse(self.cell_line.genetically_modified)


# ---------------------------------------------------------------------------
# Species
# ---------------------------------------------------------------------------


class SpeciesModelTest(TestCase):
    def setUp(self):
        self.species = _make_species()

    def test_creation(self):
        self.assertEqual(self.species.latin_name, "Homo sapiens")

    def test_str_with_risk_group(self):
        self.assertEqual(str(self.species), "Homo sapiens - RG 1")

    def test_str_without_risk_group(self):
        # save() sets name_for_search = latin_name or common_name
        s = Species.objects.create(
            name_for_search="placeholder", common_name="No risk group", risk_group=None
        )
        self.assertEqual(str(s), "No risk group")

    def test_display_name_returns_latin_name_when_set(self):
        self.assertEqual(self.species.display_name, "Homo sapiens")

    def test_display_name_returns_common_name_when_no_latin(self):
        s = Species.objects.create(
            name_for_search="mouse", common_name="Mouse", risk_group=1
        )
        self.assertEqual(s.display_name, "Mouse")

    def test_name_for_search_set_to_latin_name_on_save(self):
        s = _make_species(
            name_for_search="temp", latin_name="Mus musculus", common_name=""
        )
        self.assertEqual(s.name_for_search, "Mus musculus")

    def test_name_for_search_falls_back_to_common_name(self):
        s = Species.objects.create(
            name_for_search="placeholder",
            latin_name="",
            common_name="Baker's yeast",
            risk_group=1,
        )
        self.assertEqual(s.name_for_search, "Baker's yeast")

    def test_latin_name_stripped_on_save(self):
        s = _make_species(
            name_for_search="trimmed-latin",
            latin_name="  Drosophila melanogaster  ",
        )
        s.refresh_from_db()
        self.assertEqual(s.latin_name, "Drosophila melanogaster")

    def test_common_name_stripped_on_save(self):
        s = Species.objects.create(
            name_for_search="stripped-common",
            latin_name="",
            common_name="  fruit fly  ",
            risk_group=1,
        )
        s.refresh_from_db()
        self.assertEqual(s.common_name, "fruit fly")

    def test_show_in_cell_line_collection_defaults_to_false(self):
        self.assertFalse(self.species.show_in_cell_line_collection)

    def test_name_for_search_is_unique(self):
        from django.db import IntegrityError

        # save() derives name_for_search from latin_name, so pass same latin_name
        # to trigger the unique constraint on name_for_search
        with self.assertRaises(IntegrityError):
            Species.objects.create(latin_name="Homo sapiens", risk_group=1)

    def test_clean_raises_when_neither_name_set(self):
        s = Species(name_for_search="empty", risk_group=1)
        with self.assertRaises(ValidationError):
            s.clean()

    def test_clean_passes_with_latin_name(self):
        s = Species(
            name_for_search="ok", latin_name="Caenorhabditis elegans", risk_group=1
        )
        try:
            s.clean()
        except ValidationError:
            self.fail("clean() raised unexpectedly")

    def test_clean_passes_with_common_name_only(self):
        s = Species(name_for_search="ok2", common_name="Nematode", risk_group=1)
        try:
            s.clean()
        except ValidationError:
            self.fail("clean() raised unexpectedly")


# ---------------------------------------------------------------------------
# SequenceFeature
# ---------------------------------------------------------------------------


class SequenceFeatureModelTest(TestCase):
    def setUp(self):
        self.feat = _make_sequence_feature(name="AmpR", common_feature=True)

    def test_creation(self):
        self.assertEqual(self.feat.name, "AmpR")

    def test_str_common_feature(self):
        # common features: just the name
        self.assertEqual(str(self.feat), "AmpR")

    def test_str_non_common_feature_includes_species(self):
        species = _make_species(
            name_for_search="Aequorea victoria", latin_name="Aequorea victoria"
        )
        feat = _make_sequence_feature(name="GFP-noncommon", common_feature=False)
        feat.donor_organism.add(species)
        self.assertEqual(str(feat), "GFP-noncommon - Aequorea victoria")

    def test_name_stripped_on_save(self):
        feat = _make_sequence_feature(name="  KanR  ", common_feature=True)
        feat.refresh_from_db()
        self.assertEqual(feat.name, "KanR")

    def test_get_donor_species_risk_groups_empty_when_no_donor(self):
        self.assertEqual(self.feat.get_donor_species_risk_groups(), "")

    def test_get_donor_species_max_risk_group_zero_when_no_donor(self):
        self.assertEqual(self.feat.get_donor_species_max_risk_group(), 0)

    def test_get_donor_species_risk_groups_with_donor(self):
        species = _make_species(
            name_for_search="Ecoli-rg1", latin_name="Escherichia coli", risk_group=1
        )
        self.feat.donor_organism.add(species)
        self.assertEqual(self.feat.get_donor_species_risk_groups(), "1")

    def test_get_donor_species_max_risk_group_with_donor(self):
        species = _make_species(
            name_for_search="Ecoli-rg1b",
            latin_name="Escherichia coli K12",
            risk_group=1,
        )
        self.feat.donor_organism.add(species)
        self.assertEqual(self.feat.get_donor_species_max_risk_group(), 1)


# ---------------------------------------------------------------------------
# SequenceFeatureAlias
# ---------------------------------------------------------------------------


class SequenceFeatureAliasModelTest(TestCase):
    def setUp(self):
        self.feat = _make_sequence_feature(name="GFP-alias-test", common_feature=True)
        self.alias = SequenceFeatureAlias.objects.create(
            label="egfp", sequence_feature=self.feat
        )

    def test_creation(self):
        self.assertEqual(self.alias.label, "egfp")

    def test_str_representation(self):
        self.assertEqual(str(self.alias), "egfp")

    def test_label_stripped_on_save(self):
        alias = SequenceFeatureAlias.objects.create(
            label="  gfp2  ", sequence_feature=self.feat
        )
        alias.refresh_from_db()
        self.assertEqual(alias.label, "gfp2")

    def test_label_is_unique(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            SequenceFeatureAlias.objects.create(
                label="egfp", sequence_feature=self.feat
            )


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="projtest@example.com", password="password"
        )
        self.project = Project.objects.create(
            title="Investigation of something",
            short_title="Inv Study",
            short_title_english="Inv Study",
            safety_level=1,
            beginning_work_date=date(2024, 1, 1),
        )
        self.project.project_leader.add(self.user)

    def test_creation(self):
        self.assertEqual(self.project.short_title_english, "Inv Study")

    def test_str_representation(self):
        self.assertEqual(str(self.project), "Inv Study")

    def test_short_title_stripped_on_save(self):
        p = Project.objects.create(
            title="Title",
            short_title="  Trimmed  ",
            short_title_english="  TrimmedEn  ",
            safety_level=1,
            beginning_work_date=date(2024, 1, 1),
        )
        p.refresh_from_db()
        self.assertEqual(p.short_title, "Trimmed")
        self.assertEqual(p.short_title_english, "TrimmedEn")

    def test_parent_project_nullable(self):
        self.assertIsNone(self.project.parent_project)

    def test_end_work_date_nullable(self):
        self.assertIsNone(self.project.end_work_date)

    def test_clean_raises_on_double_quotes_in_short_title(self):
        self.project.short_title = 'Bad "title"'
        with self.assertRaises(ValidationError) as ctx:
            self.project.clean()
        self.assertIn("short_title", ctx.exception.message_dict)

    def test_clean_raises_on_double_quotes_in_short_title_english(self):
        self.project.short_title_english = 'Bad "title"'
        with self.assertRaises(ValidationError) as ctx:
            self.project.clean()
        self.assertIn("short_title", ctx.exception.message_dict)

    def test_clean_passes_with_no_air_quotes(self):
        self.project.short_title = "Normal title"
        self.project.short_title_english = "Normal title"
        try:
            self.project.clean()
        except ValidationError:
            self.fail("clean() raised unexpectedly")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


class HeaderModelTest(TestCase):
    def setUp(self):
        self.header = Header.objects.create(
            operator="Lab Institute",
            address="123 Science St",
            name_biosafety_officer="Dr. Safety",
            s1_approval_file_num="S1-001",
            s1_approval_date=date(2020, 1, 1),
            s2_approval_file_num="S2-001",
            s2_approval_date=date(2020, 6, 1),
        )

    def test_creation(self):
        self.assertEqual(self.header.operator, "Lab Institute")

    def test_str_representation(self):
        self.assertEqual(str(self.header), "Lab Institute")


# ---------------------------------------------------------------------------
# update_zkbs_celllines
# ---------------------------------------------------------------------------

_CELLLINE_HEADER = [
    "Name",
    "Synonym",
    "Risikogruppe",
    "Spezies/Organismus",
    "Gewebe",
    "Virus",
    "gentechnisch verändert",
]


class UpdateZkbsCellLinesTest(TestCase):
    def _make_excel(self, data_rows):
        return _excel_bytes(_CELLLINE_HEADER, data_rows)

    def test_creates_new_cell_line(self):
        excel = self._make_excel(
            [["Vero", "Vero cells", "1", "Cercopithecus aethiops", "kidney", "", None]]
        )
        update_zkbs_celllines(excel)
        self.assertEqual(ZkbsCellLine.objects.filter(name="Vero").count(), 1)

    def test_genetically_modified_ja_maps_to_true(self):
        excel = self._make_excel(
            [["CHO-K1", "", "1", "Cricetulus griseus", "", "", "Ja"]]
        )
        update_zkbs_celllines(excel)
        obj = ZkbsCellLine.objects.get(name="CHO-K1")
        self.assertTrue(obj.genetically_modified)

    def test_genetically_modified_non_ja_maps_to_false(self):
        excel = self._make_excel(
            [["CHO-wt", "", "1", "Cricetulus griseus", "", "", None]]
        )
        update_zkbs_celllines(excel)
        obj = ZkbsCellLine.objects.get(name="CHO-wt")
        self.assertFalse(obj.genetically_modified)

    def test_updates_existing_cell_line(self):
        ZkbsCellLine.objects.create(
            name="HEK293",
            synonym="",
            organism="old",
            risk_potential="1",
            origin="",
            virus="",
            genetically_modified=False,
        )
        excel = self._make_excel(
            [["HEK293", "HEK-293", "2", "Homo sapiens", "kidney", "", None]]
        )
        update_zkbs_celllines(excel)
        obj = ZkbsCellLine.objects.get(name="HEK293")
        self.assertEqual(obj.organism, "Homo sapiens")
        self.assertEqual(obj.synonym, "HEK-293")

    def test_returns_error_on_bad_headers(self):
        excel = _excel_bytes(["Wrong", "Headers"], [])
        errors = update_zkbs_celllines(excel)
        self.assertGreater(len(errors), 0)

    def test_returns_error_on_non_excel_file(self):
        fake = io.BytesIO(b"not an excel file")
        errors = update_zkbs_celllines(fake)
        self.assertGreater(len(errors), 0)


# ---------------------------------------------------------------------------
# update_zkbs_plasmids
# ---------------------------------------------------------------------------

_PLASMID_HEADER = ["Name", "Funktion", "Herkunft", "AZ ZKBS", "Kurzbeschreibung"]


class UpdateZkbsPlasmidsTest(TestCase):
    def _make_excel(self, data_rows):
        return _excel_bytes(_PLASMID_HEADER, data_rows)

    def test_creates_new_plasmid(self):
        excel = self._make_excel(
            [["pBR322", "Cloning", "ATCC", "AZ-1", "Classic vector"]]
        )
        update_zkbs_plasmids(excel)
        self.assertEqual(ZkbsPlasmid.objects.filter(name="pBR322").count(), 1)

    def test_correct_fields_mapped(self):
        excel = self._make_excel(
            [["pACYC184", "Dual selection", "NEB", "AZ-2", "Description text"]]
        )
        update_zkbs_plasmids(excel)
        obj = ZkbsPlasmid.objects.get(name="pACYC184")
        self.assertEqual(obj.purpose, "Dual selection")
        self.assertEqual(obj.source, "NEB")
        self.assertEqual(obj.description, "Description text")

    def test_updates_existing_plasmid(self):
        ZkbsPlasmid.objects.create(
            name="pUC19", source="old source", purpose="old purpose"
        )
        excel = self._make_excel(
            [["pUC19", "New purpose", "New source", "AZ-3", "New desc"]]
        )
        update_zkbs_plasmids(excel)
        obj = ZkbsPlasmid.objects.get(name="pUC19")
        self.assertEqual(obj.source, "New source")
        self.assertEqual(obj.purpose, "New purpose")

    def test_returns_error_on_bad_headers(self):
        excel = _excel_bytes(["Bad", "Headers"], [])
        errors = update_zkbs_plasmids(excel)
        self.assertGreater(len(errors), 0)

    def test_returns_error_on_non_excel_file(self):
        fake = io.BytesIO(b"not an excel file")
        errors = update_zkbs_plasmids(fake)
        self.assertGreater(len(errors), 0)


# ---------------------------------------------------------------------------
# update_zkbs_oncogenes
# ---------------------------------------------------------------------------

_ONCOGENE_HEADER = [
    "Eintragdatum",
    "Gen/Nukleinsäure",
    "Synonym",
    "Spezies",
    "Bewertung",
    "Literatur",
    "zusätzliche Maßnahmen",
]


class UpdateZkbsOncogenesTest(TestCase):
    def _make_excel(self, data_rows):
        return _excel_bytes(_ONCOGENE_HEADER, data_rows)

    def test_creates_new_oncogene(self):
        excel = self._make_excel(
            [["2024-01-01", "MYC", "c-MYC", "Homo sapiens", "High", "Smith 2000", None]]
        )
        update_zkbs_oncogenes(excel)
        self.assertEqual(ZkbsOncogene.objects.filter(name="MYC").count(), 1)

    def test_additional_measures_ja_maps_to_true(self):
        excel = self._make_excel(
            [["2024-01-01", "RAS", "", "Homo sapiens", "High", "", "Ja"]]
        )
        update_zkbs_oncogenes(excel)
        obj = ZkbsOncogene.objects.get(name="RAS")
        self.assertTrue(obj.additional_measures)

    def test_additional_measures_non_ja_maps_to_false(self):
        excel = self._make_excel(
            [["2024-01-01", "BCL2", "", "Homo sapiens", "Low", "", None]]
        )
        update_zkbs_oncogenes(excel)
        obj = ZkbsOncogene.objects.get(name="BCL2")
        self.assertFalse(obj.additional_measures)

    def test_asterisks_stripped_from_name(self):
        excel = self._make_excel(
            [["2024-01-01", "TP53*", "", "Homo sapiens", "High", "", None]]
        )
        update_zkbs_oncogenes(excel)
        self.assertEqual(ZkbsOncogene.objects.filter(name="TP53").count(), 1)
        self.assertEqual(ZkbsOncogene.objects.filter(name="TP53*").count(), 0)

    def test_updates_existing_oncogene(self):
        ZkbsOncogene.objects.create(
            name="BRCA1",
            synonym="",
            species="old",
            risk_potential="Low",
            reference="",
            additional_measures=False,
        )
        excel = self._make_excel(
            [
                [
                    "2024-01-01",
                    "BRCA1",
                    "BRCA-1",
                    "Homo sapiens",
                    "High",
                    "Jones 2001",
                    None,
                ]
            ]
        )
        update_zkbs_oncogenes(excel)
        obj = ZkbsOncogene.objects.get(name="BRCA1")
        self.assertEqual(obj.species, "Homo sapiens")
        self.assertEqual(obj.synonym, "BRCA-1")

    def test_returns_error_on_bad_headers(self):
        excel = _excel_bytes(["Bad", "Headers"], [])
        errors = update_zkbs_oncogenes(excel)
        self.assertGreater(len(errors), 0)

    def test_returns_error_on_non_excel_file(self):
        fake = io.BytesIO(b"not an excel file")
        errors = update_zkbs_oncogenes(fake)
        self.assertGreater(len(errors), 0)
