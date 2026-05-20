import json
import os
from io import BytesIO, StringIO

import requests
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import FeatureLocation, SeqFeature
from Bio.SeqRecord import SeqRecord
from Bio.SeqUtils import MeltingTemp as mt
from django.utils import timezone
from sgffp import (
    SgffBindingSite,
    SgffFeature,
    SgffPrimer,
    SgffReader,
    SgffSegment,
    SgffWriter,
)

from formz.models import SequenceFeature

from .colour_maps import SNAPGENE_COLOUR_MAP
from .plannotate.plannotate.annotate import annotate


def get_feature_label(feature):
    """Prefer label-like qualifiers when available, then fall back to feature type."""

    # Check common label-like qualifiers in order of preference, returning the first one found
    for key in ("label", "gene", "locus_tag", "note"):
        value = feature.qualifiers.get(key)
        if isinstance(value, list) and value:
            return str(value[0]).strip()
        elif isinstance(value, str) and value.strip():
            return str(value).strip()

    return feature.type


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


def extract_location_bounds(location):
    """Return (start, end, strand_symbol) for a location, merging parts if needed."""

    if location is None:
        return None

    # If the location has multiple parts (e.g. from a join), take the min start and max
    # end across all parts
    parts = getattr(location, "parts", None)
    if parts and len(parts) > 1:
        start = min(int(part.start) for part in parts)
        end = max(int(part.end) for part in parts)
        strand = location.strand
        if strand is None:
            for part in parts:
                if part.strand is not None:
                    strand = part.strand
                    break
    # If the location has no parts, just take its start and end
    else:
        start = int(location.start)
        end = int(location.end)
        strand = location.strand
    # Convert strand to symbol to be descriptive
    strand_symbol = {1: "+", -1: "-"}.get(strand, "?")
    return (start, end, strand_symbol)


def get_feature_bounds(feature):
    """Return (start, end, strand_symbol) for a feature's location, merging parts if needed."""
    return extract_location_bounds(feature.location)


def is_ignored_feature(feature):
    label = get_feature_label(feature).strip().lower()
    ftype = feature.type.strip().lower()
    return label == "source" or ftype == "source" or ftype == "primer_bind"


def get_map_dna_seqrecord(path):
    """Returns a SeqRecord object for the map_dna file, or None if not available or invalid"""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Map DNA file not found at path: {path}")

    try:
        name = os.path.basename(path).lower()
        if name.endswith(".dna"):
            return SeqIO.read(path, "snapgene")
        elif name.endswith((".gbk", ".gb")):
            return SeqIO.read(path, "genbank")
    except Exception:
        return None


def convert_snapgene_bytes_to_genbank(map_file_snapgene_content):
    """Convert SnapGene bytes to GenBank text while preserving feature/primer metadata"""

    if not isinstance(map_file_snapgene_content, (bytes, bytearray)):
        raise TypeError("map_file_snapgene_content must be bytes")

    seq_record = SeqIO.read(BytesIO(map_file_snapgene_content), "snapgene")
    sgff_record = SgffReader.from_bytes(map_file_snapgene_content)

    # Annotate the SeqRecord with SGFF metadata by adding qualifiers for primer information and feature colours
    add_snapgene_primer_qualifiers(seq_record, sgff_record)
    add_snapgene_colour_qualifier(seq_record, sgff_record)

    return seqrecord_to_genbank_text(seq_record)


def get_map_file_format(map_file_name, file_format):
    """Normalize map file format from explicit field or filename extension."""

    file_format = (file_format or "").strip().lower()
    if file_format:
        return file_format

    file_name = (map_file_name or "").strip()
    extension = os.path.splitext(file_name)[1].lower()
    return extension if extension else None


def _read_uploaded_file_content(uploaded_file):
    """Read the contents of an uploaded file object or raw bytes."""

    if hasattr(uploaded_file, "read"):
        return uploaded_file.read()
    return uploaded_file


def seqrecord_to_genbank_text(seq_record):
    """Write a SeqRecord to GenBank format and return the resulting text."""
    processed_handle = StringIO()
    SeqIO.write(seq_record, processed_handle, "genbank")
    return processed_handle.getvalue()


def process_genbank_map_file(map_file_edited):
    """Read and normalize an edited GenBank map file, returning clean GenBank text."""

    content = _read_uploaded_file_content(map_file_edited)
    if isinstance(content, bytes):
        content = content.decode()

    seq_record = SeqIO.read(StringIO(content), "genbank")
    return seqrecord_to_genbank_text(seq_record)


def process_snapgene_map_file(map_file_original_sg, map_file_edited_json):
    """Build an updated SnapGene map file from the original file and edited JSON payload."""

    original_content = _read_uploaded_file_content(map_file_original_sg)
    if not isinstance(original_content, (bytes, bytearray)):
        raise TypeError("map_file_original_sg must be bytes or file-like")

    sgff_record = SgffReader.from_bytes(original_content)

    if isinstance(map_file_edited_json, str):
        map_file_edited_json = json.loads(map_file_edited_json)

    required_keys = {"sequence", "features", "primers"}
    if not required_keys.issubset(map_file_edited_json):
        raise ValueError("Edited JSON is missing required fields")

    map_file_edited = update_sgff_from_edited_json(sgff_record, map_file_edited_json)
    return SgffWriter.to_bytes(map_file_edited)


def get_map_dna_features_simple(seq_record):
    """Returns a list of features in the map_dna file, with each feature represented
    as a tuple of

    (label, type, (start, end, strand_symbol))

    The start and end positions are merged across all parts of the feature if it has
    multiple parts (e.g. from a join). Strand is represented as '+' for forward, '-'
    for reverse, and '?' for unknown or mixed."""

    if not isinstance(seq_record, SeqIO.SeqRecord):
        raise ValueError("Input must be a SeqRecord object")

    return [
        (get_feature_label(f), f.type, extract_location_bounds(f.location))
        for f in seq_record.features
        if not is_ignored_feature(f)
    ]


def get_map_dna_feature_names(seq_record):
    """Return the names of the features in the map_dna file"""

    if not isinstance(seq_record, SeqIO.SeqRecord):
        raise ValueError("Input must be a SeqRecord object")

    features = get_map_dna_features_simple(seq_record)
    feature_names = [feature[0].strip() for feature in features]

    return feature_names


def covert_map_dna_to_dict(seq_record):
    """Convert the map_dna file to a dictionary format that can be used in the frontend"""

    if not isinstance(seq_record, SeqIO.SeqRecord):
        raise ValueError("Input must be a SeqRecord object")

    return {
        "id": seq_record.id,
        "name": seq_record.name,
        "description": seq_record.description,
        "sequence": str(seq_record.seq),
        "features": [
            {
                "type": f.type,
                "location": [
                    (int(p.start), int(p.end), p.strand) for p in f.location.parts
                ]
                if hasattr(f.location, "parts")
                else (
                    int(f.location.start),
                    int(f.location.end),
                    f.location.strand,
                ),
                "qualifiers": f.qualifiers,
            }
            for f in seq_record.features
        ],
        "annotations": seq_record.annotations,
    }


def convert_map_dna_to_svg(path, title):
    """Convert the map_dna file to svg format for display in the frontend"""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Map DNA file not found at path: {path}")

    # Get the map_dna file as an SVG string from the conversion service
    response = requests.get(
        "http://localhost:3000",
        params={
            "path": path,
            "title": title,
        },
    )

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to convert the map to SVG. Response: {response.text}")


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


def remove_feature_qualifiers(feature, prefix):
    """Remove qualifiers with the given prefix from a feature"""

    keys_to_remove = [k for k in feature.qualifiers if k.startswith(prefix)]
    for key in keys_to_remove:
        del feature.qualifiers[key]


def add_snapgene_colour_qualifier(seq_record, sgff_record):
    """Annotate features from a GenBank SeqRecord with bb_color qualifiers from a SGFF record."""

    # Build an index from exact SGFF feature coordinates (+ strand/type).
    # SGFF feature segments and Biopython FeatureLocation use 0-based,
    # end-exclusive coordinates for features.
    features_by_location = {}
    for sgff_feature in sgff_record.features:
        strand = 1 if getattr(sgff_feature, "strand", None) == "+" else -1
        ftype = str(getattr(sgff_feature, "type", "") or "")
        for segment in sgff_feature.segments:
            key = (
                int(segment.start),
                int(segment.end),
                strand,
                ftype,
            )
            features_by_location.setdefault(key, []).append(sgff_feature)

    # For each feature in the GenBank record, find a matching feature in the SGFF record
    for feature in seq_record.features:
        key = (
            int(feature.location.start),
            int(feature.location.end),
            feature.location.strand,
            str(feature.type or ""),
        )
        matching_features = features_by_location.get(key, [])

        if not matching_features:
            continue

        # If multiple features map to the same coordinates, just take the first one (there shouldn't be many)
        sgff_feature = matching_features[0]

        colour = getattr(sgff_feature, "color", None)
        if colour is not None:
            feature.qualifiers["color"] = colour


def add_snapgene_primer_qualifiers(seq_record, sgff_record):
    """Annotate primer_bind features from a GenBank SeqRecord with bb_primer_quals
    metadata from a SGFF record.

    ``bb_primer_quals`` contains the following comma-separated values
    ``<primer_sequence>,<annealed_bases>,<melting_temperature>``.
    """

    def _temperature_for_sort(site):
        value = getattr(site, "melting_temperature", None)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float("-inf")

    # Build an index from genomic coordinates to candidate SGFF primer sites, this allows
    # efficient lookup of the relevant SGFF primer information
    sites_by_location = {}
    for sgff_primer in sgff_record.primers:
        for binding_site in [
            bs for bs in sgff_primer.binding_sites if not bs.simplified
        ]:
            key = (
                # Convert to 0-based coordinates for comparison with Biopython features
                int(binding_site.start + 1),
                int(binding_site.end + 1),
                1 if binding_site.bound_strand == "+" else -1,
            )
            sites_by_location.setdefault(key, []).append((sgff_primer, binding_site))

    # For each primer_bind feature in the GenBank record, find a matching binding site in the SGFF record
    for feature in [f for f in seq_record.features if f.type == "primer_bind"]:
        key = (
            int(feature.location.start),
            int(feature.location.end),
            feature.location.strand,
        )
        matching_sites = sites_by_location.get(key, [])
        if not matching_sites:
            continue

        # If multiple sites map to the same coordinates, prefer the highest
        # available melting temperature value.
        sgff_primer, binding_site = max(
            matching_sites,
            key=lambda item: _temperature_for_sort(item[1]),
        )

        melting_temperature = getattr(binding_site, "melting_temperature", None)
        if melting_temperature is None:
            melting_temperature = ""
        feature.qualifiers["bb_primer_quals"] = ",".join(
            [
                str(getattr(sgff_primer, "sequence", "") or ""),
                str(getattr(binding_site, "annealed_bases", "") or ""),
                str(melting_temperature),
            ]
        )

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
                seq_record = SeqIO.read(BytesIO(file_content), "snapgene")
                sgff_record = SgffReader.from_bytes(file_content)
                # Annotate the SeqRecord with SGFF metadata by adding qualifiers for primer information and feature colours
                add_snapgene_primer_qualifiers(seq_record, sgff_record)
                add_snapgene_colour_qualifier(seq_record, sgff_record)
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

    # Annotate the sequence record with features
    annotations = annotate(seq_record.seq, linear=topology, is_detailed=is_detailed)
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

    # Return the annotated SeqRecord or the processed file content depending on the input type
    processed_content = seq_record_annotated
    if isinstance(file_content, bytes):
        processed_record = seq_record_annotated
        if compare:
            processed_record.features = features_compared

            # Get the feature names from the processed record, sanitizing them to improve matching
            # with known features in the database
            feature_names = [
                sanitize_feature_label(n, strip_fragment_suffix=True)
                for n in get_map_dna_feature_names(processed_record)
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
            for feat in processed_record.features:
                feat_name = sanitize_feature_label(
                    get_feature_label(feat), strip_fragment_suffix=True
                )
                matching_seq_feat = feature_map.get(feat_name)
                if matching_seq_feat:
                    feat.qualifiers["bb_feat_id"] = str(matching_seq_feat.id)
                    feat.qualifiers["bb_feat_name"] = matching_seq_feat.__str__()
                    feat.qualifiers["bb_feat_org"] = (
                        matching_seq_feat.donor_species_names_formatted()
                    )
                    feat.qualifiers["bb_feat_org_risk"] = (
                        matching_seq_feat.donor_species_risk_groups()
                    )
                    feat.qualifiers["bb_feat_nuc_pur"] = (
                        matching_seq_feat.nuc_acid_purity.english_name
                    )
                    feat.qualifiers["bb_feat_nuc_risk"] = (
                        matching_seq_feat.nuc_acid_risk.english_name
                    )
                    feat.qualifiers["bb_feat_oncogene"] = getattr(
                        matching_seq_feat.zkbs_oncogene, "name", "none"
                    )
                    remove_feature_qualifiers(feat, prefix="plannot_")

    return processed_content


def convert_biopython_to_sgff_feature(feature_biopython):
    """Create a new SgffFeature for the map_dna file with the given properties."""

    colour = feature_biopython.qualifiers.get("color")
    feature_sgff = SgffFeature(
        name=get_feature_label(feature_biopython),
        type=feature_biopython.type,
        strand="+" if feature_biopython.location.strand == 1 else "-",
        segments=[
            SgffSegment(
                start=int(seg.start),
                end=int(seg.end),
                color=colour,
            )
            for seg in sorted(
                feature_biopython.location.parts, key=lambda p: int(p.start)
            )
        ],
        qualifiers=feature_biopython.qualifiers,
        color=colour,
    )
    return feature_sgff


def convert_ove_to_sgff_feature(feature_ove):
    """Create a new SgffFeature for the map_dna file with the given properties."""

    colour = feature_ove.get("color", None)
    if isinstance(colour, list):
        # OVE note/color values may come through as single-item arrays.
        colour = colour[0] if colour else None

    if colour is None:
        colour = SNAPGENE_COLOUR_MAP.get(
            feature_ove["type"], SNAPGENE_COLOUR_MAP["_default"]
        )

    if colour is not None:
        colour = str(colour)

    feature_sgff = SgffFeature(
        name=feature_ove["name"],
        type=feature_ove["type"],
        strand="+" if feature_ove["strand"] == 1 else "-",
        segments=[
            SgffSegment(
                start=int(seg["start"]),
                end=int(seg["end"] + 1),
                color=colour,
            )
            for seg in sorted(feature_ove["locations"], key=lambda p: int(p["start"]))
        ]
        if "locations" in feature_ove
        else [
            SgffSegment(
                start=int(feature_ove["start"]),
                end=int(feature_ove["end"] + 1),
                color=colour,
                type=feature_ove["type"],
                translated="translation" in feature_ove.get("notes", {}),
            )
        ],
        qualifiers=feature_ove["notes"],
        color=colour,
    )

    return feature_sgff


def convert_ove_to_sgff_primer(primer_ove, primer_sequence=""):
    """Create a new SgffFeature for the map_dna file with the given properties."""

    if not primer_sequence:
        raise ValueError(
            "Primer sequence is required to convert OVE primer to SGFF primer"
        )

    annealed_bases = ""
    melting_temperature = None
    notes = primer_ove.get("notes", {})
    if "bb_primer_quals" in notes and "bb_primer_ove" not in notes:
        # This indicates that the primer originated from SnapGene and has not been modified in ove,
        # therefore we can trust the bb_primer_quals values

        try:
            quals_parts = notes["bb_primer_quals"][0].split(",")
            if len(quals_parts) == 3:
                primer_sequence = quals_parts[0]
                annealed_bases = quals_parts[1]
                if quals_parts[2] != "":
                    melting_temperature = float(quals_parts[2])
                del notes["bb_primer_quals"]

        except Exception:
            raise ValueError(
                f"Invalid format for bb_primer_quals: {notes['bb_primer_quals']}"
            )
    else:
        # For primers that did not originate from Snapgene, the annealed bases are the same as
        # the primer_sequence, in addition calculate the melting temperature based on the
        # primer sequence alone
        annealed_bases = primer_sequence
        # N.B.: The value produced by mt.Tm_NN is more often than not ± 5° C from the one
        # reported by SnapGene
        melting_temperature = round(
            mt.Tm_NN(
                primer_sequence,
                Na=100,
            ),
            0,
        )

    primer_sgff = SgffPrimer(
        name=primer_ove.get("name", ""),
        sequence=primer_sequence if primer_sequence else "",
        binding_sites=[
            SgffBindingSite(
                start=primer_ove["start"] - 1,
                end=primer_ove["end"],
                bound_strand="+" if primer_ove["strand"] == 1 else "-",
                annealed_bases=annealed_bases,
                melting_temperature=melting_temperature,
                simplified=False,
                extras=notes,
            )
        ],
        extras=notes,
    )

    return primer_sgff


def update_sgff_from_edited_json(sgff_map, edited_json):
    """Update a SnapGene map with edited JSON data."""

    # Take an "original" SnapGene map and the OVE JSON of the edited/final
    # map and update the SnapGene map to reflect the edits. Update: sequence,
    # features, and primers. Anything else?

    # Update sequence
    sgff_map.set_sequence(str(edited_json["sequence"]), record_history=False)

    # Clone features from GenBank map to SnapGene map
    sgff_map.features.clear()
    for feature in edited_json["features"].values():
        sgff_map.features.add(convert_ove_to_sgff_feature(feature))

    # Clone oligos from GenBank map to SnapGene map as primers
    sgff_map.primers.clear()
    for primer in edited_json["primers"].values():
        if "bb_primer_quals" in primer.get(
            "notes", {}
        ) or "bb_primer_ove" in primer.get("notes", {}):
            # If bb_primer_quals is present in the notes, the primer originated from SnapGene
            # If bb_primer_ove is present, the primer was created/modified in ove
            # Add this as a primer
            primer_sequence = edited_json.get("sequence", "")[
                primer["start"] : primer["end"] + 1
            ]
            sgff_map.primers.add(convert_ove_to_sgff_primer(primer, primer_sequence))
        else:
            # If the primer does not have bb_primer_quals or bb_primer_ove in the notes, it probably is
            # a primer that was added as a feature, therefore let's keep it like that
            sgff_map.features.add(convert_ove_to_sgff_feature(primer))

    return sgff_map
