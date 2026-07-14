from io import BytesIO, StringIO

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import FeatureLocation, SeqFeature
from Bio.SeqRecord import SeqRecord
from django.utils import timezone
from sgffp import SgffReader, SgffWriter

from formz.models import SequenceFeature

from ..plannotate.plannotate.annotate import annotate as plannotate_annotate
from .common import get_feature_label, get_map_dna_feature_names


def sgff_to_seqrecord(sgff_record):
    """Convert an SGFF record to a Biopython SeqRecord, preserving feature and primer information"""

    features = {}
    for i, feature in enumerate(sgff_record.features):
        feature.raw_qualifiers = None
        features[i] = feature.to_dict()
        # Make a copy of qualifiers because feature.to_dict() stores a dict
        # whose "qualifiers" value is the same object as feature.qualifiers
        features[i]["qualifiers"] = dict(feature.qualifiers)
        feature.qualifiers["bb_sgff_feat_id"] = i

    # Persist feature changes back into the underlying SGFF blocks
    sgff_record.features._sync()

    # Extract primer hybridization parameters and primers, and then wipe them from
    # the sgff_record
    primer_hybridization_params = (
        sgff_record.blocks[5][0]
        .get("Primers", {})
        .get("HybridizationParams", {})
        .copy()
        if 5 in sgff_record.blocks
        else {}
    )
    primers = [primer.to_dict() for primer in sgff_record.primers]
    sgff_record.primers.clear()

    # Convert the SGFF record to a SeqRecord
    seq_record = SeqIO.read(BytesIO(SgffWriter.to_bytes(sgff_record)), "snapgene")

    # Annotate features in the SeqRecord with their original SGFF feature information
    for feature in seq_record.features:
        sgff_id = feature.qualifiers.get("bb_sgff_feat_id")
        if isinstance(sgff_id, list):
            sgff_id = sgff_id[0] if sgff_id else None
        if sgff_id is not None:
            try:
                sgff_id = int(sgff_id)
            except (TypeError, ValueError):
                pass
        if sgff_id is not None:
            setattr(feature, "sgff_feature", features.get(sgff_id))
            del feature.qualifiers["bb_sgff_feat_id"]
            # For now, let's delete parts as well, it comes from BioPython
            # and we already have this information in sgff_feature
            if "parts" in feature.qualifiers:
                del feature.qualifiers["parts"]

    setattr(seq_record, "sgff_primer_hybridization_params", primer_hybridization_params)
    setattr(seq_record, "sgff_primers", primers)
    setattr(seq_record, "converted_from_sgff", True)

    return seq_record


def get_seq_record(inDf, inSeq, is_linear=False, record=None):
    """Modified version of plannotate.resources.get_seq_record
    Takes in a dataframe produced by plannotate and a sequence, and constructs
    a SeqRecord with features based on the dataframe
    We include additional qualifiers in the features to preserve information about
    the original features in the map_dna file.
    These qualifiers are prefixed with "plannot_" to distinguish them from any existing
    qualifiers in the original SeqRecord
    """

    inDf = inDf.reset_index(drop=True)

    def FeatureLocation_smart(r):
        # creates compound locations if needed
        if r.qend > r.qstart:
            return FeatureLocation(r.qstart, r.qend, r.sframe)
        elif r.qstart > r.qend:
            first = FeatureLocation(r.qstart, r.qlen, r.sframe)
            second = FeatureLocation(0, r.qend, r.sframe)
            if r.sframe == 1 or r.sframe == 0:
                return first + second
            elif r.sframe == -1:
                return second + first

    # adds a FeatureLocation object so it can be used in gbk construction
    inDf["feat loc"] = inDf.apply(FeatureLocation_smart, axis=1)

    # make a record if one is not provided
    if record is None:
        record = SeqRecord(seq=Seq(inSeq), name="plasmid")

    record.annotations["data_file_division"] = "SYN"

    if "date" not in record.annotations:
        record.annotations["date"] = timezone.now().date().strftime("%d-%b-%Y").upper()

    if "accession" not in record.annotations:
        record.annotations["accession"] = "."

    if "version" not in record.annotations:
        record.annotations["version"] = "."

    if is_linear:
        record.annotations["topology"] = "linear"
    else:
        record.annotations["topology"] = "circular"

    # this adds "(fragment)" to the end of a feature name
    # if it is a fragment. Maybe a better way show this data in the gbk
    # for downstream analysis, though this may suffice. change type to
    # non-canonical `fragment`?
    def append_frag(row):
        if row["fragment"] is True:
            return f"{row['Feature']} (fragment)"
        else:
            return f"{row['Feature']}"

    inDf["Feature"] = inDf.apply(lambda x: append_frag(x), axis=1)

    inDf["Type"] = inDf["Type"].str.replace("origin of replication", "rep_origin")

    for index in inDf.index:
        record.features.append(
            SeqFeature(
                inDf.loc[index]["feat loc"],
                type=inDf.loc[index]["Type"],  # maybe change 'Type'
                qualifiers={
                    "label": inDf.loc[index]["Feature"],
                    "plannot_database": inDf.loc[index]["db"],
                    "plannot_description": inDf.loc[index]["Description"],
                    "plannot_sseqid": inDf.loc[index]["sseqid"],
                },
            )
        )  # maybe change 'Type'

    return record


def remove_feature_qualifiers(feature, prefix):
    """Remove qualifiers with the given prefix from a feature"""

    keys_to_remove = [k for k in feature.qualifiers if k.startswith(prefix)]
    for key in keys_to_remove:
        del feature.qualifiers[key]


def compare_seqrecord_features(seq_record_a, seq_record_b, fuzz=3):
    """
    Compare features between two SeqRecord objects by position, strand and type.

    Matching rule:
    - Two features are considered the same when their type and strand
    are equal, and the merged start and end of the full feature span match
      within `fuzz` bases.
    - For compound (multi-part) features, the individual part coordinates are
      ignored; only the overall min-start and max-end span is compared.

    Parameters:
    - fuzz: maximum allowed difference (in bases) between corresponding
            merged start or end positions (default: 3).

    Returns:
    - dict with:
    - matched_pairs: list of (feature_from_a, feature_from_b)
    - unique_in_a: list[SeqFeature]
    - unique_in_b: list[SeqFeature]
    """

    def _get_span(feature):
        """Return the merged span (start, end, strand) for a feature."""
        loc = feature.location
        if hasattr(loc, "parts"):
            parts = loc.parts
            start = min(int(p.start) for p in parts)
            end = max(int(p.end) for p in parts)
            strand = loc.strand
            if strand is None:
                for part in parts:
                    if part.strand is not None:
                        strand = part.strand
                        break
        else:
            start = int(loc.start)
            end = int(loc.end)
            strand = loc.strand
        return (start, end, strand)

    def _get_parts(feature):
        """Return a sorted tuple of (start, end, strand) for each part of a location."""
        loc = feature.location
        if hasattr(loc, "parts"):
            return tuple(
                sorted((int(p.start), int(p.end), p.strand) for p in loc.parts)
            )
        return ((int(loc.start), int(loc.end), loc.strand),)

    def _part_matches(a_part, b_part):
        """Check if two parts match within the fuzz criteria."""
        a_start, a_end, a_strand = a_part
        b_start, b_end, b_strand = b_part
        if a_strand != b_strand:
            return False
        return abs(a_start - b_start) <= fuzz and abs(a_end - b_end) <= fuzz

    def _span_matches(a_span, b_span):
        """Check if two merged spans match within the fuzz criteria."""
        a_start, a_end, a_strand = a_span
        b_start, b_end, b_strand = b_span
        if a_strand != b_strand:
            return False
        return abs(a_start - b_start) <= fuzz and abs(a_end - b_end) <= fuzz

    def _overlaps(a, b):
        """Check if features a and b fully overlap by the defined criteria."""

        # The type must be the same for matching features
        if a.type != b.type:
            return False

        return _span_matches(_get_span(a), _get_span(b))

    features_a = list(seq_record_a.features)
    features_b = list(seq_record_b.features)

    matched_pairs = []
    used_b = set()

    # For each feature in A, find a matching feature in B
    for feature_a in features_a:
        match_index = None
        for idx_b, feature_b in enumerate(features_b):
            if idx_b in used_b:
                continue
            if _overlaps(feature_a, feature_b):
                match_index = idx_b
                break

        # If a match is found, record the pair and mark the B feature as used
        if match_index is not None:
            matched_pairs.append((feature_a, features_b[match_index]))
            used_b.add(match_index)

    # After processing all features in A, determine which features are unique to each SeqRecord
    matched_a_ids = {id(pair[0]) for pair in matched_pairs}

    unique_in_a = [f for f in features_a if id(f) not in matched_a_ids]
    unique_in_b = [f for i, f in enumerate(features_b) if i not in used_b]

    return {
        "matched_pairs": matched_pairs,
        "unique_in_a": unique_in_a,
        "unique_in_b": unique_in_b,
    }


def merge_qualifiers(target, source):
    """Return a merged qualifiers dict without mutating the inputs.

    When both objects define the same key, values from source are kept before
    values already present in target. If the values are identical, the existing
    target value is preserved as-is.
    """

    merged = dict(target)

    def _to_list(value):
        return value if isinstance(value, list) else [value]

    for key, value in source.items():
        # If the key is not in target, add it with the source value
        if key not in merged:
            merged[key] = value
            continue

        # If the value is the same in both source and target, keep the existing
        existing = merged[key]
        if existing == value:
            continue

        # If the value is different, merge them into a list of unique values,
        # with source values first
        existing_list = _to_list(existing)
        source_list = _to_list(value)
        if existing_list == source_list:
            continue

        combined = []
        for item in source_list:
            if item not in combined:
                combined.append(item)
        for item in existing_list:
            if item not in combined:
                combined.append(item)
        merged[key] = combined

    return merged


def sanitize_feature_label(label, strip_fragment_suffix=False):
    """Sanitize feature label by stripping whitespace and replacing newlines with spaces."""
    if not isinstance(label, str):
        return label

    # Optionally strip common fragment suffixes that may be added by Plannotate
    # to improve matching with known features in the database
    if strip_fragment_suffix:
        label = label.replace(" (fragment)", "")
    label = label.strip().replace("\n", " ")
    return label


def detect_map_dna_features(
    file_content,
    file_format=None,
    is_detailed=False,
    compare=True,
):
    """Detect features in a DNA map content and return a SeqRecord"""

    def _set_feature_type(feature, new_type):
        feature.qualifiers["bb_feat_type"] = new_type

    # Determine if file_content is a SeqRecord or bytes and parse accordingly
    if isinstance(file_content, SeqIO.SeqRecord):
        seq_record = file_content
    # For bytes, this could be a SnapGene or GenBank file
    elif isinstance(file_content, bytes):
        try:
            if file_format == ".dna":
                seq_record = sgff_to_seqrecord(SgffReader.from_bytes(file_content))
            elif file_format in (".gbk", ".gb"):
                seq_record = SeqIO.read(StringIO(file_content.decode()), "genbank")
        except Exception as e:
            raise ValueError(f"Error parsing file: {str(e)}")
    else:
        raise ValueError("Unsupported file content type. Expected bytes or SeqRecord.")

    topology = seq_record.annotations.get("topology", "")
    if not topology:
        raise ValueError(
            "Topology information is missing from the sequence record annotations."
        )
    topology = topology == "linear"

    # Clean up any existing bb_ qualifiers from the original features to avoid confusion with the new ones
    for feature in seq_record.features:
        remove_feature_qualifiers(feature, prefix="bb_feat_")
        remove_feature_qualifiers(feature, prefix="plannot_")

    # Annotate the sequence record with features
    annotations = plannotate_annotate(
        seq_record.seq, linear=topology, is_detailed=is_detailed
    )
    seq_record_annotated = get_seq_record(annotations, seq_record.seq)
    seq_record_annotated.annotations["molecule_type"] = "DNA"

    # Compare features and color-code them based on whether they match or are unique
    if compare:
        comparison = compare_seqrecord_features(seq_record, seq_record_annotated)

        features_compared = []

        # Matched features
        for feat_a, feat_b in comparison["matched_pairs"]:
            _set_feature_type(feat_a, "matched")
            feat_a.qualifiers = merge_qualifiers(feat_b.qualifiers, feat_a.qualifiers)
            features_compared.append(feat_a)

        # Unique features in original
        for feat in comparison["unique_in_a"]:
            _set_feature_type(feat, "original_only")
            features_compared.append(feat)

        # Unique features in annotated
        for feat in comparison["unique_in_b"]:
            _set_feature_type(feat, "processed_only")
            features_compared.append(feat)

        seq_record.features = features_compared

    # Get the feature names from the processed record, sanitizing them to improve matching
    # with known features in the database
    feature_names = [
        sanitize_feature_label(n, strip_fragment_suffix=True)
        for n in get_map_dna_feature_names(seq_record)
    ]

    # Query the database for SequenceFeature objects that have aliases matching any of the
    # feature names from the processed record
    sequence_features = SequenceFeature.objects.filter(
        alias__label__in=feature_names
    ).distinct()

    # Create a mapping of feature labels to SequenceFeature objects for quick lookup
    feature_map = {
        label: sf
        for sf in sequence_features
        for label in sf.alias.values_list("label", flat=True)
    }

    # Annotate features with database information, where available
    for feat in seq_record.features:
        feat_name = sanitize_feature_label(
            get_feature_label(feat), strip_fragment_suffix=True
        )
        matching_seq_feat = feature_map.get(feat_name)
        if matching_seq_feat:
            feat.qualifiers.update(
                {
                    "bb_feat_id": matching_seq_feat.id,
                    "bb_feat_name": str(matching_seq_feat),
                    "bb_feat_org": matching_seq_feat.donor_species_names_formatted(),
                    "bb_feat_org_risk": matching_seq_feat.donor_species_risk_groups(),
                    "bb_feat_nuc_pur": matching_seq_feat.nuc_acid_purity.english_name,
                    "bb_feat_nuc_risk": matching_seq_feat.nuc_acid_risk.english_name,
                    "bb_feat_oncogene": getattr(
                        matching_seq_feat.zkbs_oncogene, "name", "none"
                    ),
                }
            )
            remove_feature_qualifiers(feat, prefix="plannot_")

    return seq_record
